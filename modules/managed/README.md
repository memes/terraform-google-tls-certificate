# Google Cloud managed SSL Certificates module

TBD
<!-- markdownlint-disable MD033 MD034 MD060 -->
<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.5 |
| <a name="requirement_google"></a> [google](#requirement\_google) | >= 7.1 |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [google_certificate_manager_certificate.managed](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/certificate_manager_certificate) | resource |
| [google_certificate_manager_dns_authorization.managed](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/certificate_manager_dns_authorization) | resource |
| [google_compute_managed_ssl_certificate.managed](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_managed_ssl_certificate) | resource |
| [google_compute_region_ssl_policy.managed](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_region_ssl_policy) | resource |
| [google_compute_ssl_policy.managed](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_ssl_policy) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_project_id"></a> [project\_id](#input\_project\_id) | The GCP project identifier where resources will be created | `string` | n/a | yes |
| <a name="input_certificate_manager"></a> [certificate\_manager](#input\_certificate\_manager) | n/a | <pre>object({<br/>    name        = string<br/>    region      = optional(string)<br/>    description = optional(string)<br/>    type        = optional(string)<br/>  })</pre> | `null` | no |
| <a name="input_domains"></a> [domains](#input\_domains) | n/a | `list(string)` | `null` | no |
| <a name="input_labels"></a> [labels](#input\_labels) | An optional map of label key:value pairs to assign to the Google resources. Default is an empty map. | `map(string)` | `{}` | no |
| <a name="input_ssl_certificate"></a> [ssl\_certificate](#input\_ssl\_certificate) | If not null, a global Compute Engine SSL Certificate will be created for key name given, valid for the domains<br/>provided. | <pre>object({<br/>    name        = string<br/>    description = optional(string)<br/>  })</pre> | `null` | no |
| <a name="input_ssl_policy"></a> [ssl\_policy](#input\_ssl\_policy) | If not null (default), a global Compute Engine SSL policy will be created with the specified options. The policy will be<br/>regional if the region field is not empty, global otherwise. | <pre>object({<br/>    name            = string<br/>    description     = optional(string, "TLS Policy for F5 DevCentral Demos")<br/>    region          = optional(string)<br/>    profile         = optional(string, "MODERN")<br/>    min_tls_version = optional(string, "TLS_1_2")<br/>    custom_features = optional(list(string))<br/>  })</pre> | `null` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_certificate_manager_id"></a> [certificate\_manager\_id](#output\_certificate\_manager\_id) | The Certificate Manager identifier or null. |
| <a name="output_dns_challenges"></a> [dns\_challenges](#output\_dns\_challenges) | n/a |
| <a name="output_ssl_certificate_self_link"></a> [ssl\_certificate\_self\_link](#output\_ssl\_certificate\_self\_link) | The Compute Engine SSL Certificate self-link or null. |
| <a name="output_ssl_policy_self_link"></a> [ssl\_policy\_self\_link](#output\_ssl\_policy\_self\_link) | A self-link URL for the created global or regional Google SSL Policy resource, or null. |
<!-- END_TF_DOCS -->
<!-- markdownlint-enable MD033 MD034 MD060 -->
