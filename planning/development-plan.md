# Development roadmap

Current authorized deliverable: Step 1 qa-features draft specification, explicitly requested by the user with permission to draft missing details as unapproved assumptions. Only qa-features may be created. See phase-05-report.md for harness results and phase-0-report.md for unresolved readiness gates.

| Gate | Outputs | Required exit evidence |
|---|---|---|
| 0 | Tool/access inventory, missing-contract register | Required Step 1 tools/access verified; later tools recorded |
| 0.5A | Contract, steps/providers/scope config, state/evidence schemas, controller scripts | Schema, authorization, evidence and scope simulations |
| 0.5B | Antigravity/Codex/Claude native artifacts and adapters | Live discovery/configuration and enforcement checks per provider |
| 0.5C | Four skills, sync tool, evaluations and handoff | All exit criteria in verification-plan.md; no product code |
| 1 | qa-features specification, validated and untagged | OpenAPI, Hurl syntax, Gherkin, selectors, baseline, JSON schemas |
| Approval | Immutable feature tag | Explicit human approval; no autonomous tagging |
| 2 | sut-python and sut-node, Postgres, immutable shared frontend | Hurl, idempotent seeds, UI parity, bundle digests |
| 3 | qa-python: pytest-bdd, Playwright/Selenium | 3 scenarios × 2 drivers × 2 SUTs = 12 passes; complete observer |
| 4 | qa-typescript: Cypress | 3 scenarios × 2 SUTs = 6 passes; compatible results |
| 5 | Tracker CLI in qa-features/tools | Dry-run, explicitly authorized sandbox comment, idempotency, no status transition |
| 6 | Central workflow and campaign aggregation | Six matrix jobs, single campaign report, failure paths, no model calls |
| 7 | Immutable smoke release | Digests, clean-machine reproduction, 18 passes, rollback |

Each implementation step requires its predecessor and explicit authorization. Step 2 additionally requires approved immutable feature_ref. Keep feature_ref/tooling_ref and harness revision provenance in evidence. Install and verify native instructions/adapters when each repository is created.

Step 1 outputs: README.md, openapi.yml, selectors.json, api-expectations.yaml, api/auth.hurl, data/baseline.json, features/auth/login.feature, schemas/results.schema.json, schemas/campaign.schema.json, tools/validate/. Governance remains separate from business contracts. No tracker or campaign-report stubs or framework step definitions in Step 1.
