# password-strength-api

A small FastAPI service that scores password strength, built around a security focused CI/CD pipeline in GitHub Actions.

---

## What it does

`GET /health` returns a liveness response used by the container.

`POST /analyze` takes a password and returns an entropy estimate with a plain language strength rating. It sizes the character pool the password draws from, multiplies by length using log base 2, and maps the bit count to a rating from very weak through very strong.

The submitted password is never logged, never stored, and never returned. A unit test asserts the input string does not appear anywhere in the response body, so that property is enforced by the test suite rather than by convention.

---

## Running it locally

```bash
python -m venv .venv
source .venv/bin/activate        # Windows Git Bash: source .venv/Scripts/activate
pip install -r requirements.txt -r requirements-dev.txt

ruff check .
pytest -v

uvicorn app.main:app --reload
```

Interactive docs are at `http://127.0.0.1:8000/docs`.

To run the published container instead.

```bash
docker run -p 8000:8000 ghcr.io/jonathandeleon1/password-strength-api:latest
```

---

## How the pipeline works

Two workflows, split because they answer different questions and run at different times.

### ci.yml

Runs on every pull request and every push to main. Four jobs run in parallel so a failure in one does not hide failures in the others.

| Job | Tool | What it checks |
|---|---|---|
| Lint and test | ruff, pytest | Style, import order, unit tests |
| Static analysis | Bandit | Insecure patterns in application code |
| Dependency audit | pip-audit | Known CVEs in declared dependencies |
| Secret scan | Gitleaks | Credentials anywhere in git history |

The secret scan job checks out with `fetch-depth: 0` while the others use a shallow clone. Gitleaks needs full history, because a secret that was committed and later deleted is still in history and still compromised.

### release.yml

Runs on push to main. Builds the image, scans it, and only then publishes to the GitHub Container Registry.

The order matters. The image is built and loaded locally, scanned while it exists only on the runner, and pushed afterward. If the gate fails, the job stops and the image never becomes pullable.

---

## Security decisions

### Scanning is tiered rather than all or nothing

Trivy runs twice. The first pass blocks on CRITICAL and fails the job. The second reports HIGH without blocking.

This was not the original design. The first working version blocked on both, and it failed immediately on eleven HIGH findings. Every one came from the `python:3.13-slim` base image rather than from anything in this repository. Nine were a single integer overflow in the util-linux package family and two were in tooling that ships with the base image.

A gate that fails on findings nobody in the repository can fix is a gate that gets disabled within a month, and then there is no coverage at all. Blocking on CRITICAL keeps a hard stop on what genuinely cannot ship, while HIGH findings stay visible in the job output for triage.

The repository configuration follows the same pattern. GitHub code scanning fails check runs at high or higher and reports below that.

### Remediating what the repository controls

Before relaxing the gate, the image was hardened.

`apt-get upgrade` runs at build time. Base images are rebuilt on a schedule, so even a freshly pulled tag can lag behind Debian security updates, and patching during the build closes that window.

pip and setuptools are removed from the runtime stage. This application never installs packages at run time, and shipping a package manager hands an attacker who lands in the container an easy way to pull down tooling. It also cleared the two Python findings, but the reason to do it stands on its own.

### Least privilege on the workflow token

Both workflows declare `permissions: contents: read` at the top. GitHub's default token is considerably more powerful than either workflow needs. Only the publishing job elevates to `packages: write`, and only for that one job.

### No stored credentials

Publishing uses `secrets.GITHUB_TOKEN`, which GitHub mints per run and expires when the job ends. There is no personal access token in repository secrets, nothing to rotate, nothing to leak.

### Container hardening

The image is multi stage. Dependencies install into an isolated virtualenv in the build stage and copy into a clean runtime stage, so pip caches and build tooling never reach the final image.

The service runs as an unprivileged user with UID 10001. Containers run as root by default, which means a container escape starts with root on the host.

`.dockerignore` excludes `.git`, because copying the git directory into an image ships the entire commit history inside the container.

### Repository configuration

Secret scanning is enabled with push protection, which blocks a credential at `git push` rather than alerting after it is already in history. This is the layer that matters most. Gitleaks in CI catches a secret after it has been committed, while push protection stops it from being committed at all.

Dependabot alerts and security updates are on, with the dependency graph they depend on. CodeQL default setup runs as a third scanning workflow, using a different engine than Bandit and catching a different class of finding.

A branch ruleset protects main. It requires a pull request, requires all four CI jobs to pass, blocks force pushes, and restricts deletions.

---

## Known limitations

Simplified for this exercise. Covered in more detail in my email.

- Third party actions are pinned to version tags rather than commit SHAs, and `aquasecurity/trivy-action` is on `@master` after a tag resolution failure. This is the first thing I would fix.
- No SBOM generation and no image signing.
- Deploy is a registry push, not a running service. No environment, rollback, or post deploy health check.
- No rate limiting, structured logging, or observability on the API.

---

## Repository layout

```
.
├── .github/workflows/
│   ├── ci.yml            Lint, test, SAST, dependency audit, secret scan
│   └── release.yml       Build, scan, publish to GHCR
├── app/
│   ├── main.py           FastAPI routes
│   └── strength.py       Entropy scoring, pure functions only
├── tests/
│   └── test_strength.py  Unit tests including the no echo assertion
├── Dockerfile            Multi stage, patched, non root
├── .dockerignore
├── pyproject.toml        pytest and ruff configuration
├── requirements.txt      Runtime dependencies
└── requirements-dev.txt  Test and scanning tools
```