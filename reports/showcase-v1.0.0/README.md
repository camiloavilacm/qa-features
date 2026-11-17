# Recorded evaluation: showcase v1.0.0

The qualified implementation snapshot is `171f1aba25c0e413b18a726fa1e4627bdb161c4a`. The [machine-readable summary](qualified-snapshot.json) records 60 shared harness tests (including 22 outcome tests), five isolated-checkout collector checks, six scope audits, and the six registered acceptance checks. The [real agent outcome](agent-outcome.json) shows the versioned structure; its references belong to that snapshot's retained evidence.

Both the [initial smoke run](https://github.com/camiloavilacm/qa-features/actions/runs/44108586904/attempts/1) and [independent reproduction](https://github.com/camiloavilacm/qa-features/actions/runs/44109187867) passed all 18 scenarios and both rollback sequences. The [intentional failed rerun](https://github.com/camiloavilacm/qa-features/actions/runs/44108586904/attempts/2) proved that unavailable rollback prevents publication and updates the same report. A red conclusion on that attempt is expected.

A subsequent fresh-clone local first run executed the three Playwright authentication scenarios against a new disposable Python SUT on macOS/Apple Silicon. It required no development signing key or AI account. Follow the [first-run instructions](../../docs/first-run.md).

The final publication snapshot, exact source revisions, final hosted evidence and checksums are attached to the [showcase release](https://github.com/camiloavilacm/qa-features/releases). These assets remain available independently of short-lived Actions artifacts while the repository owner retains the release. The tracked summary above is historical qualification, not a claim that every later commit was already tested.

Live Claude remains NOT RUN under the artifacts-only exception. Hosted reproduction is Ubuntu 24.04/Linux amd64. Rollback covers immutable synthetic images with unchanged schema, not production migration rollback. Agent Control is deferred. Operator HMAC keys and deployment credentials are not distributed.
