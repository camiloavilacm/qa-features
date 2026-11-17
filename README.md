# QA platform — approved SEED-1

All seven implementation steps are complete: the approved authentication specification, two reference SUTs, Python and Cypress runners, private issue reporting, a six-slot campaign, and an immutable synthetic smoke release with clean-machine reproduction and image rollback. Current maintenance and acceptance status are recorded separately in the activated development harness and its retained evidence.

## Repository map

| Repository | Responsibility |
|---|---|
| qa-features (this repository) | Framework-independent contracts, canonical development governance, campaign aggregation/reporting, smoke orchestration |
| [sut-python](https://github.com/camiloavilacm/sut-python) | Python reference application, PostgreSQL, frozen frontend and baseline provisioning |
| [sut-node](https://github.com/camiloavilacm/sut-node) | Node reference application with the same approved contract and frontend |
| [qa-python](https://github.com/camiloavilacm/qa-python) | Playwright and Selenium scenario execution and sanitized observations |
| [qa-typescript](https://github.com/camiloavilacm/qa-typescript) | Cypress scenario execution and sanitized observations |

The five repositories are private and independent. Runners pin the approved feature commit through the relative GitHub submodule URL `../qa-features.git`. Campaign/release orchestration pins runner and SUT source separately. QA execution has no runtime model calls, auto-healing or silent assertion changes.

## Start here

- [Specification validation](tools/validate/validate.py): structural/semantic specification checks and fixtures; this command does not execute a SUT.
- [Campaign operations](tools/campaign/README.md): six hosted slots, 18 real scenarios, current-attempt aggregation, failure handling and private reports.
- [Smoke release and reproduction](tools/release/README.md): exact tool/image pins, immutable OCI bundles, real rollback and the intentional negative-check profile.
- [Development harness](harness/README.md): operator activation, authorization, single ownership, registered checks, evidence validation and scope auditing.
- [Approved Step 1 history](docs/seed-1-approval-history.md): the original approval-time README, preserved verbatim. Its deferred-work statements describe that historical snapshot.

## Validate the specification locally

From this repository root, use an isolated Python environment and provide Hurl/hurlfmt on PATH:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r tools/validate/requirements.txt
.venv/bin/python tools/validate/validate.py --check all
```

Specification fixtures do not count as executed QA results. Actual acceptance requires schema-valid scenario artifacts, complete observations, source/image provenance and the registered evidence checks. The hosted smoke profile is Ubuntu 24.04 linux/amd64 with its exact Python/dependency/browser versions frozen under [tools/release](tools/release/README.md).

## Run a private hosted campaign

An operator with private repository/workflow access can dispatch the committed workflows. Read-only per-repository deploy keys provide source access; job-scoped built-in tokens provide package/report permissions. Token and private-key values belong in operator/Actions configuration.

```sh
.venv/bin/python tools/campaign/launch.py dispatch --record /absolute/path/to/campaign-run.json --report-issue 1
.venv/bin/python tools/campaign/launch.py wait --record /absolute/path/to/campaign-run.json
.venv/bin/python tools/campaign/launch.py download --record /absolute/path/to/campaign-run.json --output /absolute/path/to/new-campaign-archive
```

The development campaign defaults to private `qa-features#1`. The smoke workflow defaults to private `qa-features#2`; its `report_issue` input selects another existing issue in this same repository. Acceptance validates the selected destination from campaign provenance for both successful and failed reports. Each campaign maintains one comment across attempts and leaves issue status/fields unchanged.

For smoke dispatch, use `tools/release/launch.py` with `--report-issue <issue-number>` and archive each attempt before rerunning. For independent reproduction, pass the published OCI digest with `--bundle` and a named `--ref` that points to the exact `release_tooling_ref` commit. The workflow rejects a tooling/manifest mismatch. See the release guide for all commands and the full-rerun failure check.

## Contract and approval integrity

SEED-1 contains AC-1 registration, AC-2 baseline login and AC-3 rejected login with an error, empty browser authentication state and protected-route denial. The independent Hurl contract also requires unauthenticated `GET /user` to return 401. The immutable synthetic baseline and fresh registration identities remain mandatory. Network evidence contains sanitized method/path/status/authorization-presence projections.

The human-approved annotated tag `seed-1-approved-v1` remains pinned to `12a55fb4b9312303378af72f96a28734b6b9ec9a`. Its [approval receipt](governance/approvals/seed-1-approved-v1.json), frozen specification files and [historical README](docs/seed-1-approval-history.md) retain the accepted assumptions and original approval wording. Tooling changes do not grant business approval or permission to create/move a tag.

The committed development state is a distribution/approval-time snapshot; the active operator's persisted state and matching external authorization determine writable scope. A fresh checkout requires operator provisioning. Runtime QA CI works from the committed private sources without untracked parent-workspace files or a development evidence key.

Smoke verification covers synthetic Linux/amd64 image artifacts and an unchanged application schema. It records host/configuration/development-harness provenance and does not claim a production deployment or schema-migration rollback. Live Claude remains **NOT RUN** under the approved artifacts-only exception. Further development requires explicit scope and the normal preflight/evidence/audit gates.
