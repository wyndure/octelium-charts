# Octelium Ingress control plane

Deploys the ingress xDS control plane and its Service.

## Install

```sh
helm dependency build --skip-refresh charts/octelium-ingress
helm upgrade --install ingress ./charts/octelium-ingress --namespace octelium
```

Create the namespace and configure its dependencies before installing. Published archives contain the common-library dependency. Read the [repository guide](https://github.com/wyndure/octelium-charts) for deployment, authentication and upgrade procedures.

## Values

| Value | Purpose |
| --- | --- |
| `resourceServer` | Shared resource-server discovery backend. |
| `frontProxy` | Public TLS is terminated by an existing front proxy; match the data plane and ClusterConfig. |
| `networkPolicy` | Enable the policy and select allowed client namespaces. |
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
