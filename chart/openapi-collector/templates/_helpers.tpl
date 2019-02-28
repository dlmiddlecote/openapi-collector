{{/* vim: set filetype=mustache: */}}
{{/*
Expand the name of the chart.
*/}}
{{- define "openapi-collector.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "openapi-collector.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "openapi-collector.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "openapi-collector.swagger.config.default" -}}
{{- printf "%s-%s" (include "openapi-collector.name" .) "swagger-default-config" -}}
{{- end -}}

{{- define "openapi-collector.swagger.config.dynamic" -}}
{{- printf "%s-%s" (include "openapi-collector.name" .) "swagger-dynamic-config" -}}
{{- end -}}

{{- define "openapi-collector.nginx.config.default" -}}
{{- printf "%s-%s" (include "openapi-collector.name" .) "nginx-default-config" -}}
{{- end -}}

{{- define "openapi-collector.nginx.config.dynamic" -}}
{{- printf "%s-%s" (include "openapi-collector.name" .) "nginx-dynamic-config" -}}
{{- end -}}
