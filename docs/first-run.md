# First run: one application and Playwright

This path was exercised from fresh application and runner clones on macOS/Apple Silicon with Docker running Linux/arm64, Python 3.13 and the pinned Playwright package. The full immutable release profile is separately qualified on Ubuntu 24.04 Linux/amd64. Other local platforms may need browser system libraries; no cross-platform equivalence is claimed.

Prerequisites: Git, Python 3.13, Docker with Compose, network access for pinned dependencies/images/browser downloads, and free localhost port 18081. Clone into a new directory:

```sh
git clone https://github.com/camiloavilacm/sut-python.git
git clone https://github.com/camiloavilacm/qa-python.git
```

Start a dedicated synthetic database and application. `configure.py` creates a private local `.env` and refuses to overwrite an existing one. The port override keeps this example separate from the normal port 8001:

```sh
cd sut-python
python3 tools/configure.py
export PORT=18081
export QA_REVIEW_PROJECT=qa-showcase-review
docker compose -p "$QA_REVIEW_PROJECT" up --build -d --wait
export QA_REVIEW_SUT_REVISION="$(git rev-parse HEAD)"
cd ../qa-python
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python tools/bootstrap_features.py
.venv/bin/python -m playwright install chromium
.venv/bin/python -m pytest --driver playwright --sut sut-python \
  --base-url http://localhost:18081 --sut-revision "$QA_REVIEW_SUT_REVISION" \
  --campaign-id reviewer-first-run --result-dir reports/first-run
```

On Linux, Playwright may require installing browser system dependencies through its documented `install --with-deps chromium` command. The pinned package must support your Python/platform combination.

Expected result: three passed scenarios. Inspect `reports/first-run/results.json` and the per-scenario `network.json` and `checks.json` files. They preserve story/acceptance tags and sanitized evidence, not raw credentials or browser traces. An existing result directory is rejected; choose a fresh path for each subsequent run.

Clean up only this example's disposable Compose project and synthetic database:

```sh
cd ../sut-python
docker compose -p "$QA_REVIEW_PROJECT" down -v
```

Use a different Compose project name if `qa-showcase-review` already exists. No development harness activation, external approval ledger, evidence-signing key, GitHub token, or AI account is required for this local run. Existing baseline data must not be edited to make tests pass.
