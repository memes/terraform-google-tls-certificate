# Create a self-signed TLS certificate
terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 7.1"
    }
    tls = {
      source  = "hashicorp/tls"
      version = ">= 4.2"
    }
  }
}

locals {
  key_parts   = regex("^(?:(?P<algo>ECDSA)? ?P[ -]?(?P<curve>256|384)|(?P<algo>RSA)[ -]?(?P<bits>2048|3072|4096))$", upper(coalesce(try(var.tls_options.key_type, null), "P-256")))
  algorithm   = coalesce(local.key_parts["algo"], "ECDSA")
  rsa_bits    = local.algorithm == "RSA" ? local.key_parts["bits"] : null
  ecdsa_curve = local.algorithm == "ECDSA" ? format("P%s", coalesce(local.key_parts["curve"], "256")) : null
}

# Generate a CA key
resource "tls_private_key" "ca" {
  algorithm   = local.algorithm
  rsa_bits    = local.rsa_bits
  ecdsa_curve = local.ecdsa_curve
}

# Generate a CA cert
resource "tls_self_signed_cert" "ca" {
  private_key_pem = tls_private_key.ca.private_key_pem
  subject {
    common_name         = coalesce(try(var.subject.common_name, null), "Testing CA")
    organization        = coalesce(try(var.subject.organization, null), "F5, Inc")
    organizational_unit = coalesce(try(var.subject.organizational_unit, null), "F5, Inc")
    locality            = coalesce(try(var.subject.locality, null), "Seattle")
    province            = coalesce(try(var.subject.province, null), "Washington")
    country             = coalesce(try(var.subject.country, null), "US")
  }
  validity_period_hours = try(var.tls_options.ttl_hours, 48) * 5
  early_renewal_hours   = 2
  is_ca_certificate     = true
  allowed_uses          = []
}

# Generate a TLS cert key
resource "tls_private_key" "tls" {
  for_each    = var.requests
  algorithm   = local.algorithm
  rsa_bits    = local.rsa_bits
  ecdsa_curve = local.ecdsa_curve
}

# Generate a CSR
resource "tls_cert_request" "tls" {
  for_each        = var.requests
  private_key_pem = tls_private_key.tls[each.key].private_key_pem
  subject {
    common_name         = each.key
    organization        = tls_self_signed_cert.ca.subject[0].organization
    organizational_unit = tls_self_signed_cert.ca.subject[0].organizational_unit
    locality            = tls_self_signed_cert.ca.subject[0].locality
    province            = tls_self_signed_cert.ca.subject[0].province
    country             = tls_self_signed_cert.ca.subject[0].country
  }
  dns_names    = each.value.dns_names
  ip_addresses = each.value.ip_addresses
}

# Generate the TLS cert for the domain
resource "tls_locally_signed_cert" "tls" {
  for_each              = tls_cert_request.tls
  cert_request_pem      = each.value.cert_request_pem
  ca_private_key_pem    = tls_private_key.ca.private_key_pem
  ca_cert_pem           = tls_self_signed_cert.ca.cert_pem
  validity_period_hours = try(var.tls_options.ttl_hours, 48)
  early_renewal_hours   = 2
  is_ca_certificate     = false
  allowed_uses = try(var.tls_options.allowed_uses, [
    "digital_signature",
    "client_auth",
    "server_auth",
  ])
}

resource "google_secret_manager_secret" "key" {
  for_each    = var.secret_manager != null ? { for k, v in var.secret_manager : k => v if try(v.key, true) && coalesce(try(v.region, null), "global") == "global" } : {}
  project     = var.project_id
  secret_id   = format("%s-key", coalesce(try(each.value.prefix, null), replace(lower(each.key), "/[^a-z0-9-]/", "-")))
  labels      = var.labels
  annotations = var.annotations

  replication {
    auto {
    }
  }
}

resource "google_secret_manager_secret_version" "key" {
  for_each    = google_secret_manager_secret.key
  secret      = each.value.id
  secret_data = trimspace(tls_private_key.tls[each.key].private_key_pem)
}

resource "google_secret_manager_regional_secret" "key" {
  for_each    = var.secret_manager != null ? { for k, v in var.secret_manager : k => v if try(v.key, true) && coalesce(try(v.region, null), "global") != "global" } : {}
  project     = var.project_id
  secret_id   = format("%s-key", coalesce(try(each.value.prefix, null), replace(lower(each.key), "/[^a-z0-9-]/", "-")))
  location    = each.value.region
  labels      = var.labels
  annotations = var.annotations
}

resource "google_secret_manager_regional_secret_version" "key" {
  for_each    = google_secret_manager_regional_secret.key
  secret      = each.value.id
  secret_data = trimspace(tls_private_key.tls[each.key].private_key_pem)
}

resource "google_secret_manager_secret" "cert" {
  for_each    = var.secret_manager != null ? { for k, v in var.secret_manager : k => v if try(v.cert, true) && coalesce(try(v.region, null), "global") == "global" } : {}
  project     = var.project_id
  secret_id   = format("%s-cert", coalesce(try(each.value.prefix, null), replace(lower(each.key), "/[^a-z0-9-]/", "-")))
  labels      = var.labels
  annotations = var.annotations

  replication {
    auto {
    }
  }
}

resource "google_secret_manager_secret_version" "cert" {
  for_each    = google_secret_manager_secret.cert
  secret      = each.value.id
  secret_data = format("%s\n%s", trimspace(tls_locally_signed_cert.tls[each.key].cert_pem), trimspace(tls_self_signed_cert.ca.cert_pem))
}

resource "google_secret_manager_regional_secret" "cert" {
  for_each    = var.secret_manager != null ? { for k, v in var.secret_manager : k => v if try(v.cert, true) && coalesce(try(v.region, null), "global") != "global" } : {}
  project     = var.project_id
  secret_id   = format("%s-cert", coalesce(try(each.value.prefix, null), replace(lower(each.key), "/[^a-z0-9-]/", "-")))
  location    = each.value.region
  labels      = var.labels
  annotations = var.annotations
}

resource "google_secret_manager_regional_secret_version" "cert" {
  for_each    = google_secret_manager_regional_secret.cert
  secret      = each.value.id
  secret_data = format("%s\n%s", trimspace(tls_locally_signed_cert.tls[each.key].cert_pem), trimspace(tls_self_signed_cert.ca.cert_pem))
}

resource "google_secret_manager_secret" "json" {
  for_each    = var.secret_manager != null ? { for k, v in var.secret_manager : k => v if try(v.json, true) && coalesce(try(v.region, null), "global") == "global" } : {}
  project     = var.project_id
  secret_id   = format("%s-json", coalesce(try(each.value.prefix, null), replace(lower(each.key), "/[^a-z0-9-]/", "-")))
  labels      = var.labels
  annotations = var.annotations

  replication {
    auto {
    }
  }
}

resource "google_secret_manager_secret_version" "json" {
  for_each = google_secret_manager_secret.json
  secret   = each.value.id
  secret_data = jsonencode({
    cert = format("%s\n%s", trimspace(tls_locally_signed_cert.tls[each.key].cert_pem), trimspace(tls_self_signed_cert.ca.cert_pem))
    key  = trimspace(tls_private_key.tls[each.key].private_key_pem)
  })
}

resource "google_secret_manager_regional_secret" "json" {
  for_each    = var.secret_manager != null ? { for k, v in var.secret_manager : k => v if try(v.json, true) && coalesce(try(v.region, null), "global") != "global" } : {}
  project     = var.project_id
  secret_id   = format("%s-json", coalesce(try(each.value.prefix, null), replace(lower(each.key), "/[^a-z0-9-]/", "-")))
  location    = each.value.region
  labels      = var.labels
  annotations = var.annotations
}

resource "google_secret_manager_regional_secret_version" "json" {
  for_each = google_secret_manager_regional_secret.json
  secret   = each.value.id
  secret_data = jsonencode({
    cert = format("%s\n%s", trimspace(tls_locally_signed_cert.tls[each.key].cert_pem), trimspace(tls_self_signed_cert.ca.cert_pem))
    key  = trimspace(tls_private_key.tls[each.key].private_key_pem)
  })
}

resource "google_certificate_manager_certificate" "tls" {
  for_each = var.certificate_manager != null ? { for k, v in var.certificate_manager : k => {
    scope       = coalesce(try(v.region, null), "global") == "global" ? "ALL_REGIONS" : "DEFAULT"
    location    = coalesce(try(v.region, null), "global") != "global" ? v.region : null
    description = v.description
    name        = coalesce(try(v.name, null), replace(lower(k), "/[^a-z0-9-]/", "-"))
  } } : {}
  project     = var.project_id
  name        = each.value.name
  description = each.value.description
  labels      = var.labels
  scope       = each.value.scope
  location    = each.value.location
  self_managed {
    pem_certificate = format("%s\n%s", trimspace(tls_locally_signed_cert.tls[each.key].cert_pem), trimspace(tls_self_signed_cert.ca.cert_pem))
    pem_private_key = trimspace(tls_private_key.tls[each.key].private_key_pem)
  }
}

resource "google_compute_ssl_certificate" "tls" {
  for_each    = var.ssl_certificate != null ? { for k, v in var.ssl_certificate : k => v if coalesce(try(v.region, null), "global") == "global" } : {}
  project     = var.project_id
  name_prefix = coalesce(try(each.value.prefix, null), replace(lower(each.key), "/[^a-z0-9-]/", "-"))
  description = try(each.value.description, null)
  private_key = tls_private_key.tls[each.key].private_key_pem
  certificate = format("%s\n%s", trimspace(tls_locally_signed_cert.tls[each.key].cert_pem), trimspace(tls_self_signed_cert.ca.cert_pem))

  lifecycle {
    create_before_destroy = true
  }
}

resource "google_compute_region_ssl_certificate" "tls" {
  for_each    = var.ssl_certificate != null ? { for k, v in var.ssl_certificate : k => v if coalesce(try(v.region, null), "global") != "global" } : {}
  project     = var.project_id
  name_prefix = coalesce(try(each.value.prefix, null), replace(lower(each.key), "/[^a-z0-9-]/", "-"))
  description = try(each.value.description, null)
  region      = each.value.region
  private_key = tls_private_key.tls[each.key].private_key_pem
  certificate = format("%s\n%s", trimspace(tls_locally_signed_cert.tls[each.key].cert_pem), trimspace(tls_self_signed_cert.ca.cert_pem))

  lifecycle {
    create_before_destroy = true
  }
}

resource "google_compute_ssl_policy" "tls" {
  for_each        = var.ssl_policy != null && coalesce(try(var.ssl_policy.region, null), "global") == "global" ? { enabled = var.ssl_policy } : {}
  project         = var.project_id
  name            = each.value.name
  description     = try(each.value.description, "TLS Policy for F5 DevCentral Demos")
  profile         = try(each.value.profile, "MODERN")
  min_tls_version = try(each.value.min_tls_version, "TLS_1_2")
  custom_features = try(each.value.profile, "MODERN") == "CUSTOM" ? try(each.value.custom_features, []) : null
}

resource "google_compute_region_ssl_policy" "tls" {
  for_each        = var.ssl_policy != null && coalesce(try(var.ssl_policy.region, null), "global") != "global" ? { enabled = var.ssl_policy } : {}
  project         = var.project_id
  name            = each.value.name
  region          = each.value.region
  description     = try(each.value.description, "TLS Policy for F5 DevCentral Demos")
  profile         = try(each.value.profile, "MODERN")
  min_tls_version = try(each.value.min_tls_version, "TLS_1_2")
  custom_features = try(each.value.profile, "MODERN") == "CUSTOM" ? try(each.value.custom_features, []) : null
}
