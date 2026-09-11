# Creating pull requests (tilt-repo)

Local reference for opening and updating PRs. Source of truth for the **body
structure** is always
[`.github/pull_request_template.md`](../.github/pull_request_template.md) — copy
every section; do not replace it with a one-line Summary.

---

## Before you open the PR

1. **Branch** — feature/fix name that matches the work (`fix/dc-pfl-…`,
   `PIE-123-…`).
2. **Title** — describe what the PR _does_, not the first symptom you fixed.
   - Bad: `Fix DC PFL benefit titles to match leave type` (understates refactor)
   - Good:
     `DC PFL: child rules per leave type, tracking registration, and template provisioning`
3. **Commits** — push all commits; `gh pr create` only includes what is on the
   remote branch.
4. **Stage fully before commit** — if staged and unstaged edits overlap the same
   files, pre-commit may stash, ruff may reformat, and the hook restore can
   **roll back** fixes. Fix:

   ```bash
   git add -A   # or add the specific paths
   git commit -m "..."
   ```

---

## PR body (required sections)

Use the GitHub template verbatim. At minimum fill in:

| Section            | What to write                                                  |
| ------------------ | -------------------------------------------------------------- |
| **Issue Link**     | Full Jira URL: `https://ourtilt.atlassian.net/browse/PIE-XXX`  |
| **Checklist**      | Check boxes honestly (flags, tests, docstrings, breaking API)  |
| **Description**    | What changed — architecture, files, behavior                   |
| **Motivation**     | Bug / gap / why this approach (not a duplicate of Description) |
| **Observability**  | New monitors or explicit “none; why”                           |
| **Rollback plan**  | Revert + any follow-up (re-run rules, `--live-run` commands)   |
| **Testing**        | Commands that ran + manual dev/stage steps                     |
| **Performance**    | Usually “negligible” with one sentence why                     |
| **Visual changes** | Screenshots or “N/A — backend only”                            |

### Title vs description

If the PR grew beyond the original ticket (refactor, provisioning, tests),
**update both title and body** before review — reviewers read the title in Slack
notifications.

### Feature flags

When BKE or product behavior is flag-gated, name the flag(s) and ON/OFF behavior
in Description or Testing (e.g. `enableBKEDCPFL`, `enableDCPflTracking`).

### Post-merge / per-environment steps

Call out ops that are **not** automatic on deploy:

- `python manage.py construct_child_benefits --live-run`
- `python manage.py run_rules --leaves … --ignore-checks`
- Flag rollout order

---

## Creating the PR with `gh`

Repo: `ourtilt/tilt-repo`.

### Fix `gh` auth (common Cursor / CI issue)

If you see `read:packages` only or “Could not resolve Repository”:

```bash
unset GITHUB_TOKEN          # env var overrides keyring and often has narrow scope
gh auth switch -u eliaz-tilt # use account with repo scope (adjust username if needed)
gh auth status              # active account should list token scopes including repo
```

If refresh fails because of `GITHUB_TOKEN`:

```bash
unset GITHUB_TOKEN
gh auth refresh -h github.com -s repo,read:org
```

### Create

```bash
git push -u origin HEAD

unset GITHUB_TOKEN
gh pr create --repo ourtilt/tilt-repo \
  --title "Your accurate title" \
  --body-file .github/pull_request_template.md
```

Then edit the body on GitHub (or replace placeholders in a temp file) — the
template has empty sections and `TICKET_NUMBER` placeholders.

### Update title + body on an existing PR

```bash
unset GITHUB_TOKEN

# Option A: edit on GitHub UI (fastest)

# Option B: body from a file
gh pr edit 11455 --repo ourtilt/tilt-repo \
  --title "DC PFL: child rules per leave type, tracking registration, and template provisioning" \
  --body-file /path/to/pr-body.md
```

Write the body file following the template sections, not a short GitHub default
“Summary / Test plan” unless the team explicitly wants that for a tiny PR.

### View / checks

```bash
unset GITHUB_TOKEN
gh pr view 11455 --repo ourtilt/tilt-repo
gh pr checks 11455 --repo ourtilt/tilt-repo
```

---

## Agent / automation notes

When an agent creates a PR for you, it should:

1. Read
   [`.github/pull_request_template.md`](../.github/pull_request_template.md).
2. Run `git log main..HEAD` and `git diff main...HEAD` for accurate scope.
3. Set title from **full** scope, not the first commit message.
4. Use `unset GITHUB_TOKEN` before every `gh` call in environments where
   `GITHUB_TOKEN` is injected (Cursor, some CI shells).
5. Return the PR URL when done.

User rule in Cursor: prefer `gh` for all GitHub tasks; push with
`-u origin HEAD`.

---

## Quick checklist

- [ ] Title matches final scope (not just the original bug)
- [ ] Body uses repo template sections
- [ ] Jira link filled in
- [ ] Flags, tests, rollback, manual QA steps documented
- [ ] `unset GITHUB_TOKEN` if `gh` fails
- [ ] All related files staged before commit (avoid pre-commit stash conflicts)
