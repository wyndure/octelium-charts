{{- define "octelium.octovigil.env" -}}
- name: OCTELIUM_REGION_NAME
  valueFrom:
    configMapKeyRef:
      name: {{ .Values.regionRef.name | quote }}
      key: name
{{- include "octelium.spiffeEnv" . | nindent 0 }}
{{- end -}}
