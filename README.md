# Octelium Helm charts

Independent Helm charts for deploying Octelium components on Kubernetes. The Go component charts use Octelium v0.47.0; the ingress data plane uses Envoy v1.40.0. Chart version 0.47.0 includes the resource-server initializer by default.

| Chart | Purpose |
| --- | --- |
| [octelium-rscserver](charts/octelium-rscserver) | Resource server, PostgreSQL/Redis connections and default ClusterConfig initialization |
| [octelium-gwagent](charts/octelium-gwagent) | Gateway Agent DaemonSet and node-network integration |
| [octelium-nocturne](charts/octelium-nocturne) | Service workload controller, Kubernetes RBAC and optional certificates |
| [octelium-octovigil](charts/octelium-octovigil) | Octovigil control service |
| [octelium-ingress](charts/octelium-ingress) | Ingress xDS control plane |
| [octelium-ingress-dataplane](charts/octelium-ingress-dataplane) | Envoy data plane and public Service |
| [octelium-common](charts/octelium-common) | Shared library bundled into each application chart |

## Install

Use Helm 3.19 or later and Kubernetes 1.27 or later. Supply existing PostgreSQL and Redis services, their credentials, and the namespaces in which workloads will run.

```sh
helm show chart oci://ghcr.io/wyndure/charts/octelium-rscserver --version 0.47.0
```

Create the upstream workload namespace:

```sh
kubectl create namespace octelium
```

Prepare a values file using [examples/rscserver.yaml](examples/rscserver.yaml). Create the referenced credentials Secrets in the resource server's namespace:

```yaml
postgresql:
  host: postgres.database.svc.cluster.local
  database: octelium
  secretRef:
    name: postgres-credentials
    usernameKey: username
    passwordKey: password
redis:
  host: redis.database.svc.cluster.local
  secretRef:
    name: redis-credentials
    usernameKey: username
    passwordKey: password
initializer:
  domain: access.example.com
regionRef:
  name: octelium-region
```

PostgreSQL and Redis TLS are enabled by default; configure them to match your storage services. The PostgreSQL user needs table/index creation permissions for the resource server's startup migrations. Values reference an existing database and user. Both `secretRef` objects identify a Secret in the resource server namespace containing the username and password. For Redis without a named ACL user, store an empty username in the referenced key. The server and initializer use the same Secret references.

Create a Region ConfigMap in each Go component's namespace. Its `name` key supplies the selected Region name. Nocturne also requires the Region's actual UID under `uid`; see [examples/region-configmap.yaml](examples/region-configmap.yaml). The resource server can start with the `name` key before the Region resource is provisioned.

Install the resource server:

```sh
helm upgrade --install resource-server oci://ghcr.io/wyndure/charts/octelium-rscserver --version 0.47.0 \
  --namespace octelium --values values.yaml
```

Once it is running, provision the selected Region, Octelium Namespaces, application keys and Services using the Octelium operator or your management workflow. Nocturne uses those Service resources to create the API server, authentication server, DNS server and Vigil workloads. Install the other component charts as needed; each is a separate release.

For installation from this repository, build the local library dependency first:

```sh
helm dependency build --skip-refresh charts/octelium-rscserver
helm upgrade --install resource-server ./charts/octelium-rscserver \
  --namespace octelium --values values.yaml
```

Published chart archives already contain the library dependency.

## Resource-server initialization

The resource-server chart runs `octelium-initializer` before its main container. It connects directly to the configured PostgreSQL and Redis services, creates a minimal `ClusterConfig/default` when missing, and preserves an existing configuration and its UID.

```yaml
initializer:
  enabled: true
  domain: access.example.com
  timeout: 2m
  image:
    repository: ghcr.io/wyndure/octelium-initializer
    tag: "" # Defaults to Chart.appVersion.
```

Set `initializer.domain` for a fresh database. Existing ClusterConfig installations can leave it empty. An empty `initializer.image.tag` defaults to `Chart.appVersion`. Set an explicit tag or digest through `initializer.image` to select another build.

The init container shares the server's storage settings, Secret references, storage-related `extraEnv` overrides and `extraEnvFrom`. Configure initializer-specific settings through `initializer.extraEnv`, `extraEnvFrom`, `securityContext`, `resources` and `extraVolumeMounts`. It defaults to UID/GID 65532 with a read-only root filesystem. Extra init containers run before the built-in initializer, allowing shared-volume preparation.

To manage ClusterConfig initialization externally:

```yaml
initializer:
  enabled: false
```

### Publish the ClusterConfig identity

```yaml
clusterConfigMap:
  name: octelium-cluster
```

With initialization enabled, the chart creates this ConfigMap in the release namespace. The initializer writes fixed keys `name` and `uid`, preserving other keys. The ConfigMap remains Helm-owned. A dedicated ServiceAccount can patch only that named ConfigMap; a projected API token is mounted only in the initializer. The main resource server has automatic token mounting disabled. Publication requires access to the Kubernetes API.

Use a separate ConfigMap from `regionRef`: ClusterConfig and Region have distinct identities. Empty `clusterConfigMap.name` disables publication. Removing the initializer also requires disabling publication.

## Resource-server discovery

Gateway Agent, Nocturne, Octovigil and the ingress control plane use the upstream address `octelium-rscserver.octelium.svc:8080`. Configure their backend through the same values in all four releases:

```yaml
resourceServer:
  endpoint: octelium-rscserver-backend.octelium.svc.cluster.local
  port: 8080
  headless: true
```

Each consumer creates or reuses a retained discovery Service in the existing `octelium` namespace. Install the first consumer before the others so connected Helm installations can discover and reuse its alias. All consumers in a Kubernetes cluster share this address and must agree on the backend.

DNS backends use an ExternalName Service. IP backends use a Service and explicit EndpointSlice; IPv4 and IPv6 are supported. To translate backend ports, use an IP endpoint with `headless: false`. DNS and headless discovery use port 8080. See the [DNS](examples/rscserver-endpoint.yaml) and [IP](examples/rscserver-ip-endpoint.yaml) examples.

The owning release can update the alias. Other releases validate and reuse matching resources through Helm `lookup`. Alias resources remain after uninstall so other consumers retain discovery. Offline renderers emit the alias for each chart; coordinate its ownership when assembling multiple rendered releases.

The resource-server provider's backend Service defaults to `octelium-rscserver-backend`. Envoy connects to the ingress control plane through `xds.host` and `xds.port`.

## SPIFFE and public TLS

Enable SPIFFE authentication for the Go services and mount the Workload API socket using the [shared overlay](examples/spiffe.yaml):

```yaml
spiffe:
  enabled: true
  csiDriver: csi.spiffe.io
  socketPath: /run/spire/sockets/spire-agent.sock
```

Install SPIRE, the SPIFFE CSI driver and matching workload registration before starting those workloads. Go charts additionally accept `spiffe.trustDomain`. Empty socket paths in Go charts preserve upstream socket discovery; Envoy uses its configured socket directly for SDS.

Nocturne can request cert-manager Certificates through `certificates.enabled`, `issuerRef`, `cluster.domain` or explicit DNS names, and per-namespace certificate entries. Its Secret synchronization uses `cert-cluster` and `cert-ns-<namespace>` in the upstream `octelium` namespace. See [examples/nocturne.yaml](examples/nocturne.yaml).

For public TLS terminated by an existing front proxy, set `frontProxy: true` in both ingress charts and use a suitable data-plane Service type. Match this with ClusterConfig and preserve the required Host, HTTP/2, gRPC and streaming behavior at the proxy.

## Scheduling, networking and permissions

Gateway Agent runs on host networking with the network capabilities needed for gateway operation. Prepare WireGuard and `ip6table_filter` kernel support, a primary CNI, Multus and the Octelium NetworkAttachmentDefinition. `multusHostConfDir` identifies the host Multus configuration directory.

Nocturne watches Pods, Services, Secrets and Nodes cluster-wide and updates Nodes for gateway taints. Its workload-write Role is confined to the upstream `octelium` namespace, even when the controller is installed elsewhere. Customize `rbac.rules` and `rbac.workloadRules`, or provide equivalent permissions with `rbac.create: false`.

Ingress and Octovigil network policies allow label-matched clients across namespaces, with optional namespace restrictions. Resource-server network isolation is selected through `networkPolicy.mode`; the `cilium` mode requires Cilium's policy API. Cert-manager features similarly require its CRDs and controller.

## Pod extensions

All six application charts support `podSecurityContext`, `securityContext`, `extraInitContainers`, `extraVolumes`, `extraVolumeMounts`, `extraEnv` and `extraEnvFrom`. These accept native Kubernetes objects. An `extraEnv` entry replaces a built-in variable with the same name, including replacing literal values with Secret or ConfigMap references. Repeated names are rejected. See [examples/workload-extensions.yaml](examples/workload-extensions.yaml).

## Upgrades and removal

Upgrade each component release with its reviewed values. Storage and application-resource upgrades follow Octelium's release procedures. A Helm rollback changes workloads; it does not roll back PostgreSQL state.

When upgrading from chart 0.2.x, remove any manually configured `extraInitContainers` entry named `octelium-initializer` and use `initializer` values instead. It is enabled by default in 0.47.0. Disabling it requires an existing ClusterConfig before resource-server startup.

Uninstalling removes chart-owned workloads and publication ConfigMaps. Shared discovery resources are retained. PostgreSQL, Redis, their credentials, application resources and workloads managed by Nocturne have their own lifecycle. Allow controllers to finish resource finalization before decommissioning them.

## Validate and package

Maintainer tooling uses Python 3.10 or later, Helm 3.19 and the pinned dependencies:

```sh
python3 -m pip install -r requirements-dev.txt
make lint
make package
make test
```

## License

See [LICENSE](LICENSE) for GNU AGPL v3. Each chart package includes the license.

## Legal

This project is a community endeavour and is not associated with Octelium Labs, LLC.

Octelium and Octelium logo are trademarks of Octelium Labs, LLC.

WireGuard is a registered trademark of Jason A. Donenfeld.
