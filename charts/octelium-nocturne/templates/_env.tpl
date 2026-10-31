{{- define "octelium.nocturne.env" -}}
- name: OCTELIUM_REGION_NAME
  valueFrom:
    configMapKeyRef:
      name: {{ .Values.regionRef.name | quote }}
      key: name
- name: OCTELIUM_REGION_UID
  valueFrom:
    configMapKeyRef:
      name: {{ .Values.regionRef.name | quote }}
      key: uid
{{- include "octelium.spiffeEnv" . | nindent 0 }}
{{- end -}}
