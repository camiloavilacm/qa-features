# Immutable synthetic smoke release — Step 7

This profile supports clean **Ubuntu 24.04, linux/amd64** environments. It consumes the frozen application images by registry digest; it never rebuilds application images. Baseline and candidate use the same approved application source/schema but distinct previously verified image artifacts. This first release establishes its rollback baseline from exact versioned Step 6 evidence (the prior attempt artifact is no longer available through Actions); it does not claim an earlier production/tagged release or schema-migration rollback.

The two core manifests bind approved feature/source revisions, application image/config digests, served frontend hashes, configuration source hashes, exact QA tool versions, Python dependency hashes, Node/npm integrity and browser/driver/Hurl archive/executable hashes. Synthetic credentials are freshly generated per clean environment, and their non-reversible configuration fingerprint is preserved across rollback. Secret values are never included in bundles. The host image/version is recorded; reproduction does not claim a bit-for-bit rebuild of the host OS or application image.

The smoke workflow creates an immutable baseline OCI bundle, runs all six slots/18 unchanged scenarios, and independently tests baseline -> candidate -> baseline on both SUTs with the same database/configuration. Every rollback phase executes the original seven-request Hurl contract, including unauthenticated GET /user -> 401, and checks served frontend bytes and immutable baseline-row preservation. Each QA job uses fresh isolated environments/caches. Python wheels are hash-locked; official browser archives and installed executables are checked. Playwright's installer receives only checksum-verified assets from a temporary loopback mirror that is stopped before tests; application HTTP is never stubbed.

A private, content-addressed OCI bundle is published only after those checks pass. It contains manifests, locks, actual smoke/rollback evidence, configuration and development-harness provenance, and the previous baseline-bundle reference. GitHub artifacts are convenient evidence copies; reproduction uses the immutable OCI digest and source commit rather than relying on their retention. No new Git/feature/release tag is created. Source and the original approved tag remain independently pinned.

To reproduce, dispatch smoke.yml using a named branch/ref that resolves to release_record.release_tooling_ref, with reproduce_bundle set to the published ghcr.io/camiloavilacm/qa-smoke-release@sha256:... digest. GitHub workflow dispatch requires a named ref; the release context verifies its exact commit against the bundle. Public checkouts require no deploy keys; package-scoped job tokens provide image access; the final reporting job uses separate issue permissions. A second set of fresh hosted machines pulls the sealed bundle, verifies all payload digests/manifests, and repeats all 18 scenarios and both rollback sequences with identical application-image/toolchain pins. No untracked parent workspace file or development recorder key is required at runtime. Model/agent calls and auto-healing are absent from QA CI.

Supported prerequisites are Linux/amd64 Docker/Compose, the pinned Python toolchain, private GitHub/package authorization and the documented Ubuntu system libraries. No production database is involved. The workflows create and remove only their disposable per-run database volumes. Registry artifacts remain subject to operator retention; immutable digests identify contents, not an availability guarantee.

Five registered acceptance checks — image-digests, reproduction, 18-passes, rollback, failure-reporting — require real hosted evidence from initial and bundle-reproduction runs. Deterministic fixture tests alone cannot complete the release gate. The approved feature remains seed-1-approved-v1 at 12a55fb4b9312303378af72f96a28734b6b9ec9a.

## Scoped maintenance: architecture findings 1 and 2

Rollback receipts bind campaign ID, numeric run ID/attempt, tooling commit and both manifest hashes. Both artifact upload/download names include the current attempt. Publication requires all upstream jobs to succeed; a matching receipt from another execution cannot substitute for a failed or missing rollback.

The issue reporter runs independently of release publication and distinguishes QA outcome from release outcome. It updates the same campaign comment on failed/incomplete attempts, including when current-attempt evidence is unavailable or invalid. A failed attempt never inherits an earlier attempt's verified-release claim. Report snapshots and publication receipts are retained in each smoke artifact.

For the explicit development negative check, dispatch with validation_failure_attempt=2 (normal default is 0). Attempt 1 exercises the full unchanged QA/rollback pipeline; a full rerun at attempt 2 deliberately makes both rollback jobs unavailable before they can write receipts. The QA matrix remains unchanged. The release gate must fail, publish no bundle, and update the same private comment to a failed release even if all 18 QA scenarios pass. No passing rollback is claimed for that intentional failure. Registered failure-reporting acceptance requires this actual hosted pass-to-failure transition in addition to fresh successful smoke and independent bundle reproduction.

## Configured private report destination

The workflow defaults to issue 2 in the current qa-features repository. The required report_issue input (CLI --report-issue) can select another existing issue in that same repository. Both successful and failed receipt validation use report_repository/report_issue from current-attempt provenance, check the exact comment identity/URL, and require the report's campaign marker to bind the same destination. A report for another issue or repository is rejected even when its other checks pass.

From qa-features, with private workflow/package/source access already configured:

```sh
.venv/bin/python tools/release/launch.py dispatch --record /absolute/path/to/smoke-run.json --report-issue 2 --failure-attempt 2
.venv/bin/python tools/release/launch.py wait --record /absolute/path/to/smoke-run.json
.venv/bin/python tools/release/launch.py download --record /absolute/path/to/smoke-run.json --output /absolute/path/to/new-initial-archive
.venv/bin/python tools/release/launch.py rerun --record /absolute/path/to/smoke-run.json
.venv/bin/python tools/release/launch.py wait --record /absolute/path/to/smoke-run.json --attempt 2
.venv/bin/python tools/release/launch.py download --record /absolute/path/to/smoke-run.json --output /absolute/path/to/new-failure-archive
```

Archive attempt 1 before the full rerun; prior Actions artifacts may not remain available. For independent reproduction, dispatch a separate run with --bundle set to the initial published digest and --ref set to a named ref at its exact tooling commit. Download it to a third fresh directory. Normal smoke dispatch omits --failure-attempt (default 0); the example above explicitly enables the development negative check. Select --report-issue 3 only when that alternate private report issue exists and is the intended destination. Development acceptance wiring is described in ../../harness/README.md.
