# repo-template

![GitHub release](https://img.shields.io/github/v/release/memes/repo-template?sort=semver)
![GitHub last commit](https://img.shields.io/github/last-commit/memes/repo-template)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-3.0-4baaaa.svg)](CODE_OF_CONDUCT.md)

This repository contains common settings and actions that I tend to use in my
demos and projects.

> NOTE: Unless explicitly stated, this repo is not officially endorsed or supported by F5 Inc (or any prior employer).
> Feel free to open issues and I'll do my best to respond, but for product support you should go through F5's official
> channels.

## Setup

> NOTE: TODOs are sprinkled in the files and can be used to find where changes
> may be necessary.

1. Use as a template when creating a new GitHub repo, or copy the contents into
   a bare-repo directory.
2. Update `.pre-commit-config.yml` to add/remove plugins as necessary.
3. Modify README.md and CONTRIBUTING.md, change LICENSE as needed.
4. Review GitHub PR and issue templates.
5. If using `release-please` action, make these changes:
   1. In GitHub Settings:
      * _Settings_ > _Actions_ > _General_  > _Allow GitHub Actions to create and approve pull requests_ is checked
      * _Settings_ > _Secrets and Variables_ > _Actions_, and add `RELEASE_PLEASE_TOKEN` with PAT as a _Repository Secret_
   2. Modify [release-please action](.github/workflows/release-please.yml) to enable it
   3. Modify [release-please-config.json](release-please-config.json)] as needed
   4. Reset [.release-please-manifest.json](.release-please-manifest.json) to an empty file or starting version for package(s).
6. Remove all [CHANGELOG](CHANGELOG.md) entries.
7. Commit changes.
