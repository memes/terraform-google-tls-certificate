variable "project_id" {
  type = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "The project_id variable must must be 6 to 30 lowercase letters, digits, or hyphens; it must start with a letter and cannot end with a hyphen."
  }
  description = <<-EOD
  The GCP project identifier where resources will be created
  EOD
}

variable "labels" {
  type     = map(string)
  nullable = true
  validation {
    # GCP resource labels must be lowercase alphanumeric, underscore or hyphen,
    # and the key must be <= 63 characters in length
    condition     = var.labels == null ? true : alltrue([for k, v in var.labels : can(regex("^[a-z][a-z0-9_-]{0,62}$", k)) && can(regex("^[a-z0-9_-]{0,63}$", v))])
    error_message = "Each label key:value pair must match GCP requirements."
  }
  default     = {}
  description = <<EOD
An optional map of label key:value pairs to assign to the Google resources. Default is an empty map.
EOD
}

variable "domains" {
  type     = list(string)
  nullable = true
  validation {
    condition     = var.domains == null ? true : alltrue([for domain in var.domains : can(regex("^(?:\\*\\.)?(?:[a-z0-9][a-z0-9-]{0,61}[a-z0-9]\\.)+[a-z]{2,63}$", domain))])
    error_message = "Each domains entry must be a valid DNS name."
  }
  default = null
}

variable "certificate_manager" {
  type = object({
    name               = string
    region             = optional(string)
    description        = optional(string)
    add_wildcard       = optional(bool, false)
    dns_challenge      = optional(bool, false)
    dns_challenge_type = optional(string)
  })
  nullable = true
  validation {
    condition     = var.certificate_manager == null ? true : can(regex("^[a-z][a-z0-9-]{0,62}$", var.certificate_manager.name))
    error_message = "The name field must be RFC1035 compliant and between 1 and 63 characters in length."
  }
  default     = null
  description = <<-EOD
  If not null (default), or empty, create a Certificate Manager Certificate for each domain present in `domains`. The
  name and description of the Certificate will be taken from the mapped fields name and description, respectively, or
  derived from the domain name. Each entry may be regional if the region field is not empty, or global otherwise. If the
  add_wildcard field is true, the Certificate Manager Certificate will include wildcard support for each domain and
  force the use of DNS Challenges for domain verification regardless of the value of dns_challenge flag. The
  Certificate Manager Certificate will be ready for load-balancer authorization, but the use of DNS challenge may be
  forced by setting dns_challenge field to true, and optionally setting the dns_challenge_type field.
  EOD
}

variable "ssl_certificate" {
  type = object({
    name        = string
    description = optional(string)
  })
  nullable = true
  validation {
    condition     = var.ssl_certificate == null ? true : can(regex("^[a-z][a-z0-9-]{0,61}$", var.ssl_certificate.name))
    error_message = "The name field must be RFC1035 compliant and between 1 and 63 characters in length."
  }
  default     = null
  description = <<-EOD
  If not null, a global Compute Engine SSL Certificate will be created for key name given, valid for the domains
  provided.
  EOD
}

variable "ssl_policy" {
  type = object({
    name            = string
    description     = optional(string, "TLS Policy for F5 DevCentral Demos")
    region          = optional(string)
    profile         = optional(string, "MODERN")
    min_tls_version = optional(string, "TLS_1_2")
    custom_features = optional(list(string))
  })
  nullable = true
  validation {
    condition     = var.ssl_policy == null ? true : var.ssl_policy.name != null && can(regex("^[a-z][a-z0-9-]{0,62}$", var.ssl_policy.name))
    error_message = "The name variable must be RFC1035 compliant and between 1 and 63 characters in length."
  }
  default     = null
  description = <<-EOD
  If not null (default), a global Compute Engine SSL policy will be created with the specified options. The policy will be
  regional if the region field is not empty, global otherwise.
  EOD
}
