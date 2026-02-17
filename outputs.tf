output "ca_cert" {
  value       = trimspace(tls_self_signed_cert.ca.cert_pem)
  description = <<-EOD
  The CA certificate in PEM format.
  EOD
}

output "certificates" {
  value = { for k, v in tls_locally_signed_cert.tls : k => trimspace(v.cert_pem) }

  description = <<-EOD
  The map of generated TLS certificate PEMs, keyed by common name.
  EOD
}

output "secret_ids" {
  value = { for k, v in { for entry in concat(
    [for k, v in google_secret_manager_secret.key : [k, { key = v.id }]],
    [for k, v in google_secret_manager_secret.cert : [k, { cert = v.id }]],
    [for k, v in google_secret_manager_secret.json : [k, { json = v.id }]],
    [for k, v in google_secret_manager_regional_secret.key : [k, { key = v.id }]],
    [for k, v in google_secret_manager_regional_secret.cert : [k, { cert = v.id }]],
    [for k, v in google_secret_manager_regional_secret.json : [k, { json = v.id }]],
  ) : entry[0] => entry[1]... } : k => merge(v...) }
  description = <<-EOD
  A map of Secret Manager Secret identifiers for each TLS certificate, key, or JSON representation of the pair, keyed by
  common name.
  EOD
}

output "certificate_manager_ids" {
  value       = { for k, v in google_certificate_manager_certificate.tls : k => v.id }
  description = <<-EOD
  A map of Certificate Manager identifiers for each TLS certificate, keyed by common name.
  EOD
}

output "ssl_certificate_self_links" {
  value = merge(
    { for k, v in google_compute_ssl_certificate.tls : k => v.self_link },
    { for k, v in google_compute_region_ssl_certificate.tls : k => v.self_link },
  )
  description = <<-EOD
  A map of global or regional Compute Engine SSL Certificate self-links, keyed by common name.
  EOD
}

output "ssl_policy_self_link" {
  value = one(concat(
    [for policy in google_compute_ssl_policy.tls : policy.self_link],
    [for policy in google_compute_region_ssl_policy.tls : policy.self_link],
  ))
  description = <<-EOD
  A self-link URL for the created global or regional Google SSL Policy resource, or null.
  EOD
}
