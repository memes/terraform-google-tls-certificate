# Create a self-signed TLS certificate
terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 7.1"
    }
  }
}

resource "google_certificate_manager_dns_authorization" "managed" {
  for_each    = var.certificate_manager != null && try(length(var.domains), 0) > 0 ? { for domain in var.domains : domain => substr(format("%s-%s", var.certificate_manager.name, replace(lower(domain), "/[^a-z0-9-]/", "-")), 0, 64) } : {}
  project     = var.project_id
  name        = each.value
  description = var.certificate_manager.description
  type        = try(var.certificate_manager.type, null)
  domain      = each.key
  location    = coalesce(try(var.certificate_manager.region, null), "global")
  labels      = var.labels
}

resource "google_certificate_manager_certificate" "managed" {
  for_each    = var.certificate_manager != null ? { enabled = true } : {}
  project     = var.project_id
  name        = var.certificate_manager.name
  description = var.certificate_manager.description
  labels      = var.labels
  scope       = coalesce(try(var.certificate_manager.region, null), "global") == "global" ? "ALL_REGIONS" : "DEFAULT"
  location    = coalesce(try(var.certificate_manager.region, null), "global") != "global" ? var.certificate_manager.region : null
  managed {
    domains            = [for k, v in google_certificate_manager_dns_authorization.managed : v.domain]
    dns_authorizations = [for k, v in google_certificate_manager_dns_authorization.managed : v.id]
  }

  depends_on = [
    google_certificate_manager_dns_authorization.managed,
  ]
}



resource "google_compute_managed_ssl_certificate" "managed" {
  for_each    = var.ssl_certificate != null && try(length(var.domains), 0) > 0 ? { enabled = true } : {}
  project     = var.project_id
  name        = var.ssl_certificate.name
  description = var.ssl_certificate.description
  type        = "MANAGED"
  managed {
    domains = var.domains
  }
}

resource "google_compute_ssl_policy" "managed" {
  for_each        = var.ssl_policy != null && coalesce(try(var.ssl_policy.region, null), "global") == "global" ? { enabled = var.ssl_policy } : {}
  project         = var.project_id
  name            = var.ssl_policy.name
  description     = try(var.ssl_policy.description, "TLS Policy for F5 DevCentral Demos")
  profile         = try(var.ssl_policy.profile, "MODERN")
  min_tls_version = try(var.ssl_policy.min_tls_version, "TLS_1_2")
  custom_features = try(var.ssl_policy.profile, "MODERN") == "CUSTOM" ? try(var.ssl_policy.custom_features, []) : null
}

resource "google_compute_region_ssl_policy" "managed" {
  for_each        = var.ssl_policy != null && coalesce(try(var.ssl_policy.region, null), "global") != "global" ? { enabled = var.ssl_policy } : {}
  project         = var.project_id
  name            = each.value.name
  region          = each.value.region
  description     = try(each.value.description, "TLS Policy for F5 DevCentral Demos")
  profile         = try(each.value.profile, "MODERN")
  min_tls_version = try(each.value.min_tls_version, "TLS_1_2")
  custom_features = try(each.value.profile, "MODERN") == "CUSTOM" ? try(each.value.custom_features, []) : null
}
