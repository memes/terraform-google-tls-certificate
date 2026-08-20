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
  type = map(object({
    managed_zone_id = optional(string)
  }))
  nullable = true
  validation {
    condition = var.domains == null ? true : alltrue([for k, v in var.domains : (
      can(regex("^(?:[a-z0-9][a-z0-9-]{0,61}[a-z0-9]\\.)+[a-z]{2,63}$", k)) &&
      (v == null || coalesce(v.managed_zone_id, "unspecified") == "unspecified" ? true : can(regex("projects/[a-z][a-z0-9-]{4,28}[a-z0-9]/managedZones/[a-z][a-z0-9-]{0,61}[a-z0-9]?$", v.managed_zone_id)))
    )])
    error_message = "Each domains key must be a valid, non-wildcard, DNS name, and if a managed_zone_id is provided it must be valid."
  }
  default     = null
  description = <<-EOD
  If not null (default), the module will create a managed TLS certificate - optionally with wildcard support (see
  `certificate_manager` variable) - for each key in the map. If the value of a domain contains a Cloud DNS managed zone
  identifier the module will attempt to add DNS challenge records needed to provision a managed certificate.

  E.g. to create managed TLS certiicate for `example.com` without adding CNAME challenge records, use
  domains = {
    "example.com" = null,
  }

  To do the same, but automatically add challenge records to Cloud DNS zone, use
  domains = {
    "example.com" = {
      "managed_zone_id = "projects/DNS_PROJECT/managedZones/MANAGED_ZONE_ID"
    },
  }
  EOD
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

variable "certificate_map" {
  type = object({
    name        = string
    description = optional(string)
  })
  nullable = true
  validation {
    condition = var.certificate_map == null ? true : (
      var.certificate_map.name != null &&
      can(regex("^[a-z][a-z0-9-]{0,62}$", var.certificate_map.name))
    )
    error_message = "The name variable must be RFC1035 compliant and between 1 and 63 characters in length, and if specified, the hostname must be a valid DNS name."
  }
  default     = null
  description = <<-EOD
  If not null (default), a Certificate Map will be created as PRIMARY matcher for the generated certificates and with
  the specified options.
  NOTE: Only global Certificates can be added to a Certificate Manager Certificate Map; this variable will be have no
  effect if all Certificate Manager resources are regional.
  EOD
}
