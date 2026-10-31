{{- define "octelium.gwagent.env" -}}
- name: OCTELIUM_NODE
  valueFrom:
    fieldRef: {fieldPath: spec.nodeName}
- name: OCTELIUM_NAMESPACE
  valueFrom:
    fieldRef: {fieldPath: metadata.namespace}
- name: OCTELIUM_POD
  valueFrom:
    fieldRef: {fieldPath: metadata.name}
- name: OCTELIUM_REGION_NAME
  valueFrom:
    configMapKeyRef:
      name: {{ .Values.regionRef.name | quote }}
      key: name
- name: OCTELIUM_MULTUS_CONF_DIR
  value: /host/multus-conf
{{- include "octelium.spiffeEnv" . | nindent 0 }}
{{- end -}}
