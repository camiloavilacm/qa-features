# Evaluate the showcase

This is an educational example of developing automation frameworks with AI assistance. Playwright, Selenium and Cypress are alternative implementations to study. The combined campaign checks their consistency; adopting all three is optional.

## Read the results first

1. Read the [project overview](README.md) and [recorded evaluation](reports/showcase-v1.0.0/README.md).
2. Inspect the [shared authentication scenarios](features/auth/login.feature): registration, baseline login, and rejected login.
3. Choose [Playwright/Selenium](https://github.com/camiloavilacm/qa-python) or [Cypress](https://github.com/camiloavilacm/qa-typescript). Trace an acceptance criterion to an assertion and a sanitized observation.
4. Inspect the [agent-outcome contract](harness/schemas/agent-outcome.schema.json), [collector workflow](harness/outcomes.md), and [real recorded outcome](reports/showcase-v1.0.0/agent-outcome.json). Shape validation and evidence verification answer different questions.
5. Download the durable evidence from the [showcase release](https://github.com/camiloavilacm/qa-features/releases). It includes a passing smoke attempt, independent reproduction and an intentional failed rerun. The failed attempt is expected evidence, not an unexplained broken build.

The tracked evaluation records the previously qualified tooling snapshot. The release assets record the final publication snapshot and exact revisions. Runtime SUT/runner pins can differ from their latest governance/documentation commits; both are listed explicitly.

## Run one framework example

Follow the [tested first-run guide](docs/first-run.md). It starts a disposable Python application and runs three Playwright scenarios. Reading or running the example does not require a development authorization file, recorder key, model subscription, or all three frameworks.

The automated lightweight checks run on pushes and pull requests. The full hosted campaign remains an operator workflow; sealed OCI artifacts may require registry authorization even though source and downloadable evaluation evidence are public; fork contributors do not need or receive source deploy keys, issue-write credentials, or package credentials for lightweight validation.

## Verify downloaded evidence offline

Use the exact tooling revision recorded in the release manifest. The publication tag is separate from the immutable approved feature tag. Clone with Git history/tags available, create an isolated Python environment, and install `tools/validate/requirements.txt`. Download `showcase-evidence.zip` and `SHA256SUMS` from the release, verify the archive checksum, and extract the archive so that `initial`, `reproduction`, and `failure` live under `harness/evidence/review/`:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r tools/validate/requirements.txt
.venv/bin/python tools/review/verify.py --evidence harness/evidence/review
```

This rechecks scenario artifacts, source/image provenance, rollback, reproduction and report integrity against the checked-out tooling commit. It requires no running SUT or private recorder key. File hashes establish content integrity; operator HMAC attestations are not independently verifiable without the private key, which is deliberately not distributed. GitHub run links supply the external execution record. These checks do not establish production readiness or prove which model authored text.

## Suggested evaluation questions

- Can you follow one requirement from specification through implementation, assertion, observation, and report?
- Does missing or invalid evidence prevent a passing conclusion?
- Are human approval and agent authority separate from an agent's claims?
- Can you repeat the local example using the documented commands?
- Are pinned versions and limitations visible, including Linux/amd64 hosted reproduction, unchanged-schema image rollback, and Claude's artifacts-only exception?

Agent Control integration is intentionally deferred. There are no runtime model calls or auto-healing in QA execution. No further feature implementation is required to evaluate this showcase.
