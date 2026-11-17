# Agent Control evaluation

Review date: 2026-11-17. Status: documentation assessment; no installation, integration, or live compatibility tests performed.

## Recommendation: defer integration

Keep the existing development harness as the authority for authorization, ownership, evidence, and scope. Agent Control may merit a separately authorized, isolated pilot if a concrete need arises for centralized evaluation of instrumented development-agent calls. There is currently no demonstrated native interception path for this project's three coding-agent adapters. Adding a service without establishing that coverage would not establish enforcement.

This is an architectural inference from the current project and upstream documentation, not a measured runtime result. No Agent Control component belongs in the deterministic QA campaign under the current contract.

## Sources and reviewed version

The assessment reviews upstream main as documented on the review date. The exact commit is recorded below; future adoption must pin and reevaluate a specific release. Primary references:

- [Upstream repository and SDK examples](https://github.com/agentcontrol/agent-control)
- [Official overview](https://docs.agentcontrol.dev/core/overview)
- [Project master contract](../MASTER-CONTRACT.md)
- [Existing harness operations](../harness/README.md)

## Fit against current controls

| Concern | Existing project | Agent Control evidence and fit |
|---|---|---|
| Policy evaluation | Step policy, preflight, supported provider controls, final scope audit | Upstream documents centralized rules and pluggable evaluators around instrumented inputs/outputs. Potential supplement; not a filesystem sandbox. |
| Interception coverage | Provider-specific adapters with different supported semantics | SDK examples wrap calls with `@control()`. Native Codex, Antigravity, and Claude Code interception is unverified in this assessment. |
| Authorization and ownership | External human receipt and one writable owner | A control decision cannot replace the human approval record or acquire ownership. No equivalent project integration is demonstrated. |
| Evidence and audit | Signed execution records, source fingerprints, retained artifacts and Git audits | Upstream documents control events and telemetry sinks. Compatibility with signed project evidence is unverified; event logging alone is insufficient acceptance evidence. |
| Data exposure | Sanitized observations and external credentials | Instrumented inputs/outputs may reach evaluators or telemetry sinks. A pilot must establish exact payloads, redaction, persistence, and deletion before private data is used. |
| Authentication | External operator credentials and scoped CI credentials | Upstream quickstart documents agent/admin API keys and warns that its default server starts without keys. Deployment needs explicit authentication configuration. |
| Failure behavior | Missing evidence cannot PASS | Timeout, unreachable server, stale policy, and evaluator-error behavior have not been tested here. Fail-closed behavior must be demonstrated before enforcement reliance. |
| Operations | Repository-local harness and deterministic hosted jobs | Upstream quickstart adds a server, PostgreSQL, SDK instrumentation, credentials, and service maintenance. Benefits must justify this operating cost. |

Upstream capability descriptions are documented claims. None of the compatibility, privacy, failure-mode, or operational checks above has passed a local pilot.

## Conditions for a future pilot

A separate scope would use a pinned version, synthetic inputs, local authenticated services, disposable storage, and an instrumented mock development tool. It would not introduce a sixth product repository or alter application/test runtimes.

Acceptance would require permitted calls executing once, denied calls producing no side effect, and unavailable/erroring evaluation blocking protected actions. Tests would cover policy changes and version recording, concurrent calls, authentication failure, secret redaction, telemetry retention, and bypass through uninstrumented calls. A real supported coding-agent interception point must be demonstrated separately; a mock wrapper cannot prove native coverage.

Record verdicts, policy/version identifiers, timing, and sanitized evidence. Preserve existing preflight and final audits. Compare enforcement coverage and maintenance cost with the current harness, then make a new adoption decision. Any model-based evaluators require explicit separate consideration; the pilot defaults to deterministic evaluators.

## Interfaces and compatibility

This assessment adds no API, dependency, service, credential, or runtime configuration. Integration remains unbuilt. Claude's artifacts-only exception remains in effect. The four Ds guide human collaboration; neither this tool nor the existing harness certifies responsible use automatically.

Reviewed upstream main commit: [`a77589bfcbecf31e59aa0a8ab970c4ea9c442fad`](https://github.com/agentcontrol/agent-control/tree/a77589bfcbecf31e59aa0a8ab970c4ea9c442fad).
