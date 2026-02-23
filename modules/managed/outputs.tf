
output "dns_challenges" {
  sensitive = true
  value     = { for k, v in google_certificate_manager_dns_authorization.managed : k => v.dns_resource_record }
}

output "certificate_manager_id" {
  value       = one([for managed in google_certificate_manager_certificate.managed : managed.id])
  description = <<-EOD
  The Certificate Manager identifier or null.
  EOD
}

output "ssl_certificate_self_link" {
  value       = one([for managed in google_compute_managed_ssl_certificate.managed : managed.self_link])
  description = <<-EOD
  The Compute Engine SSL Certificate self-link or null.
  EOD
}

output "ssl_policy_self_link" {
  value = one(concat(
    [for policy in google_compute_ssl_policy.managed : policy.self_link],
    [for policy in google_compute_region_ssl_policy.managed : policy.self_link],
  ))
  description = <<-EOD
  A self-link URL for the created global or regional Google SSL Policy resource, or null.
  EOD
}
