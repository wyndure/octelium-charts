{{/*
The upstream client always resolves octelium-rscserver.octelium.svc:8080.
Every consumer includes this template. The first release owns the shared alias;
other releases reuse it after validating its configuration. Retention prevents
uninstalling one consumer from deleting discovery used by the other consumers.
*/}}
{{- define "octelium.common.resourceServerAlias" -}}
{{- $endpoint := required "resourceServer.endpoint is required" .Values.resourceServer.endpoint | trimSuffix "." | lower -}}
{{- $backendPort := int .Values.resourceServer.port -}}
{{- $ip := or (contains ":" $endpoint) (regexMatch "^[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+$" $endpoint) -}}
{{- $headless := and $ip .Values.resourceServer.headless -}}
{{- if regexMatch "^octelium-rscserver\\.octelium\\.svc(\\.|$)" $endpoint -}}
{{- fail "resourceServer.endpoint must name the backend, not the alias octelium-rscserver.octelium.svc itself." -}}
{{- end -}}
{{- if and (ne $backendPort 8080) (or (not $ip) $headless) -}}
{{- fail "The upstream client uses port 8080. DNS and headless aliases require resourceServer.port=8080; use an IP endpoint with headless=false for port translation." -}}
{{- end -}}
{{- $configuration := dict "endpoint" $endpoint "port" $backendPort "headless" $headless -}}
{{- $fingerprint := toJson $configuration | sha256sum -}}
{{- $port := dict "name" "grpc" "protocol" "TCP" "port" 8080 "targetPort" $backendPort -}}
{{- $spec := dict "ports" (list $port) -}}
{{- if $ip -}}
{{- $_ := set $spec "type" "ClusterIP" -}}
{{- if $headless -}}{{- $_ := set $spec "clusterIP" "None" -}}{{- end -}}
{{- else -}}
{{- $_ := set $spec "type" "ExternalName" -}}
{{- $_ := set $spec "externalName" $endpoint -}}
{{- end -}}
{{- $service := lookup "v1" "Service" "octelium" "octelium-rscserver" -}}
{{- $renderService := true -}}
{{- if $service -}}
{{- $annotations := default dict $service.metadata.annotations -}}
{{- $owned := and (eq (index $annotations "meta.helm.sh/release-name") .Release.Name) (eq (index $annotations "meta.helm.sh/release-namespace") .Release.Namespace) -}}
{{- if not $owned -}}
{{- $actual := pick $service.spec "type" "ports" "externalName" "selector" -}}
{{- if $headless -}}{{- $_ := set $actual "clusterIP" $service.spec.clusterIP -}}{{- end -}}
{{- if or (ne (index $annotations "octelium.com/rscserver-configuration") $fingerprint) (ne (index $annotations "helm.sh/resource-policy") "keep") (ne (toJson $actual) (toJson $spec)) -}}
{{- fail "The shared Service octelium/octelium-rscserver has a different endpoint or is not a retained consumer alias. All consumers must use identical resourceServer settings; update the owning release or migrate the existing Service explicitly." -}}
{{- end -}}
{{- $renderService = false -}}
{{- end -}}
{{- end -}}
{{- if $renderService }}
---
apiVersion: v1
kind: Service
metadata:
  name: octelium-rscserver
  namespace: octelium
  labels:
    {{- include "octelium.labels" . | nindent 4 }}
  annotations:
    helm.sh/resource-policy: keep
    octelium.com/rscserver-configuration: {{ $fingerprint | quote }}
spec:
  {{- toYaml $spec | nindent 2 }}
{{- end }}
{{- if $ip -}}
{{- $sliceSpec := dict "addressType" (ternary "IPv6" "IPv4" (contains ":" $endpoint)) "ports" (list (dict "name" "grpc" "protocol" "TCP" "port" $backendPort)) "endpoints" (list (dict "addresses" (list $endpoint) "conditions" (dict "ready" true))) -}}
{{- $slice := lookup "discovery.k8s.io/v1" "EndpointSlice" "octelium" "octelium-rscserver-manual" -}}
{{- $renderSlice := true -}}
{{- if $slice -}}
{{- $annotations := default dict $slice.metadata.annotations -}}
{{- $owned := and (eq (index $annotations "meta.helm.sh/release-name") .Release.Name) (eq (index $annotations "meta.helm.sh/release-namespace") .Release.Namespace) -}}
{{- if not $owned -}}
{{- $actual := pick $slice "addressType" "ports" "endpoints" -}}
{{- $labels := default dict $slice.metadata.labels -}}
{{- if or (ne (index $annotations "octelium.com/rscserver-configuration") $fingerprint) (ne (index $annotations "helm.sh/resource-policy") "keep") (ne (index $labels "kubernetes.io/service-name") "octelium-rscserver") (ne (toJson $actual) (toJson $sliceSpec)) -}}
{{- fail "The shared EndpointSlice octelium/octelium-rscserver-manual has a different endpoint or is not a retained consumer alias. Align resourceServer settings with its owning release." -}}
{{- end -}}
{{- $renderSlice = false -}}
{{- end -}}
{{- end -}}
{{- if $renderSlice }}
---
apiVersion: discovery.k8s.io/v1
kind: EndpointSlice
metadata:
  name: octelium-rscserver-manual
  namespace: octelium
  labels:
    {{- include "octelium.labels" . | nindent 4 }}
    kubernetes.io/service-name: octelium-rscserver
    endpointslice.kubernetes.io/managed-by: octelium-charts
  annotations:
    helm.sh/resource-policy: keep
    octelium.com/rscserver-configuration: {{ $fingerprint | quote }}
{{ toYaml $sliceSpec }}
{{- end }}
{{- end }}
{{- end -}}
