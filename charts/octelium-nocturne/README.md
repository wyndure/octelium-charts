# Octelium Nocturne

Deploys the controller that translates Octelium Service resources into Kubernetes workloads and synchronizes certificates.

## Install

```sh
helm dependency build --skip-refresh charts/octelium-nocturne
helm upgrade --install nocturne ./charts/octelium-nocturne --namespace octelium
```

Create the namespace and configure its dependencies before installing. Published archives contain the common-library dependency. Read the [repository guide](https://github.com/wyndure/octelium-charts) for deployment, authentication and upgrade procedures.

## Values

| Value | Purpose |
| --- | --- |
| `resourceServer` | Shared resource-server discovery backend. |
| `replicas` | `1`; upstream Nocturne has a single active controller. |
| `rbac.rules`, `rbac.workloadRules` | Cluster reads/Node updates and namespace-local workload writes. |
| `certificates` | Optional cert-manager issuer, cluster and per-namespace certificates. |
| `networkPolicy.enabled` | Enable Nocturne isolation policy. |
| `image`, `imagePullSecrets` | Container repository, tag/digest and registry credentials. |
| `nodeSelector`, `tolerations`, `affinity` | Node scheduling. |
| `podLabels`, `podAnnotations` | Additional Pod labels and annotations; selector labels remain fixed. |
| `resources`, `podSecurityContext`, `securityContext` | Main-container resources and Pod/container security settings. |
| `spiffe` | SPIFFE CSI driver and Workload API socket settings. |
| `extraEnv`, `extraEnvFrom` | Additional environment configuration; matching explicit names replace defaults. |
| `extraInitContainers`, `extraVolumes`, `extraVolumeMounts` | Additional native Kubernetes objects. |
| `regionRef.name` | Region ConfigMap in this namespace, with a `name` key; Nocturne additionally requires `uid`. |

See [values.yaml](values.yaml) for defaults and [values.schema.json](values.schema.json) for accepted fields.

## License

GNU AGPL v3; see [LICENSE](LICENSE).
