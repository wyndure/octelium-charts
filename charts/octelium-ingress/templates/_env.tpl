{{- define "octelium.ingress.env" -}}
- name: OCTELIUM_REGION_NAME
  valueFrom:
    configMapKeyRef:
      name: {{ .Values.regionRef.name | quote }}
      key: name
- name: OCTELIUM_FRONT_PROXY_MODE
  value: {{ .Values.frontProxy | quote }}
{{- include "octelium.spiffeEnv" . | nindent 0 }}
{{- end -}}
