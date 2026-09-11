# Reviewing like Dustin (`dmwyatt`)

Distilled from his reviews on
[DC FMLA #11119](https://github.com/ourtilt/tilt-repo/pull/11119) and
[DC PFL #11120](https://github.com/ourtilt/tilt-repo/pull/11120). Use this to
**self-review BKE / benefits PRs before asking him**, or to leave the same kind
of feedback.

Tone overall: precise, collaborative, evidence-backed. He leads with what landed
well, then asks targeted questions. Non-blocking notes stay labeled as such. He
prefers fixing framing/docs when the code is already fine.

---

## How a Dustin review is structured

1. **Summary verdict first** — what looks right, what was verified (scope trim,
   tests, complexity).
2. **Blocking / framing issues** — wrong product language, Missing-vs-deny,
   stale module names.
3. **Smaller notes** — merge conflicts, missing test cases, enablement
   follow-through.
4. **Nits** — docstrings, import placement, unnecessary `__all__` exports (“take
   or leave”).

He runs the tests and mentions the result (`87/87 with --create-db`, “tests pass
for me and complexity is fine”).

---

## Lens 1 — Collected vs uncollected (bright line)

This is the main review lens for BKE activation PRs.

| Ask                                                   | Fail signal                                                                           |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Does every new check read a **real collected** field? | Stub seam that always returns a hard-coded default                                    |
| Is anything still labeled “seam” when it’s wired?     | `*_data_seams.py` docstring about “may not collect yet” after PR says “no stubs left” |
| Are out-of-scope leave types left alone?              | Military / DV / organ donor / bereavement wired prematurely                           |
| Are proposal placeholders gone?                       | Unwired accessors hanging around “for later”                                          |

**Prefer:** delete the seams module once accessors are real; fold into
`checks.*` or the rule file. Naming that still says “seam” invites the confusion
the PR is trying to avoid.

---

## Lens 2 — Missing vs determined deny

Nullable / unanswered config must not look like a firm “no.”

**Pattern he almost always checks:**

```text
None / absent config / no profile  →  eligible=None (“Missing …”)
explicit False                     →  eligible=False
explicit True                      →  eligible=True
```

**Classic trap:** `value is True` (or `bool(x)`) collapses absents into `False`,
so non-onboarded / legacy companies silently deny. Call that out with the
concrete product consequence (“every non-onboarded DC company”).

**Implementation trap he calls out:**

> Gate on `is None` explicitly. (`require(False)` / `_is_empty` behavior can
> surprise people — verify against this codebase before advising.)

**Test expectation:** unanswered cases flip from `expect_benefit_ineligible` →
`expect_benefit_missing`. Explicit-false stays ineligible.

Engage the author’s own reviewer-guide / L&C question when they already
suspected this (“Does that match what you were getting at?”).

---

## Lens 3 — Words must match code (framing)

If PR/commit language oversells behavior, ask to fix the **description**, even
when the code is acceptable.

Examples from these PRs:

| Oversell                         | Accurate                                                                                                   |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| “routes to manual review”        | sets `PaycalcItem.needs_manual_approval` (legacy status-hold flag; engine off in prod → **no hold today**) |
| “published” StateConfiguration   | `.active()` = not soft-deleted; no publish/draft                                                           |
| “data seams” module after wiring | accessors / fallbacks over collected data                                                                  |

When code matches a sibling pattern he’s fine keeping it — but follow-through
must capture what would be needed for the _real_ product behavior (e.g. hold via
`ApprovalMethodRule` / `ApprovalMethodOverride`, not the rule-level flag).

---

## Lens 4 — Semantics & enablement follow-through

Call out behavior changes even when he agrees they’re correct:

- DC FMLA ignoring federal `fmla_eligibility_rule` in favor of a 24-month
  program default — “more correct… but calling it out since it’s a semantics
  change.”
- Persistence reading **template** tracking, not the rule → “prod templates need
  `ROLLING_FORWARD_24`; worth a line in the follow-through ticket.”

Ask: _after this merges, what still has to be true in prod data/flags for
enablement?_

---

## Lens 5 — Robustness & honesty in small details

| Kind                  | Example                                                                                                                                                                  |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Divergent read paths  | `reqs` via `Requirement.get(leave, "company.policy…")` vs result via `get_policy()` — Missing detection and value read can disagree                                      |
| Assumed uniqueness    | `.order_by("-updated_at").first()` when related_name allows multiple rows; newer row without a key can shadow an older one — comment the convention or filter explicitly |
| Silent `except: pass` | Usually flagged; add a one-line “why benign” comment when the catch is correct                                                                                           |
| Stale docs            | Module docstring describing a previous design — rewrite or rename                                                                                                        |

He often frames soft doubts as questions: “Worth aligning them, or am I
overthinking it?”

---

## Lens 6 — Tests tell the acceptance story

- Cover the **bank / threshold story ends**, not only the happy middle (PFL: no
  prior → full bank; partial; fully exhausted → 0).
- Unsupported caregiver / relationship: **deny**, don’t expand the survey enum
  “just to green the path.”
- New tests: one-line declarative docstrings (testing-standards).
- Prefer plain pytest functions; classes are “take or leave” when touching
  legacy test files.
- Don’t hide imports inside test functions.

---

## Lens 7 — Hygiene he notices

- Parallel PRs creating the same new file (`helpers.py`) → call the merge order
  (`merge A first, rebase B`).
- Complexity on touched code: fine / not fine — he says so.
- Unnecessary package re-exports (`__all__` shipping a private helper nothing
  imports).
- Null-guarded / jurisdiction-scoped onboarding writes (“DC-only so it shouldn’t
  touch other companies”).

---

---

## Self-review checklist (before tagging him)

Copy/paste for BKE / benefits eligibility PRs:

- [ ] No stubs for uncollected statute slices; out-of-scope leave types
      untouched
- [ ] No `*_data_seams` name/doc after everything is collected
- [ ] Unanswered nullable fields → Missing, not silent deny; explicit false
      stays ineligible
- [ ] Gate Missing with `is None` (don’t fold False into Missing by accident)
- [ ] PR/commit wording matches what the code actually does in prod today
- [ ] Enablement follow-through listed (templates, approval-method data, flags)
- [ ] Semantics changes from prior revision called out in the PR body
- [ ] Tracking / shared-bank tests cover empty / partial / full (or equivalent
      ends)
- [ ] New tests have one-line docstrings; no mid-function imports
- [ ] Sibling PRs won’t add/add-conflict the same new path (or merge order
      noted)
- [ ] Bare `except X: pass` has a one-line justification
- [ ] Check `reqs` path and `result` path read the same field the same way
- [ ] Ran the relevant `just test …` suite and noted the count

---

## Phrase bank (sound like him)

**Lead with approval**

> The trimming looks right to me: … Tests pass clean for me … and complexity on
> everything the PR touches is fine.

**Missing vs deny**

> As written, absent config… all resolve to False, which is a determined
> eligible=False indistinguishable from an employer who actually answered "no".
> … Should the None case require() the field so it surfaces as "Missing …",
> reserving False for an explicit "no"?

**Framing fix**

> One framing thing I'd like to fix in the PR description and commits: "…"
> oversells what the code does. … The code itself matches the sibling … pattern
> and I'm fine with it, but the description should say "…".

**Soft robustness**

> Small robustness question: … Worth aligning them, or am I overthinking it?

**Nits**

> Nit: … / Nits: … / Test-style nits, take or leave: …

**Follow-through**

> Worth a line in the follow-through ticket. / worth capturing in the
> follow-through.

**Engage the author**

> Does that match your read, or is deny-on-null deliberate?\
> Does that match what you were getting at with the L&C question?

---

## What he usually does _not_ do

- Rewrite the author’s approach when a sibling pattern already exists and is
  intentional — he accepts it and tightens language instead.
- Block on every style nit — many are explicitly optional.
- Ignore product/enablement consequences of a “correct” code change.
- Treat PR description / commit message accuracy as optional.

---

## Source reviews

- [#11477 Tracking None reaccrual sentinel](https://github.com/ourtilt/tilt-repo/pull/11477)
  — guard placement, measured-forward fallback, SpanLimiter vs UNKNOWN_SPAN,
  test coverage →
  [tracking-none-reaccrual-sentinel.md](tracking-none-reaccrual-sentinel.md)
- [#11119 DC FMLA](https://github.com/ourtilt/tilt-repo/pull/11119) — Missing
  threshold, seams rename, `Benefit.DoesNotExist` comment, `reqs`/result
  alignment, tracking semantics, helpers merge order, test style.
- [#11120 DC PFL](https://github.com/ourtilt/tilt-repo/pull/11120) — Missing tax
  contribution, “published” misnomer, multi-row shadowing, manual-approval
  framing, shared-bank test ends, `__all__` nit.

Update this file when his later reviews add a recurring theme.
