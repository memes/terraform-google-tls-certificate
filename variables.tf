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

variable "annotations" {
  type     = map(string)
  nullable = true
  validation {
    # GCP resource annotations keys must begin and end with a lowercase alphanumeric character,
    # and period, underscore, or hyphen characters; the key must be <= 63 characters in length.
    # The values have only a size constraint, which is unenforceable here.
    condition     = var.annotations == null ? true : alltrue([for k, v in var.annotations : can(regex("^[a-z0-9][a-z0-9._-]{0,61}[a-z0-9]?$", k))])
    error_message = "Each label key:value pair must match GCP requirements."
  }
  default     = {}
  description = <<EOD
An optional map of annotation key:value pairs to assign to the secret resources.
Default is an empty map.
EOD
}

variable "requests" {
  type = map(object({
    dns_names    = optional(list(string))
    ip_addresses = optional(list(string))
  }))
  nullable = false
  validation {
    condition = alltrue(
      [for k, v in var.requests : length(k) <= 64 &&
        (try(length(var.requests.dns_names), 0) == 0 ? true : alltrue(
          [for name in var.requests.dns_names :
            can(regex("^(?:\\*\\.)?(?:[a-z0-9][a-z0-9-]{0,61}[a-z0-9]\\.)+[a-z]{2,63}$", name))
          ])) && (try(length(var.requests.ip_addresses), 0) == 0 ? true : alltrue(
          [for address in var.requests.ip_addresses : can(cidrhost(address, 0))]
        ))
    ])
    error_message = "Each request entry must have a valid common name as key, and if DNS names and/or IP addresses are provided they must be valid."
  }
  default     = {}
  description = <<-EOD
  A map of common name to a list of DNS names and/or IP addresses that will be added to the generated certificates. For
  each common-name key a self-signed TLS certificate and key will be generated. The optional description will be added
  to any Google Cloud resources associated with the TLS certificate.
  EOD
}

variable "subject" {
  type = object({
    common_name         = optional(string, "Testing CA")
    organization        = optional(string)
    organizational_unit = optional(string)
    locality            = optional(string)
    province            = optional(string)
    country             = optional(string)
  })
  nullable = true
  validation {
    condition = var.subject == null ? true : (
      (try(var.subject.common_name, null) == null ? true : can(regex("^[[:alnum:]][^[:cntrl:]]{0,63}$", var.subject.common_name))) &&
      (try(var.subject.organization, null) == null ? true : can(regex("^[[:alnum:]][^[:cntrl:]]{0,63}$", var.subject.organization))) &&
      (try(var.subject.organizational_unit, null) == null ? true : can(regex("^[[:alnum:]][^[:cntrl:]]{0,63}$", var.subject.organizational_unit))) &&
      (try(var.subject.locality, null) == null ? true : can(regex("^[[:alnum:]][^[:cntrl:]]{0,127}$", var.subject.locality))) &&
      (try(var.subject.province, null) == null ? true : can(regex("^[[:alnum:]][^[:cntrl:]]{0,127}$", var.subject.province))) &&
      (try(var.subject.country, null) == null ? true : can(regex("^[[:alpha:]]{1,2}$", var.subject.country)))
    )
    error_message = "The subject fields must be x509 compatible."
  }
  default = {
    common_name         = "Testing CA"
    organization        = "F5, Inc"
    organizational_unit = "F5 DevCentral Demos"
    locality            = "Seattle"
    province            = "Washington"
    country             = "US"
  }
  description = <<-EOD
  An optional set of subject parameters to include in the generated CA certificate. This same set, excluding the common
  name, will be used in each TLS certificate generated. Any blank fields will be replaced by an F5 testing value.
  EOD
}

variable "tls_options" {
  type = object({
    key_type  = optional(string, "P-256")
    ttl_hours = optional(number, 48)
    allowed_uses = optional(list(string), [
      "digital_signature",
      "client_auth",
      "server_auth",
    ])
  })
  nullable = true
  validation {
    condition     = var.tls_options == null ? true : can(regex("^(?:(ECDSA)? ?P[ -]?(256|384)|(RSA)[ -]?(2048|3072|4096))$", coalesce(upper(var.tls_options.key_type), "P-256")))
    error_message = "Each entry must have a key_type that is one of RSA-2048, RSA-3072, RSA-4096, ECDSA P-256, or ECDSA P-384."
  }
  default     = null
  description = <<-EOD
  NOTE: For maximum compatibility with regional, global, Certificate Manager, and Compute Engine SSL Certificates, the
  module will create TLS certificates with ECDSA P-256 keys by default. The key_type field can be used to select a
  different key curve or size.
  See Google documentation for compatibility: https://docs.cloud.google.com/load-balancing/docs/ssl-certificates#key-types.
  EOD
}

variable "secret_manager" {
  type = map(object({
    prefix = optional(string)
    region = optional(string)
    key    = optional(bool, true)
    cert   = optional(bool, false)
    json   = optional(bool, false)
  }))
  nullable = true
  validation {
    condition     = var.secret_manager == null ? true : alltrue([for k, v in var.secret_manager : v.prefix == null ? true : can(regex("^[a-z][a-z0-9-]{0,57}$", v.prefix))])
    error_message = "The name variable must be RFC1035 compliant and between 1 and 58 characters in length."
  }
  default     = null
  description = <<-EOD
  Define which Secret Manager secrets, if any, to create for each generated TLS cert:key pair. By default, only a secret
  for the TLS key will be created.
  EOD
}

variable "certificate_manager" {
  type = map(object({
    name        = optional(string)
    region      = optional(string)
    description = optional(string)
  }))
  nullable = true
  validation {
    condition     = var.certificate_manager == null ? true : alltrue([for k, v in var.certificate_manager : v.name == null ? true : can(regex("^[a-z][a-z0-9-]{0,62}$", v.name))])
    error_message = "The name variable must be RFC1035 compliant and between 1 and 63 characters in length."
  }
  default = null
}

variable "ssl_certificate" {
  type = map(object({
    prefix      = optional(string)
    region      = optional(string)
    description = optional(string)
  }))
  nullable = true
  validation {
    condition     = var.ssl_certificate == null ? true : alltrue([for k, v in var.ssl_certificate : v.prefix == null ? true : can(regex("^[a-z][a-z0-9-]{0,61}$", v.prefix))])
    error_message = "The name variable must be RFC1035 compliant and between 1 and 63 characters in length."
  }
  default     = null
  description = <<-EOD
  If not null, a Compute Engine SSL Certificate will be created for each generated TLS certificate. The SSL Certificate
  will be global unless the region field is not empty.
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
  If not null (default), a Compute Engine SSL policy will be created with the specified options. The policy will be
  regional if the region field is not empty, global otherwise.
  EOD
}
