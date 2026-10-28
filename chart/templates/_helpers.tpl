{{/* Names and labels shared by every template. */}}
{{- define "ta.name" -}}
{{- .Chart.Name -}}
{{- end -}}

{{- define "ta.labels" -}}
app.kubernetes.io/name: {{ include "ta.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Values.image.tag | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end -}}

{{/* Selector labels for one component; usage: include "ta.selector" (dict "ctx" . "component" "api") */}}
{{- define "ta.selector" -}}
app.kubernetes.io/name: {{ include "ta.name" .ctx }}
app.kubernetes.io/instance: {{ .ctx.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{- define "ta.apiImage" -}}
{{ .Values.image.registry }}/travel-agency-api:{{ .Values.image.tag }}
{{- end -}}

{{- define "ta.webImage" -}}
{{ .Values.image.registry }}/travel-agency-web:{{ .Values.image.tag }}
{{- end -}}

{{/* Environment shared by api, worker, beat and migrate: ConfigMap plus the app Secret. */}}
{{- define "ta.envFrom" -}}
envFrom:
  - configMapRef:
      name: {{ include "ta.name" . }}-config
  - secretRef:
      name: {{ .Values.secret.name }}
{{- end -}}
