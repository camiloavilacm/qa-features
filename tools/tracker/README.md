# GitHub Issues campaign reporter — Step 5

Consumes an existing approved-schema campaign and verifies its local artifacts. This tool does not aggregate runs or change issue status. Dependencies are the existing pinned tools/validate/requirements.txt in the isolated environment. GitHub CLI must be installed and authenticated for publication; dry-run uses no GitHub transport.

From qa-features:

```sh
.venv/bin/python tools/tracker/tracker.py \
  --campaign tools/tracker/fixtures/missing.json \
  --artifacts /tmp --repository camiloavilacm/ai-qa-agent --issue 1 --fixture
```

The issue number above is a preview placeholder, not an existing issue selection. Default behavior validates and prints Markdown offline. Add --apply only with authorization to create/update the concrete comment. It never creates an issue; issue creation is a separately reviewed operator action. --fixture visibly labels specification fixtures as not executed. No local path, raw failure body, token or private artifact content is published.

Schema validation loads Git blobs from the immutable seed-1-approved-v1 commit; --feature-ref may explicitly select another immutable approved commit. The tracker enforces slot/result/campaign agreement, status precedence, actual timestamp ordering, required observation events, consistent per-SUT/per-runner/tooling revisions, unique execution IDs, and artifact existence/hashes. Artifact layout is <artifacts-root>/<slot-with-colon-replaced-by-dash>/<artifact.path>. Artifact paths must remain inside the explicit root and cannot use symlinks. HTTP bodies are never persisted by the tracker. A campaign whose observation is unavailable cannot pass.

A stable marker identifies one comment per repository/issue/SEED-1/campaign. An identical body is a no-op; changed content updates that comment. Duplicate markers or a different publisher fail for review. The full comment search is paginated; an incomplete search fails. An uncertain POST/PATCH is reconciled by reading comments, without blindly retrying a mutation. Local flock serializes CLI publishers; callers on different machines must use a single serialized publishing job. This CLI does not claim distributed atomic uniqueness. Prior campaign attempts remain the responsibility of the Step 6 campaign workflow.

The gh client uses its existing authentication without exposing credentials. POST and PATCH target comment endpoints only; issue fields are read before and after publication. Never pass a user-controlled token on the command line. API reference: https://docs.github.com/en/rest/issues/comments .

Run local tests with `.venv/bin/python -m unittest discover -s tools/tracker -p 'test_*.py' -v`. The fake transport tests are development regressions, not live publishing evidence.

Registered checks use harness/scripts/verify_step.py run --check dry-run|sandbox-comment|idempotency|no-transition. Supply QA_AUTHORIZATION_FILE and QA_EVIDENCE_KEY_FILE for the development recorder. The three live checks return NOT RUN until QA_TRACKER_SANDBOX_APPROVAL_FILE names an external mode-0600 receipt binding the repository, actual sandbox issue, explicit human instruction, and exact SHA-256 of both reviewed fixture files. The live sequence creates/verifies one comment, repeats without writes, updates to the second fixture, repeats, restores the original body, then compares original issue fields. No workflow, issue transition, auto-healing or model call is implemented. Step 6 remains outside this step.
