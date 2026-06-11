# Changelog

## [0.2.0](https://github.com/memes/terraform-google-tls-certificate/compare/v0.1.1...v0.2.0) (2026-06-11)


### Features

* Add Cloud DNS RRs for Managed domains ([f98329a](https://github.com/memes/terraform-google-tls-certificate/commit/f98329a2a1321899b4ebd1c2f3370f06c651ea48))
* Add wildcard option to managed TLS module ([cfc4e4e](https://github.com/memes/terraform-google-tls-certificate/commit/cfc4e4e2af1590bc91cc14549c11be74cf375731))
* Add wildcard option to managed TLS module ([defad90](https://github.com/memes/terraform-google-tls-certificate/commit/defad9005386bf4e136f498363db05b3e2bf7dc1))
* Default to LB authorization for managed TLS ([d4dea08](https://github.com/memes/terraform-google-tls-certificate/commit/d4dea081d22c511a9ba25b81f3b951ae4ada8f2c))
* Support creation of Certificate Map ([7ff87c2](https://github.com/memes/terraform-google-tls-certificate/commit/7ff87c2ca7aacbc5e4308da8ea740cfd28a1c94f))


### Bug Fixes

* Make sure managed certificate maps are global ([1f78ddc](https://github.com/memes/terraform-google-tls-certificate/commit/1f78ddc181376fded4d8840c5fb263ef27a0322e))
* Prefer sets for domains and requests SANs ([b87060c](https://github.com/memes/terraform-google-tls-certificate/commit/b87060c86a0871c4c7b6289bd6295db85a6515af))
* Remove empty domains in wildcard handling ([c7420b9](https://github.com/memes/terraform-google-tls-certificate/commit/c7420b948b482106105835d1bfaa044da24e77ca))

## [0.1.1](https://github.com/memes/terraform-google-tls-certificate/compare/v0.1.0...v0.1.1) (2026-03-04)


### Bug Fixes

* The DNS challenges output is not sensitive ([0f26ca5](https://github.com/memes/terraform-google-tls-certificate/commit/0f26ca5c6d25bbe3659ebe9c70f15a67e8e5a040))
* The DNS challenges output is not sensitive ([49e2ce2](https://github.com/memes/terraform-google-tls-certificate/commit/49e2ce2318927df8b1073ffdb0e18c678a257e65))

## [0.1.0](https://github.com/memes/terraform-google-tls-certificate/compare/v0.0.1...v0.1.0) (2026-02-25)


### Features

* Google managed SSL certificates ([c62a340](https://github.com/memes/terraform-google-tls-certificate/commit/c62a34076325bddf0cce6361abe3cdb055033e33))
* Self-managed TLS certificates with Google ([2964e67](https://github.com/memes/terraform-google-tls-certificate/commit/2964e6790427f663f48c9ce9d689386859d3e20a))


### Bug Fixes

* Add region support to "managed" SSL Policy ([af307c9](https://github.com/memes/terraform-google-tls-certificate/commit/af307c97ea24cc4a850dade4d7835bfb71d1b5a3))
* Add regional SSL policy to output ([8957f2b](https://github.com/memes/terraform-google-tls-certificate/commit/8957f2bf2966b3ff9576727fdc8c571c0896df3a))
