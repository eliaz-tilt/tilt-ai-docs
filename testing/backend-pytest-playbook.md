# Backend pytest playbook (for agents)

Quick reference for running Django/pytest tests locally. Normative testing
standards live in `@.ai/rules/testing/testing-standards.mdc`.

---

## Fast path (preferred)

From repo root, with Docker running and a `.env` file (copy from `.env-dist` if
missing):

```bash
just test benefits/rules/new_jersey/tests/test_pfl.py::TestNjFliClaimModeGuide -q
```

- Wraps `docker compose run --rm django pytest …`
- Strips a leading `backend/` from paths automatically
- Uses `config.test_settings` (see `backend/pyproject.toml`)
- Default pytest addopts: `--reuse-db --nomigrations` (fast reruns)

**First run / migration drift:**

```bash
just test --create-db benefits/rules/<module>/tests/test_foo.py -q
```

**Skip slow tests:**

```bash
just test-fast benefits/rules/new_jersey/tests/ -q
```

---

## Prerequisites

| Requirement            | Check                                                                              |
| ---------------------- | ---------------------------------------------------------------------------------- |
| Docker Desktop running | `docker info`                                                                      |
| `.env` at repo root    | `test -f .env` — needs at least `DJANGO_SECRET_KEY` (`.env-dist` has `top-secret`) |
| Backing services       | `just services-up` starts `db`, `redis`, `dynamodb-local`, etc.                    |
| Django image built     | First `just test` builds `tilt-repo-django:latest` (~1–2 min)                      |

Postgres must be reachable. Default host `.env` uses
`postgres://ourtilt:ourtilt@localhost:5432/ourtilt`.

---

## Common failures and fixes

### `Bind for 0.0.0.0:6379 failed: port is already allocated`

Another process (often a non-Tilt Redis container) owns port 6379. `just test`
tries to start `ourtilt-redis` and fails.

**Options:**

1. Stop the conflicting container: `docker ps` → stop the process on `:6379`
2. Use the **fallback runner** below (connects to existing `ourtilt-db` on the
   compose network; Redis not required for most unit tests — test settings use
   `DummyCache`)

### `Environment variable "DJANGO_SECRET_KEY" not set` (host `uv run pytest`)

Host-mode pytest loads `backend/config/test_settings.py` → `settings.py` →
requires env vars.

```bash
cd backend
set -a && source ../.env && set +a
uv run pytest benefits/rules/... -q
```

### `cannot load library 'libgobject-2.0-0'` (host macOS)

WeasyPrint native libs are in the Docker image, not a typical Mac host venv.
**Use Docker** (`just test`) instead of host pytest for full Django tests.

### `role "ourtilt" does not exist` / SSL errors in Docker

When hand-running `docker run`, set:

```bash
-e DATABASE_URL=postgres://ourtilt:ourtilt@db:5432/ourtilt
-e POSTGRES_SSL_MODE=
```

and attach to the compose network (see fallback below).

### `get_max_duration` returns `0` but test expects a positive cap

Often **leave metadata vs schedule mismatch**: `expected_leave_date` /
`expected_return_date` must cover the `ScheduleDay.from_field` / `to_field`
range. Update leave dates before asserting duration (see
`TestNjFliClaimModeGuide` in `test_pfl.py`).

---

## Fallback: pytest when `just test` cannot start Redis

Use when `ourtilt-db` is already up on network `local-dev-network` but port 6379
is blocked:

```bash
cd /path/to/tilt-repo

docker run --rm \
  --network local-dev-network \
  -v "$(pwd)/backend:/code" \
  -w /code \
  -e DJANGO_SECRET_KEY=top-secret \
  -e ENV_NAME=local \
  -e DATABASE_URL=postgres://ourtilt:ourtilt@db:5432/ourtilt \
  -e POSTGRES_SSL_MODE= \
  -e REDIS_URL=redis://host.docker.internal:6379 \
  -e SITE_DOMAIN=ourtilt.org:3000 \
  tilt-repo-django:latest \
  pytest benefits/rules/new_jersey/tests/test_fli_benefit_days.py -q
```

Replace the trailing path with your target. Image name:
`tilt-repo-django:latest` (from `docker compose build django`).

---

## Useful pytest patterns

```bash
# Single test
just test benefits/rules/new_jersey/tests/test_pfl.py::TestNjFliClaimModeGuide::test_single_uninterrupted_leave_is_continuous -vv

# Whole file
just test benefits/rules/new_jersey/tests/test_pfl.py -q

# Keyword
just test -k "intermittent and nj" -q

# Unit only (exclude integration marker)
just test-unit benefits/rules/new_jersey/ -q
```

Paths are relative to `backend/` (pytest root).

---

## NJ FLI intermittent logic (example suite)

After changing `fli_benefit_days.py` or `new_jersey/pfl.py`:

```bash
just test \
  benefits/rules/new_jersey/tests/test_fli_benefit_days.py \
  benefits/rules/new_jersey/tests/test_pfl.py::TestNjFliClaimModeGuide \
  benefits/rules/new_jersey/tests/test_pfl.py::TestNjFliIntermittentTransition \
  benefits/rules/new_jersey/tests/test_pfl.py::TestNjFliIntermittentBondingSegments \
  -q
```

**Expected:** 20 passed (pure decrement tests + claim-mode / transition /
bonding segment tests).

Product guide:
[NJ FLI intermittent leave (NJ DOL)](https://www.nj.gov/labor/myleavebenefits/worker/resources/intermittent-leave.shtml)
— mirrored in `TestCountNjFliBenefitDays` docstrings.

---

## Host-mode dev (optional, not for full pytest)

Documented in root `README.md` — `just services-up` +
`cd backend && uv run pytest`. Requires complete `.env`, WeasyPrint system libs
on Linux, and local Postgres. Agents should default to **`just test`** unless
the user explicitly uses host-mode.

---

## CI parity

CI runs the full backend suite in Docker with migrations and coverage. A green
targeted `just test` run is necessary but not sufficient for merge — watch the
GitHub `python` check for the full run.
