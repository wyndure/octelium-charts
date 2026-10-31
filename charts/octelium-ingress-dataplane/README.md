# Octelium Ingress data plane

Deploys Envoy, its bootstrap ConfigMap and the public Service. Uses Envoy v1.40.0.

## Install

```sh
helm dependency build --skip-refresh charts/octelium-ingress-dataplane
helm upgrade --install ingress-dataplane ./charts/octelium-ingress-dataplane --namespace octelium
```

Create the namespace and configure its dependencies before installing. Published archives contain the common-library dependency. Read the [repository guide](https://github.com/wyndure/octelium-charts) for deployment, authentication and upgrade procedures.

## Values

| Value | Purpose |
| --- | --- |
| `xds.host`, `xds.port` | Ingress control-plane endpoint. |
| `frontProxy` | Match the ingress control plane and ClusterConfig. |
| `service` | Public Service type, ports, annotations and load-balancer settings. |
| `image`, `imagePullSecrets` | Container repository, tag/digest and registry credentials. |
| `nodeSelector`, `tolerations`, `affinity` | Node scheduling. |
| `service.labels` | Additional Service labels; selector labels remain fixed. |
| `podLabels`, `podAnnotations` | Additional Pod labels and annotations; selector labels remain fixed. |
| `resources`, `podSecurityContext`, `securityContext` | Main-container resources and Pod/container security settings. |
| `spiffe` | SPIFFE CSI driver and Workload API socket settings. |
| `extraEnv`, `extraEnvFrom` | Additional environment configuration; matching explicit names replace defaults. |
| `extraInitContainers`, `extraVolumes`, `extraVolumeMounts` | Additional native Kubernetes objects. |
| `replicas` | Number of workload replicas. |

See [values.yaml](values.yaml) for defaults and [values.schema.json](values.schema.json) for accepted fields.

## License

GNU AGPL v3; see [LICENSE](LICENSE).
