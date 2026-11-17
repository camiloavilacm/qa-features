# Development harness — current operating guide

This controller governs coding-agent development and is separate from QA execution CI. This guide is distributed as `qa-features/harness/README.md`; its links and commands refer to that distribution. The seven implementation steps are complete; current maintenance work still requires explicit user authorization. Read [MASTER-CONTRACT.md](../MASTER-CONTRACT.md), persisted `harness/state.json`, the matching external human receipt and `harness/config/steps.yaml` before writes. The committed state is a distribution snapshot; a fresh checkout requires operator provisioning of its own authorization, baseline, evidence recorder and owner. Never infer activation from a completed roadmap or an agent-edited state.

## Registered verification profiles

| Profile | Execution repository | Required check IDs |
|---|---|---|
| Phase 0.5 readiness | Canonical development controller | adapters, evals, codex-native, claude-artifacts, antigravity-native, native-cycle |
| Step 1 specification | qa-features | openapi, hurl, gherkin, selectors, baseline, json-schemas, governance |
| Step 2 SUTs | Each SUT repository | hurl, seeds, ui-parity, digests |
| Step 3 Python runner | qa-python | 12-passes, observer-complete |
| Step 4 Cypress runner | qa-typescript | 6-passes, result-schema |
| Step 5 tracker | qa-features | dry-run, sandbox-comment, idempotency, no-transition |
| Step 6 campaign | qa-features | six-jobs, single-report, failure-paths, no-model-calls |
| Step 7 smoke/maintenance | qa-features | image-digests, reproduction, 18-passes, rollback, failure-reporting |

The executable registrations and active step policy are authoritative. Run a profile only from its registered repository under matching authorization. Repository-local adapters use their own persisted state/provenance; workspace-level scope auditing does not replace canonical qa-features acceptance. The workspace controller does not execute repository-only release checks.

## Isolated local setup

From qa-features, install the specification/controller dependencies in an isolated environment; provide Hurl/hurlfmt on PATH:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r tools/validate/requirements.txt
.venv/bin/python tools/validate/validate.py --check all
.venv/bin/python -m unittest discover -s harness/evals -p 'test_*.py' -v
```

These commands validate specifications and controller regressions. They do not provide actual SUT/browser acceptance. Campaign, tracker and release tooling now exist under `tools/`; framework-specific assertions stay in their runner repositories. See the [platform overview](../README.md), [campaign guide](../tools/campaign/README.md) and [release guide](../tools/release/README.md).

## Operator-controlled execution

`QA_AUTHORIZATION_FILE` must point to an external human receipt matching persisted authorization. `QA_EVIDENCE_KEY_FILE` must point to an external random recorder key of at least 32 bytes with permissions 0600. Neither value belongs in source control. Source/Git proofs, an original retained baseline and single writable ownership must also be valid before execution. Existing workstation records are operator-local and are not a fresh-checkout dependency.

For an explicitly activated Step 7 maintenance session with owner `codex-step7`:

```sh
export QA_AUTHORIZATION_FILE=/absolute/operator/path/authorization.json
export QA_EVIDENCE_KEY_FILE=/absolute/operator/path/evidence.key
export QA_STEP7_RUNS_FILE=/absolute/operator/path/smoke-runs.json
.venv/bin/python harness/scripts/preflight.py --step 7 --provider codex --owner codex-step7
.venv/bin/python harness/scripts/verify_step.py run --check image-digests
.venv/bin/python harness/scripts/verify_step.py run --check reproduction
.venv/bin/python harness/scripts/verify_step.py run --check 18-passes
.venv/bin/python harness/scripts/verify_step.py run --check rollback
.venv/bin/python harness/scripts/verify_step.py run --check failure-reporting
.venv/bin/python harness/scripts/verify_step.py validate
.venv/bin/python harness/scripts/verify_step.py gate
```

Use the actual authorized step/provider/owner from activated state. `QA_STEP7_RUNS_FILE` maps `initial`, `reproduction` and `failure` to distinct retained archive directories below this repository's `harness/evidence/`. Each archive includes actual run/job/artifact metadata, campaign artifacts and publication receipts. The failure archive is a later attempt of the initial campaign that deliberately lacks rollback evidence. The successful archives include verified release records and immutable bundle digests. See `tools/release/launch.py` for dispatch, full rerun, bounded wait and archive download.

Step 6 uses `QA_STEP6_RUNS_FILE` with its campaign archives. Other profiles have their own documented evidence prerequisites. Missing tools, observation or fresh execution evidence cannot PASS. The recorder captures commands, exit codes, logs and source fingerprints; signed validation checks artifact receipts again. A successful technical gate does not approve a business requirement, create a tag or authorize another step.

## Scope, ownership and provenance

Run the mandatory audit against the exact retained `state.baseline`:

```sh
qa_baseline="$(.venv/bin/python -c 'import json;print(json.load(open("harness/state.json"))["baseline"])')"
.venv/bin/python harness/scripts/scope_guard.py --baseline "$qa_baseline"
```

Auditing includes tracked/untracked files, empty directories, symlinks and Git references. It preserves the original content inventory; authorized source-reference checkpoints do not waive tag or unrelated-ref changes. A final audit cannot observe transient reverted writes or changes outside its inspected root.

Keep one writable owner. Use `ownership.py release/claim` and a structured handoff before a provider/owner transfer. Antigravity uses its scoped execution integration; Codex combines supported command rules with preflight/audits. These controls are not a universal filesystem sandbox. Claude remains artifacts-only and cannot become a writer until its live profile is explicitly activated and validated; see `.claude/ACTIVATION.md`.

`governance/source` retains the canonical source distributed into qa-features native artifacts and the shared controller. Generated/preserved hashes are checked by `governance/manifest.json` and `harness/provenance.json`; operational state/evidence are outside copy equivalence. The original Phase 0.5 archive and the approved Step 1 history remain separate preserved records. No parent untracked files or cross-repository symlinks are required.

Native-cycle checks can launch real provider sessions and consume credits; they are development readiness checks and are not part of QA execution CI. The approved profile retains Antigravity → Codex → Antigravity live evidence plus static Claude artifact validation. Live Claude is **NOT RUN**. Stop at the explicitly authorized development boundary after registered checks, signed validation/gate and the mandatory scope audit.
