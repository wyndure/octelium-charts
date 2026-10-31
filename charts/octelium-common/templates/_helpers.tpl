{{- define "octelium.labels" -}}
app.kubernetes.io/name: octelium
app.kubernetes.io/instance: {{ .Release.Name | quote }}
app.kubernetes.io/version: {{ default .Chart.AppVersion .Values.image.tag | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service | quote }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | quote }}
{{- end -}}

{{- define "octelium.selectorLabels" -}}
app: octelium
octelium.com/component: {{ . | quote }}
octelium.com/component-type: cluster
{{- end -}}

{{- define "octelium.image" -}}
{{- $repository := required "image.repository is required" .image.repository -}}
{{- if .image.digest -}}
{{- printf "%s@%s" $repository .image.digest -}}
{{- else -}}
{{- printf "%s:%s" $repository (default .root.Chart.AppVersion .image.tag) -}}
{{- end -}}
{{- end -}}

{{- define "octelium.spiffeEnv" -}}
- name: OCTELIUM_ENABLE_SPIFFE_CSI
  value: {{ .Values.spiffe.enabled | quote }}
{{- if .Values.spiffe.enabled }}
- name: OCTELIUM_SPIFFE_CSI_DRIVER
  value: {{ .Values.spiffe.csiDriver | quote }}
{{- with .Values.spiffe.socketPath }}
- name: SPIFFE_ENDPOINT_SOCKET
  value: {{ . | quote }}
{{- end }}
{{- with .Values.spiffe.trustDomain }}
- name: OCTELIUM_SPIFFE_TRUST_DOMAIN
  value: {{ . | quote }}
{{- end }}
{{- end }}
{{- end -}}

{{- define "octelium.spiffeVolume" -}}
- name: spiffe-agent
  csi:
    driver: {{ .Values.spiffe.csiDriver | quote }}
    readOnly: true
{{- end -}}

{{- define "octelium.spiffeMount" -}}
- name: spiffe-agent
  mountPath: /run/spire/sockets
  readOnly: true
{{- end -}}


{{/* Extra EnvVar entries replace defaults in place, including valueFrom entries. */}}
{{- define "octelium.mergeEnv" -}}
{{- $overrides := dict -}}
{{- $seen := dict -}}
{{- range .extra -}}
{{- if hasKey $overrides .name -}}{{- fail (printf "duplicate extraEnv name %s" .name) -}}{{- end -}}
{{- $_ := set $overrides .name . -}}
{{- end -}}
{{- $env := list -}}
{{- range .base -}}
{{- $env = append $env (default . (get $overrides .name)) -}}
{{- $_ := set $seen .name true -}}
{{- end -}}
{{- range .extra -}}
{{- if not (hasKey $seen .name) -}}{{- $env = append $env . -}}{{- end -}}
{{- end -}}
{{- toYaml $env -}}
{{- end -}}

{{/* Custom labels may override descriptive labels; selectors remain stable. */}}
{{- define "octelium.customLabels" -}}
{{- $labels := mergeOverwrite (dict) (include "octelium.labels" .root | fromYaml) .extra (include "octelium.selectorLabels" .component | fromYaml) -}}
{{- toYaml $labels -}}
{{- end -}}
