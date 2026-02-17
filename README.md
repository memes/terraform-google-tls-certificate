# Configure TLS certificate for Google Cloud and F5 scenarios

![GitHub release](https://img.shields.io/github/v/release/memes/terraform-google-tls-certificate?sort=semver)
![GitHub last commit](https://img.shields.io/github/last-commit/memes/terraform-google-tls-certificate)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-3.0-4baaaa.svg)](CODE_OF_CONDUCT.md)

> NOTE: Unless explicitly stated, this repo is not officially endorsed or supported by F5 Inc (or any prior employer).
> Feel free to open issues and I'll do my best to respond, but for product support you should go through F5's official
> channels.

TBD
<!-- markdownlint-disable MD033 MD034 MD060 -->
<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.5 |
| <a name="requirement_google"></a> [google](#requirement\_google) | >= 7.1 |
| <a name="requirement_tls"></a> [tls](#requirement\_tls) | >= 4.2 |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [google_certificate_manager_certificate.tls](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/certificate_manager_certificate) | resource |
| [google_compute_region_ssl_certificate.tls](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_region_ssl_certificate) | resource |
| [google_compute_region_ssl_policy.tls](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_region_ssl_policy) | resource |
| [google_compute_ssl_certificate.tls](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_ssl_certificate) | resource |
| [google_compute_ssl_policy.tls](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_ssl_policy) | resource |
| [google_secret_manager_regional_secret.cert](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_regional_secret) | resource |
| [google_secret_manager_regional_secret.json](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_regional_secret) | resource |
| [google_secret_manager_regional_secret.key](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_regional_secret) | resource |
| [google_secret_manager_regional_secret_version.cert](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_regional_secret_version) | resource |
| [google_secret_manager_regional_secret_version.json](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_regional_secret_version) | resource |
| [google_secret_manager_regional_secret_version.key](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_regional_secret_version) | resource |
| [google_secret_manager_secret.cert](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_secret) | resource |
| [google_secret_manager_secret.json](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_secret) | resource |
| [google_secret_manager_secret.key](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_secret) | resource |
| [google_secret_manager_secret_version.cert](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_secret_version) | resource |
| [google_secret_manager_secret_version.json](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_secret_version) | resource |
| [google_secret_manager_secret_version.key](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_secret_version) | resource |
| [tls_cert_request.tls](https://registry.terraform.io/providers/hashicorp/tls/latest/docs/resources/cert_request) | resource |
| [tls_locally_signed_cert.tls](https://registry.terraform.io/providers/hashicorp/tls/latest/docs/resources/locally_signed_cert) | resource |
| [tls_private_key.ca](https://registry.terraform.io/providers/hashicorp/tls/latest/docs/resources/private_key) | resource |
| [tls_private_key.tls](https://registry.terraform.io/providers/hashicorp/tls/latest/docs/resources/private_key) | resource |
| [tls_self_signed_cert.ca](https://registry.terraform.io/providers/hashicorp/tls/latest/docs/resources/self_signed_cert) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_project_id"></a> [project\_id](#input\_project\_id) | The GCP project identifier where resources will be created | `string` | n/a | yes |
| <a name="input_annotations"></a> [annotations](#input\_annotations) | An optional map of annotation key:value pairs to assign to the secret resources.<br/>Default is an empty map. | `map(string)` | `{}` | no |
| <a name="input_certificate_manager"></a> [certificate\_manager](#input\_certificate\_manager) | n/a | <pre>map(object({<br/>    name        = optional(string)<br/>    region      = optional(string)<br/>    description = optional(string)<br/>  }))</pre> | `null` | no |
| <a name="input_labels"></a> [labels](#input\_labels) | An optional map of label key:value pairs to assign to the Google resources. Default is an empty map. | `map(string)` | `{}` | no |
| <a name="input_requests"></a> [requests](#input\_requests) | A map of common name to a list of DNS names and/or IP addresses that will be added to the generated certificates. For<br/>each common-name key a self-signed TLS certificate and key will be generated. The optional description will be added<br/>to any Google Cloud resources associated with the TLS certificate. | <pre>map(object({<br/>    dns_names    = optional(list(string))<br/>    ip_addresses = optional(list(string))<br/>  }))</pre> | `{}` | no |
| <a name="input_secret_manager"></a> [secret\_manager](#input\_secret\_manager) | Define which Secret Manager secrets, if any, to create for each generated TLS cert:key pair. By default, only a secret<br/>for the TLS key will be created. | <pre>map(object({<br/>    prefix = optional(string)<br/>    region = optional(string)<br/>    key    = optional(bool, true)<br/>    cert   = optional(bool, false)<br/>    json   = optional(bool, false)<br/>  }))</pre> | `null` | no |
| <a name="input_ssl_certificate"></a> [ssl\_certificate](#input\_ssl\_certificate) | If not null, a Compute Engine SSL Certificate will be created for each generated TLS certificate. The SSL Certificate<br/>will be global unless the region field is not empty. | <pre>map(object({<br/>    prefix      = optional(string)<br/>    region      = optional(string)<br/>    description = optional(string)<br/>  }))</pre> | `null` | no |
| <a name="input_ssl_policy"></a> [ssl\_policy](#input\_ssl\_policy) | If not null (default), a Compute Engine SSL policy will be created with the specified options. The policy will be<br/>regional if the region field is not empty, global otherwise. | <pre>object({<br/>    name            = string<br/>    description     = optional(string, "TLS Policy for F5 DevCentral Demos")<br/>    region          = optional(string)<br/>    profile         = optional(string, "MODERN")<br/>    min_tls_version = optional(string, "TLS_1_2")<br/>    custom_features = optional(list(string))<br/>  })</pre> | `null` | no |
| <a name="input_subject"></a> [subject](#input\_subject) | An optional set of subject parameters to include in the generated CA certificate. This same set, excluding the common<br/>name, will be used in each TLS certificate generated. Any blank fields will be replaced by an F5 testing value. | <pre>object({<br/>    common_name         = optional(string, "Testing CA")<br/>    organization        = optional(string)<br/>    organizational_unit = optional(string)<br/>    locality            = optional(string)<br/>    province            = optional(string)<br/>    country             = optional(string)<br/>  })</pre> | <pre>{<br/>  "common_name": "Testing CA",<br/>  "country": "US",<br/>  "locality": "Seattle",<br/>  "organization": "F5, Inc",<br/>  "organizational_unit": "F5 DevCentral Demos",<br/>  "province": "Washington"<br/>}</pre> | no |
| <a name="input_tls_options"></a> [tls\_options](#input\_tls\_options) | NOTE: For maximum compatibility with regional, global, Certificate Manager, and Compute Engine SSL Certificates, the<br/>module will create TLS certificates with ECDSA P-256 keys by default. The key\_type field can be used to select a<br/>different key curve or size.<br/>See Google documentation for compatibility: https://docs.cloud.google.com/load-balancing/docs/ssl-certificates#key-types. | <pre>object({<br/>    key_type  = optional(string, "P-256")<br/>    ttl_hours = optional(number, 48)<br/>    allowed_uses = optional(list(string), [<br/>      "digital_signature",<br/>      "client_auth",<br/>      "server_auth",<br/>    ])<br/>  })</pre> | `null` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_ca_cert"></a> [ca\_cert](#output\_ca\_cert) | The CA certificate in PEM format. |
| <a name="output_certificate_manager_ids"></a> [certificate\_manager\_ids](#output\_certificate\_manager\_ids) | A map of Certificate Manager identifiers for each TLS certificate, keyed by common name. |
| <a name="output_certificates"></a> [certificates](#output\_certificates) | The map of generated TLS certificate PEMs, keyed by common name. |
| <a name="output_secret_ids"></a> [secret\_ids](#output\_secret\_ids) | A map of Secret Manager Secret identifiers for each TLS certificate, key, or JSON representation of the pair, keyed by<br/>common name. |
| <a name="output_ssl_certificate_self_links"></a> [ssl\_certificate\_self\_links](#output\_ssl\_certificate\_self\_links) | A map of global or regional Compute Engine SSL Certificate self-links, keyed by common name. |
| <a name="output_ssl_policy_self_link"></a> [ssl\_policy\_self\_link](#output\_ssl\_policy\_self\_link) | A self-link URL for the created global or regional Google SSL Policy resource, or null. |
<!-- END_TF_DOCS -->
<!-- markdownlint-enable MD033 MD034 MD060 -->
