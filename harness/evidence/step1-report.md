# Step 1 — technically validated, untagged draft

Summary: created only qa-features. New missing details are explicitly unapproved assumptions, as authorized by the user. No approval tag, commit, remote or application implementation was created. Branch: validated (unborn).

## Added product tree

```text
qa-features/
├── README.md
├── openapi.yml
├── selectors.json
├── api-expectations.yaml
├── api/auth.hurl
├── data/baseline.json
├── features/auth/login.feature
├── schemas/{results,campaign}.schema.json
├── tools/validate/{validate.py,test_specification.py,requirements.txt}
├── governance/{source/,phase05-tested-source.tar,evidence/,manifest.json}
├── AGENTS.md, CLAUDE.md, MASTER-CONTRACT.md
├── .agents/, .claude/, .codex/, planning/
└── harness/{config/,schemas/,scripts/,evals/,state.json,evidence/}
```

Canonical governance and generated native copies are checked by hashes. The exact tested Phase 0.5 archive/evidence is preserved independently. The local environment uses pinned requirements and requires no parent files or cross-repository symlinks. Workspace controller changes before activation added Step 1 recording/gates, unborn-repository initialization and governance path support; no future-step implementation was added.

## Commands and results

Exact commands, cwd, exit codes and logs are in step1-commands.json. Seven registered checks: openapi, hurl, gherkin, selectors, baseline, json-schemas, governance. PASS: all seven; 34 harness tests; 7 specification mutation tests; 4 positive and 17 negative schema fixtures; selector coverage (10); Hurl syntax (7 request entries); source-only clean extraction; dependencies; state/schema/adapters/skill synchronization; local and workspace scope audits; repository Step 1 completion gate.

Codex and Antigravity discovery passed from this actual repository root. The initial Codex probe forbade its available read-only shell interface; a corrected prompt allowed read-only shell reads and passed without changing any specification. Both attempts are retained. Claude live checks are NOT RUN under the approved artifacts-only exception; its local files/copies validate statically.

NOT RUN: Hurl against live SUTs, browser scenarios, application authentication, observer runtime capture, runner executions, tracker/sandbox comments, campaign jobs, private GitHub/CI permissions or release reproduction. Schema fixtures are not actual QA executions. These checks belong to later explicitly authorized steps.

## Pending approval and remaining work

The assumptions in README.md — including AC-1/AC-2 mapping/tag syntax, UI routes/selectors/session convention, exact error/status choices, synthetic credentials and result/campaign fields — require explicit human business approval. Supplied SEED-1/AC-3 identifiers and frozen rules are preserved; no unavailable original wording is asserted to be approved. Technical validation is not feature approval. feature_ref/tooling_ref remain unset. GitHub origin and private CI access remain unconfigured for later steps.

sut-python, sut-node, qa-python and qa-typescript remain unbuilt. No framework step definitions, tracker CLI or campaign-report stubs exist. No model calls were added to QA CI. Development-native discovery used read-only coding-agent sessions only.

Work stopped at Step 1's technical-validation boundary. No approval tag or Step 2 execution is authorized by this report.
