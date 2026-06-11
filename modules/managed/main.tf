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

locals {
  # Handle nulls, etc.
  domains               = var.domains == null ? {} : var.domains
  domain_names          = keys(local.domains)
  expanded_domain_names = setunion(local.domain_names, [for domain in local.domain_names : try(var.certificate_manager.add_wildcard, false) ? format("*.%s", domain) : ""])
}

resource "google_certificate_manager_dns_authorization" "managed" {
  for_each    = var.certificate_manager != null && (try(var.certificate_manager.dns_challenge, false) || try(var.certificate_manager.add_wildcard, false)) ? { for domain in local.domain_names : domain => substr(format("%s-%s", var.certificate_manager.name, replace(lower(domain), "/[^a-z0-9-]/", "-")), 0, 64) } : {}
  project     = var.project_id
  name        = each.value
  description = var.certificate_manager.description
  type        = try(var.certificate_manager.dns_challenge_type, null)
  domain      = each.key
  location    = coalesce(try(var.certificate_manager.region, null), "global")
  labels      = var.labels
}

# If a Cloud DNS managed zone identifier has been provided we can add the supporting entries for Certificate Manager DNS
# challenges.
resource "google_dns_record_set" "challenges" {
  for_each = { for k, v in google_certificate_manager_dns_authorization.managed : k => {
    project_id   = coalesce(reverse(split("/", local.domains[k].managed_zone_id))[2], var.project_id)
    managed_zone = reverse(split("/", local.domains[k].managed_zone_id))[0]
    name         = one([for record in v.dns_resource_record : record.name])
    type         = one([for record in v.dns_resource_record : record.type])
    rrdatas      = [one([for record in v.dns_resource_record : record.data])]
    } if coalesce(try(local.domains[k].managed_zone_id, null), "unspecified") != "unspecified"
  }
  project      = each.value.project_id
  managed_zone = each.value.managed_zone
  name         = each.value.name
  type         = each.value.type
  ttl          = 300
  rrdatas      = each.value.rrdatas

  depends_on = [
    google_certificate_manager_dns_authorization.managed,
  ]
}

resource "google_certificate_manager_certificate" "managed" {
  for_each    = var.certificate_manager != null && length(local.domain_names) > 0 ? { enabled = true } : {}
  project     = var.project_id
  name        = var.certificate_manager.name
  description = var.certificate_manager.description
  labels      = var.labels
  scope       = coalesce(try(var.certificate_manager.region, null), "global") == "global" && length(google_certificate_manager_dns_authorization.managed) > 0 ? "ALL_REGIONS" : "DEFAULT"
  location    = coalesce(try(var.certificate_manager.region, null), "global") != "global" ? var.certificate_manager.region : null
  managed {
    domains            = local.expanded_domain_names
    dns_authorizations = [for k, v in google_certificate_manager_dns_authorization.managed : v.id]
  }

  depends_on = [
    google_certificate_manager_dns_authorization.managed,
  ]
}

resource "google_compute_managed_ssl_certificate" "managed" {
  for_each    = var.ssl_certificate != null && length(local.domain_names) > 0 ? { enabled = true } : {}
  project     = var.project_id
  name        = var.ssl_certificate.name
  description = var.ssl_certificate.description
  type        = "MANAGED"
  managed {
    domains = local.domain_names
  }
}

resource "google_compute_ssl_policy" "managed" {
  for_each        = var.ssl_policy != null && coalesce(try(var.ssl_policy.region, null), "global") == "global" ? { enabled = true } : {}
  project         = var.project_id
  name            = var.ssl_policy.name
  description     = try(var.ssl_policy.description, "TLS Policy for F5 DevCentral Demos")
  profile         = try(var.ssl_policy.profile, "MODERN")
  min_tls_version = try(var.ssl_policy.min_tls_version, "TLS_1_2")
  custom_features = try(var.ssl_policy.profile, "MODERN") == "CUSTOM" ? try(var.ssl_policy.custom_features, []) : null
}

resource "google_compute_region_ssl_policy" "managed" {
  for_each        = var.ssl_policy != null && coalesce(try(var.ssl_policy.region, null), "global") != "global" ? { enabled = true } : {}
  project         = var.project_id
  name            = var.ssl_policy.name
  region          = var.ssl_policy.region
  description     = try(var.ssl_policy.description, "TLS Policy for F5 DevCentral Demos")
  profile         = try(var.ssl_policy.profile, "MODERN")
  min_tls_version = try(var.ssl_policy.min_tls_version, "TLS_1_2")
  custom_features = try(var.ssl_policy.profile, "MODERN") == "CUSTOM" ? try(var.ssl_policy.custom_features, []) : null
}

resource "google_certificate_manager_certificate_map" "managed" {
  for_each    = length([for k, v in google_certificate_manager_certificate.managed : v.id if coalesce(v.location, "global") == "global"]) > 0 && coalesce(try(var.certificate_map.name, null), "unspecified") != "unspecified" ? { enabled = true } : {}
  project     = var.project_id
  name        = var.certificate_map.name
  description = try(var.certificate_map.description, null)
}

resource "google_certificate_manager_certificate_map_entry" "managed" {
  for_each     = google_certificate_manager_certificate_map.managed
  project      = each.value.project
  name         = each.value.name
  description  = each.value.description
  map          = each.value.name
  certificates = [for k, v in google_certificate_manager_certificate.managed : v.id if coalesce(v.location, "global") == "global"]
  matcher      = "PRIMARY"
}
