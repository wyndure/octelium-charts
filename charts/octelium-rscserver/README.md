# Octelium Resource server

Deploys the resource server with external PostgreSQL and Redis connections. The built-in initializer ensures the default ClusterConfig exists before startup.

## Install

```sh
helm dependency build --skip-refresh charts/octelium-rscserver
helm upgrade --install rscserver ./charts/octelium-rscserver --namespace octelium --values examples/rscserver.yaml
```

Create the namespace and configure its dependencies before installing. Published archives contain the common-library dependency. Read the [repository guide](https://github.com/wyndure/octelium-charts) for deployment, authentication and upgrade procedures.

## Values

| Value | Purpose |
| --- | --- |
| `postgresql`, `redis` | Storage endpoints, TLS, database settings and credential Secret references (`secretRef.name`, `secretRef.usernameKey`, `secretRef.passwordKey`). |
| `initializer.enabled` | `true`; run the built-in initializer before the server. |
| `initializer.domain` | Cluster domain used when creating a missing ClusterConfig. |
| `initializer.image`, `initializer.timeout` | Initializer image (empty tag defaults to `Chart.appVersion`) and retry timeout. |
| `initializer.securityContext`, `initializer.resources`, `initializer.extraEnv`, `initializer.extraEnvFrom`, `initializer.extraVolumeMounts` | Init-container configuration. |
| `clusterConfigMap.name` | Optional output ConfigMap with ClusterConfig `name` and `uid`; requires the initializer. |
| `service.name` | Backend Service name; default `octelium-rscserver-backend`. |
| `networkPolicy.mode` | `disabled` or `cilium`. |
| `image`, `imagePullSecrets` | Container repository, tag/digest and registry credentials. |
| `nodeSelector`, `tolerations`, `affinity` | Node scheduling. |
| `podLabels`, `podAnnotations` | Additional Pod labels and annotations; selector labels remain fixed. |
| `resources`, `podSecurityContext`, `securityContext` | Main-container resources and Pod/container security settings. |
| `spiffe` | SPIFFE CSI driver and Workload API socket settings. |
| `extraEnv`, `extraEnvFrom` | Additional environment configuration; matching explicit names replace defaults. |
| `extraInitContainers`, `extraVolumes`, `extraVolumeMounts` | Additional native Kubernetes objects. |
| `regionRef.name` | Region ConfigMap in this namespace, with a `name` key; Nocturne additionally requires `uid`. |
| `replicas` | Number of workload replicas. |

See [values.yaml](values.yaml) for defaults and [values.schema.json](values.schema.json) for accepted fields.

## License

GNU AGPL v3; see [LICENSE](LICENSE).
