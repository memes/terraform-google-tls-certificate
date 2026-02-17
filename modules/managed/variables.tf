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
    name        = string
    region      = optional(string)
    description = optional(string)
    type        = optional(string)
  })
  nullable = true
  validation {
    condition     = var.certificate_manager == null ? true : can(regex("^[a-z][a-z0-9-]{0,62}$", var.certificate_manager.name))
    error_message = "The name field must be RFC1035 compliant and between 1 and 63 characters in length."
  }
  default = null
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
  If not null (default), a global Compute Engine SSL policy will be created with the specified options.
  EOD
}
