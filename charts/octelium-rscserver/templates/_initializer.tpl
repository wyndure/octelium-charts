{{- define "octelium.rscserver.validateInitializer" -}}
{{- if and .Values.clusterConfigMap.name (not .Values.initializer.enabled) -}}
{{- fail "clusterConfigMap.name requires initializer.enabled=true" -}}
{{- end -}}
{{- if and .Values.clusterConfigMap.name (eq .Values.clusterConfigMap.name .Values.regionRef.name) -}}
{{- fail "clusterConfigMap.name must differ from regionRef.name" -}}
{{- end -}}
{{- if .Values.initializer.enabled -}}
{{- range .Values.extraInitContainers -}}
{{- if eq .name "octelium-initializer" -}}
{{- fail "octelium-initializer is managed by initializer.enabled; remove it from extraInitContainers or disable the built-in initializer" -}}
{{- end -}}
{{- end -}}
{{- range .Values.initializer.extraEnv -}}
{{- if has .name (list "OCTELIUM_INITIALIZER_CLUSTER_CONFIG_MAP" "POD_NAMESPACE") -}}
{{- fail (printf "initializer.extraEnv must not override %s; configure publication through clusterConfigMap.name" .name) -}}
{{- end -}}
{{- end -}}
{{- if regexMatch "^(0+(\\.0+)?(ns|us|µs|ms|s|m|h))+$" .Values.initializer.timeout -}}
{{- fail "initializer.timeout must be positive" -}}
{{- end -}}
{{- end -}}
{{- if .Values.clusterConfigMap.name -}}
{{- range .Values.extraVolumes -}}
{{- if eq .name "initializer-api-access" -}}
{{- fail "extraVolumes must not use the reserved initializer-api-access volume name" -}}
{{- end -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "octelium.rscserver.initializer" -}}
{{- $env := include "octelium.rscserver.initializerStorageEnv" . | fromYamlArray -}}
{{- $env = append $env (dict "name" "OCTELIUM_CLUSTER_DOMAIN" "value" .Values.initializer.domain) -}}
{{- $env = include "octelium.mergeEnv" (dict "base" $env "extra" .Values.initializer.extraEnv) | fromYamlArray -}}
{{- if .Values.clusterConfigMap.name -}}
{{- $env = append $env (dict "name" "OCTELIUM_INITIALIZER_CLUSTER_CONFIG_MAP" "value" .Values.clusterConfigMap.name) -}}
{{- $env = append $env (dict "name" "POD_NAMESPACE" "valueFrom" (dict "fieldRef" (dict "fieldPath" "metadata.namespace"))) -}}
{{- end -}}
- name: octelium-initializer
  image: {{ include "octelium.image" (dict "root" . "image" .Values.initializer.image) | quote }}
  imagePullPolicy: {{ .Values.initializer.image.pullPolicy }}
  args:
    - {{ printf "--timeout=%s" .Values.initializer.timeout | quote }}
  {{- with .Values.initializer.securityContext }}
  securityContext:
    {{- toYaml . | nindent 4 }}
  {{- end }}
  {{- with .Values.initializer.resources }}
  resources:
    {{- toYaml . | nindent 4 }}
  {{- end }}
  env:
    {{- toYaml $env | nindent 4 }}
  {{- $envFrom := concat .Values.extraEnvFrom .Values.initializer.extraEnvFrom }}
  {{- with $envFrom }}
  envFrom:
    {{- toYaml . | nindent 4 }}
  {{- end }}
  {{- if or .Values.clusterConfigMap.name .Values.initializer.extraVolumeMounts }}
  volumeMounts:
    {{- if .Values.clusterConfigMap.name }}
    - name: initializer-api-access
      mountPath: /var/run/secrets/kubernetes.io/serviceaccount
      readOnly: true
    {{- end }}
    {{- with .Values.initializer.extraVolumeMounts }}
    {{- toYaml . | nindent 4 }}
    {{- end }}
  {{- end }}
{{- end -}}
