{{- define "octelium.rscserver.storageEnv" -}}
- name: OCTELIUM_POSTGRES_HOST
  value: {{ required "postgresql.host is required" .Values.postgresql.host | quote }}
- name: OCTELIUM_POSTGRES_PORT
  value: {{ .Values.postgresql.port | quote }}
- name: OCTELIUM_POSTGRES_DATABASE
  value: {{ required "postgresql.database must name an existing database" .Values.postgresql.database | quote }}
- name: OCTELIUM_POSTGRES_USERNAME
  valueFrom:
    secretKeyRef:
      name: {{ required "postgresql.secretRef.name is required" .Values.postgresql.secretRef.name | quote }}
      key: {{ required "postgresql.secretRef.usernameKey is required" .Values.postgresql.secretRef.usernameKey | quote }}
- name: OCTELIUM_POSTGRES_NOSSL
  value: {{ not .Values.postgresql.tls | quote }}
- name: OCTELIUM_POSTGRES_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ required "postgresql.secretRef.name is required" .Values.postgresql.secretRef.name | quote }}
      key: {{ required "postgresql.secretRef.passwordKey is required" .Values.postgresql.secretRef.passwordKey | quote }}
- name: OCTELIUM_REDIS_HOST
  value: {{ required "redis.host is required" .Values.redis.host | quote }}
- name: OCTELIUM_REDIS_PORT
  value: {{ .Values.redis.port | quote }}
- name: OCTELIUM_REDIS_DATABASE
  value: {{ .Values.redis.database | quote }}
- name: OCTELIUM_REDIS_USERNAME
  valueFrom:
    secretKeyRef:
      name: {{ required "redis.secretRef.name is required" .Values.redis.secretRef.name | quote }}
      key: {{ required "redis.secretRef.usernameKey is required" .Values.redis.secretRef.usernameKey | quote }}
- name: OCTELIUM_REDIS_USE_TLS
  value: {{ .Values.redis.tls | quote }}
- name: OCTELIUM_REDIS_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ required "redis.secretRef.name is required" .Values.redis.secretRef.name | quote }}
      key: {{ required "redis.secretRef.passwordKey is required" .Values.redis.secretRef.passwordKey | quote }}
{{- end -}}

{{- define "octelium.rscserver.env" -}}
- name: OCTELIUM_REGION_NAME
  valueFrom:
    configMapKeyRef:
      name: {{ .Values.regionRef.name | quote }}
      key: name
{{- include "octelium.rscserver.storageEnv" . | nindent 0 }}
{{- include "octelium.spiffeEnv" . | nindent 0 }}
{{- end -}}

{{/* Share effective storage overrides while keeping Region/SPIFFE out of initialization. */}}
{{- define "octelium.rscserver.initializerStorageEnv" -}}
{{- $overrides := list -}}
{{- range .Values.extraEnv -}}
{{- if or (hasPrefix "OCTELIUM_POSTGRES_" .name) (hasPrefix "OCTELIUM_REDIS_" .name) -}}
{{- $overrides = append $overrides . -}}
{{- end -}}
{{- end -}}
{{- include "octelium.mergeEnv" (dict "base" (include "octelium.rscserver.storageEnv" . | fromYamlArray) "extra" $overrides) -}}
{{- end -}}
