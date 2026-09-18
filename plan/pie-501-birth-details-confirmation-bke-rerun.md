# PIE-501: Birth-details confirmation BKE re-run — Work Plan

**Status:** Not done on `main` (verified 2026-09-18; revised after review rounds 1–4).
Investigation + regression tests exist only on a remote branch (~1981 commits
behind `main`); the apply-path guard is unimplemented.
**Ticket:** [PIE-501](https://ourtilt.atlassian.net/browse/PIE-501)
**Related:** [PIE-498](https://ourtilt.atlassian.net/browse/PIE-498) (AC4 owns the
shared apply-path guard; PIE-501 needs that guard to pass its third AC)
**Assignee:** Eliaz Bobadilla · Sprint: PIE Sprint 16
**Branch with tests (not on main):** `origin/dmwyatt/PIE-501/birth-details-rerun`
  - `daad333cbf` — mid-leave re-anchor + incidental-dispatch pin
  - `58cf5796fc` — documents that a crashing concurrent rule deletes applied time

**Adjacent (do not confuse):** commit `d5b96138a7` on
`origin/fix/unknown-span-deletes-paycalc-items` (remote branch may be deleted —
cite the commit SHA, not the branch name as a hard dependency). That change
preserves **record-keeping** items (`paycalc__isnull=True`) on unknown spans; it
**explicitly still clears applied** paycalc items. That is not PIE-501's guard.

---

## Executive summary

Confirming birth details mid-leave already re-runs BKE, but only because
`perform_update` → `profile_update` → `HistoricalProfile` →
`leave_profile_change` → `RuleService.run_rules`. The birth-details block itself
only notifies the LSM. That incidental re-run can wipe already-applied ABC
benefit time when any rule in the same pass raises (`spans` stays `None` →
`contains_unknown_span` → `_apply_benefit` deletes items).

Remaining work: (1) bring and **re-baseline** the remote regression tests for
current `main` (PIE-510 changed MPLA floor semantics), (2) land the apply-path
exception guard (PIE-501 AC3 + PIE-498 AC4), (3) satisfy AC2 via the **mandatory
minimum** of pinning the incidental dependency + comments (deliberate dispatch
is an optional follow-up, not default scope).

---

## Done vs not done (check first)

| Acceptance criterion | State on `main` | Notes |
|---|---|---|
| Mid-leave confirmation re-runs rules; delivery-date-sensitive spans update | **Behavior true**, test **missing** / **stale** | Incidental `leave_profile_change`. Remote test asserts MPLA start → `actual_delivery_date`; after PIE-510 (`8fc6d38e4f`) MPLA floor for this fixture moves to `expected_leave_date` instead. Must re-baseline. |
| Re-run is deliberate **or** dependency explicit+tested | **Not on main** | Remote has pin test. **Mandatory for this PR:** keep pin test + comments. Deliberate send is optional follow-up only. |
| Re-run does not destroy applied paycalc time | **False / unprotected** | Remote crash test documents deletion. Guard not written. |
| Regression coverage for mid-leave confirmation | **Not on main** | `backend/legacy/views/tests/test_leave_birth_details_confirmation.py` on remote only. |

**Verdict:** ticket is **not done**. Do not re-investigate whether deletion happens.

---

## Problem (causal chain)

```
PUT legacy-apis:leave-detail  (birth_details_confirmed False/None → True,
                               expected_due_date ← actual delivery)
│
├─ LeaveViewSet.perform_update  (leaves.py ~881–944)
│    └─ profile_update(...)     # comment already says this re-runs rules
│         └─ Profile.save()
│              └─ HistoricalProfile created
│                   └─ post_create_historical_record_callback
│                        (profiles/signals/handlers.py ~104–265)
│                        └─ leave_profile_change.send(sender=leave)  ★ incidental BKE
│                             └─ benefits/signals/handlers.py:63–70
│                                  update_leave_fmla + RuleService.run_rules(
│                                      leave, LeaveProfileTrigger(leave))
│
├─ LeaveViewSet.update birth-details block  (leaves.py:1116–1131)
│    └─ notify_lsm_of_birth_details_confirmed + activity log only
│       (NO RuleService / leave_profile_change)
│
└─ past_leave_change  (leaves.py:1204–1210)
     └─ ONLY if is_completed_leave + plan + no published paycalc
        → mid-leave confirmation NEVER hits this
```

Admin (`perform_update` ~452) and HR (`perform_update` ~1578) also call
`profile_update` and can write `birth_details_confirmed` without the EE notify
block — same incidental re-run + wipe risk. The apply-path guard covers all
callers. AC2 comments must cover Admin/HR `profile_update` sites too (or an
explicit non-goal that only EE is in scope — prefer comments on all three).

There is **no** separate survey birth-confirmation API (only
`get_survey_changeset` diffs). Non-goal.

### Why applied time disappears (PIE-498 mechanism)

1. Rule expression raises → eval catch in `benefits/rules/__init__.py` ~701–720
   sets `result.exception`, leaves `spans` as `None`.
2. `BenefitResult.contains_unknown_span` (`__init__.py` ~1521–1528):
   `if self.spans is None: return True` (`@cached_property` — clear cache in
   unit tests after mutating `spans`/`exception`).
3. `_apply_benefit` (`benefits/services/rules.py` ~968–1009):
   `spans = ()` when unknown; existing applied items ⇒ `changed=True`.
4. `check_duplicate_clean_paycalc` (`benefits/utils/creation.py` ~108–109)
   deletes paycalc-linked items for that result; recreate from empty ⇒ gone.

`exception_msg` is persisted in `save_results` via
`exception_msg=repr(result.exception)` **before** `_apply_benefit`, so
integration assertions on `exception_msg` remain valid after the guard.

**Exposure carve-outs:**
- ABC must be eligible (any `automated=False` item disqualifies the paycalc).
- Published paycalc is duplicated first today (loss moves to the new draft).
  **After the guard:** published items stay put on crash (duplication skipped).
  State this explicitly; add a unit case.
- Draft / publish-pending would lose items in place without the guard.
- User-visible trace is a normal `ABC-PAYCALC-UPDATE` LSM task — nothing says a rule crashed.

### PIE-510 impact on the MPLA observable (blocker for Phase 0)

Remote tests assume MPLA suggestion start moves
`estimated_due_date → actual_delivery_date`.

On current `main`, `MinnesotaPLA.get_parental_min_start_date` uses
`get_parental_pre_birth_span_floor(leave, exclude_nesting_pre_birth=True)`
(`mpla.py` ~105–108; util docstring at `utils.py` ~2075–2078): after
confirmation, when `expected_leave_date < expected_due_date`, the floor is
**`expected_leave_date`**, not the confirmed delivery date. Bonding windows
that read `expected_due_date` directly still move estimate→actual; MPLA's min
start for this fixture does not.

For the remote `mid_leave` fixture shape:

| State | MPLA suggestion start on current `main` |
|---|---|
| Before confirmation | `estimated_due_date` |
| After confirmation **with** re-run | `expected_leave_date` (leave start) |
| After confirmation **without** re-run | stays `estimated_due_date` |

That is still a valid “did the rules re-run?” observable — but assertions that
expect `[actual_delivery_date]` **will fail** and must be rewritten.

---

## Goals / non-goals

### Goals (PIE-501)

1. Mid-leave birth confirmation continues to re-run BKE; delivery-date-sensitive
   (or confirmation-sensitive) spans update per **current** rule floors.
2. AC2 **mandatory minimum:** incidental HistoricalProfile dependency remains
   explicitly tested + commented. Deliberate dispatch is optional follow-up only
   (see D2).
3. A failed rule evaluation (`result.exception` with `spans is None`)
   **never** removes already-applied paycalc items on the ABC
   `_apply_benefit` path, and that same early-return also leaves
   record-keeping alone there (shared with PIE-498 AC4 for applied time).
   Non-ABC `save_results` rebuild remains a residual wipe path (D4).
4. Regression tests from `dmwyatt/PIE-501/birth-details-rerun` land on a branch
   from current `main`, re-baselined, and stay green under the new behavior.

### Non-goals

- Fixing the FMLA `_rolling_back_day_draw` null-balance TypeError (PIE-498
  criteria 1–3).
- Panel copy that conflates crashes with deliberate no-coverage (PIE-495).
- Changing Todd's non-exception unknown-span “still clear applied” policy
  (`d5b96138a7`).
- Guarding the non-ABC `save_results` record-keeping rebuild path
  (`rules.py` ~303–310) as part of PIE-501 — note as residual / Todd follow-up;
  PIE-501 AC3 is about **applied** paycalc time via `_apply_benefit`.
- Making `past_leave_change` fire for active leaves.
- Frontend Birth Details UI.
- Separate survey birth-confirmation API (does not exist).
- Defaulting to deliberate `leave_profile_change` send in this PR.

---

## Design decisions

### D1 — Where the apply-path guard lives

**Put it in `RuleService._apply_benefit`.**

**Key (precise):**

```python
if rule_result.exception is not None and rule_result.spans is None:
    # Failed evaluation must not look like "zero spans".
    # Return BEFORE the `if not spans and not items` delete branch.
    # Do NOT also require `items` — paycalc-linked `items` excludes
    # paycalc__isnull=True rows; requiring items would still wipe
    # record-keeping via the empty-spans branch.
    logger.warning(
        "Skipping paycalc apply after evaluation exception; "
        "preserving existing items",
        result_id=result.pk,
        leave_id=result.leave_id,
    )
    return False
```

Why this key:

- Crash-in-`spans` leaves `spans is None` + `exception` set — the PIE-501 /
  PIE-498 failure mode.
- Bare `exception` alone can fire after spans already succeeded (later attrs
  like `waiting_period_config` / overrides) — still apply those spans.
- Do **not** add `contains_unknown_span` to the key: deliberate
  `UNKNOWN_SPAN` + a later-attr exception would over-preserve and fight
  Todd/`d5b96138a7` (still clear applied on undeterminable non-crash).
- Bare `spans is None` without exception (`MissingValue`) is not a “failed
  evaluation” under PIE-498 AC4 — leave existing behavior.

**Unconditional early return** when the key matches — never `and items`.

**Scope boundary:** ABC `_apply_benefit` only. Non-ABC `save_results`
rebuild may still touch record-keeping; out of PIE-501 AC3. Mention in PR.

**Published paycalc:** skipping `check_duplicate_clean_paycalc` means no
draft duplication on crash; published applied items remain. Add a unit case.

### D2 — AC2 path (single source of truth)

**Mandatory for this PR (satisfies AC2 “or”):**

1. Keep `test_confirmation_rerun_depends_on_the_profile_history_dispatch`
   (after re-baseline of span assertions).
2. Comments at EE/Admin/HR `profile_update` call sites and at the EE
   birth-details block noting mid-leave confirmation BKE depends on the
   HistoricalProfile → `leave_profile_change` path.

**Optional follow-up (AC2 first clause) — do NOT do by default:**

Deliberate `leave_profile_change.send(sender=new_leave)` in the birth-details
block. Constraints if ever done:

- Must use `leave_profile_change.send` (imports `leave_profile_change` alongside
  existing `past_leave_change`). **Forbid** direct
  `RuleService.run_rules(..., LeaveProfileTrigger)` — that skips
  `update_leave_fmla` in the receiver.
- Birth-details block is EE-only and only runs on False/None → True. The
  remote healthy/crash tests’ **second** PUT already has
  `birth_details_confirmed=True`, so they never re-enter that block — re-run
  is still via `profile_update`. Deliberate send in the confirm block alone
  does **not** cover post-confirm due-date edits.
- Accept double `run_rules` on first confirmation, or de-dupe carefully.
- Invert the pin test only after deliberate send is real.

### D3 — Relationship to PIE-498

| Work | Ticket |
|---|---|
| Apply-path guard in `_apply_benefit` for `exception and spans is None` | PIE-498 AC4 **and** PIE-501 AC3 — implement once under PIE-501 PR |
| FMLA null `total_minute_balance` root cause + drain behavior | PIE-498 only — out of scope |
| Mid-leave confirmation tests + AC2 pin/comments | PIE-501 |

**Before merge:** PR links both tickets; comment on PIE-498 that AC4 is claimed
by the PIE-501 PR (avoid duplicate guards / dropped ownership).

### D4 — Residual wipe paths (accepted for this ticket)

`exception and spans is None` does **not** cover:

- `spans is None` via `MissingValue` (no exception)
- Invalid spans coerced to `None` in `_validate_spans` without exception
- Deliberate `UNKNOWN_SPAN` with applied items (Todd stance: still clear)
- Non-ABC `save_results` record-keeping rebuild

Document in PR as accepted residual unless product expands scope.

---

## Implementation plan

### Phase 0 — Branch hygiene + re-baseline tests

1. `git fetch origin`
2. Branch from current `main` (e.g. `pie-501-birth-details-bke-guard`).
3. Confirm file absent: `rg test_mid_leave_birth_confirmation` → no hits.
4. Bring tests: try cherry-pick `daad333cbf` then `58cf5796fc`. Prefer
   **copy-file + fix-to-main** if replay is messy — tip is ~1981 commits
   behind (`leave→profile` sync, PIE-510 floors, EE `perform_update`
   null-field stripping).
5. **Re-baseline span observables before any production change:**

   **Re-anchor + pin tests** (single confirm after `ForceRun` on unconfirmed
   leave — MPLA start is a valid re-run signal):

   | State | Assert `mpla_suggestion_starts` |
   |---|---|
   | Before confirm / suppressed re-run | `[estimated_due_date]` |
   | After confirm + re-run | `[mid_leave.expected_leave_date]` (== leave start) |

   **Healthy + crash tests** (seed with a first confirm PUT, then a second
   PUT that only moves `expected_due_date`): after PIE-510 the first confirm
   already moves MPLA start to `expected_leave_date`; the second PUT does
   **not** change that floor. Asserting `[expected_leave_date]` on the second
   PUT is **tautological** — it passes even if the second PUT never re-runs.

   Calling `MinnesotaPLA(...).get_parental_max_start_date(leave)` /
   `one_year_eligible_date(expected_due_date)` in the test is **also not a
   re-run proof** — that is leave-field math and changes even if BKE never
   ran.

   For healthy/crash, prove second-PUT re-run with a **persisted**
   due-date-sensitive signal:
   - Prefer: make `ConcurrentRule.spans` derive from
     `leave.expected_due_date` so applied item from/to move on a healthy
     second PUT (and crash still asserts `exception_msg` + item survival
     from the seed).
   - Or: drop re-run proof on healthy/crash and document that AC1 re-run
     coverage lives only in re-anchor/pin; healthy asserts item survival
     only; crash asserts `exception_msg` + preservation.

6. Run the four tests once **before** guard work:
   - Re-anchor + pin should pass after re-baseline.
   - Healthy applied-time keep should pass.
   - Crash-deletes test should pass **as written** (documents the defect).
7. Fixture triage if 400s / flakes:
   - Prefer minimal writable PUT payload over full `LeaveOutputSerializer`
     round-trip if validation fails.
   - `ConcurrentRule.explode` must reset in `finally` (remote fixture already
     partly does).
   - Dates are `timezone.now()`-relative — keep mid-leave shape (started,
     not ended).

### Phase 1 — Apply-path guard (primary fix)

**File:** `backend/benefits/services/rules.py` — `RuleService._apply_benefit`

1. Early return with the D1 key **before** unknown→`()` coercion and before
   the `if not spans and not items` record-keeping delete.
2. Do not call `check_duplicate_clean_paycalc`.
3. Unit tests in `backend/benefits/services/tests/test_rules.py` near
   `test_apply_benefit_no_spans_but_items` (~1290). **All of these are
   required:**
   - Crash shape: `rule_result.spans = None`,
     `rule_result.exception = SomeError(...)`, then
     `rule_result.__dict__.pop("contains_unknown_span", None)`.
     Do **not** use `_setup_apply_benefit(..., with_spans=False)` alone
     (`spans=()` ≠ crash).
   - `exception` + `spans is None` + existing applied items → preserved,
     `changed is False`.
   - `exception` + `spans is None` + no applied items → record-keeping not
     wiped (proves unconditional early return / no `and items`).
   - Good spans + later-attr `exception` → still applies.
   - Deliberate `UNKNOWN_SPAN` + no exception → still clears applied (Todd
     stance unchanged).
   - No exception + empty/ineligible spans → existing delete/recreate unchanged.
   - Published paycalc + `exception` + `spans is None` + applied items →
     items preserved, no forced duplicate.

### Phase 2 — Flip the integration regression

**File:** `backend/legacy/views/tests/test_leave_birth_details_confirmation.py`

1. Rename/rewrite
   `test_confirmation_rerun_deletes_applied_paycalc_time_when_a_rule_crashes`
   → `test_confirmation_rerun_preserves_applied_paycalc_time_when_a_rule_crashes`.
2. Assert: concurrent result has `exception_msg`; applied items for the
   concurrent template **still exist** with same from/to. Prove second-PUT
   re-run via a **persisted** due-date-sensitive signal (prefer
   `ConcurrentRule.spans` tied to `leave.expected_due_date` on the healthy
   path). Do **not** use MPLA suggestion start or bare
   `get_parental_max_start_date` as second-PUT re-run proof (see Phase 0 §5).
3. Keep healthy control test (same rules).

### Phase 3 — AC2 mandatory minimum

1. Keep pin test (re-baselined).
2. Comments at EE birth-details block + EE/Admin/HR `profile_update` sites.
3. Do **not** implement deliberate send unless product explicitly asks.

### Phase 4 — Verification

```bash
pytest backend/benefits/services/tests/test_rules.py -q -k 'apply_benefit'
pytest backend/legacy/views/tests/test_leave_birth_details_confirmation.py -q
pytest backend/legacy/views/tests/test_leave_viewsets.py -q -k birth
```

Checks:
- `past_leave_change` still completed-leave-only.
- Guard keys on `exception is not None and spans is None` only.
- Policy not placed solely in `check_duplicate_clean_paycalc`.

### Phase 5 — PR / ticket hygiene

- Title/body: PIE-501; note PIE-498 AC4 claimed.
- Comment on PIE-498 linking the PR.
- State AC2 path chosen: pin + comments (minimum).
- Note published-paycalc behavior change on crash (no duplicate).
- **Required:** note accepted residual wipe paths (D4) —
  `MissingValue`/`spans is None` without exception; deliberate
  `UNKNOWN_SPAN`; non-ABC rebuild.
- Do not force-push; do not commit unless the user asks.

---

## Key file map

| Path | Role |
|---|---|
| `backend/legacy/views/leaves.py` | EE/Admin/HR update; birth-details block; `profile_update`; `past_leave_change` |
| `backend/profiles/services.py` | `profile_update` active vs completed |
| `backend/profiles/signals/handlers.py` | HistoricalProfile → `leave_profile_change` (~265) |
| `backend/benefits/signals/handlers.py` | `run_rules_on_leave_change` (~63) |
| `backend/benefits/services/rules.py` | `_apply_benefit` ← **guard here** |
| `backend/benefits/utils/creation.py` | `check_duplicate_clean_paycalc` (do not put policy solely here) |
| `backend/benefits/rules/__init__.py` | exception catch; `contains_unknown_span` |
| `backend/benefits/rules/utils.py` | `get_parental_pre_birth_span_floor` (PIE-510; test re-baseline) |
| `backend/benefits/rules/minnesota/mpla.py` | MPLA min start uses floor util |
| `backend/legacy/views/tests/test_leave_birth_details_confirmation.py` | Bring + re-baseline from remote |
| `backend/benefits/services/tests/test_rules.py` | Unit tests for guard |

---

## Risks

| Risk | Mitigation |
|---|---|
| Remote MPLA assertions fail on `main` (PIE-510) | Phase 0 re-baseline before guard work |
| Guarding all `contains_unknown_span` fights Todd | Key is `exception and spans is None` only |
| Bare `exception` skips valid apply | Require `spans is None` too |
| Healthy/crash MPLA start assert tautological after seed confirm | Use due-date-tracking observable or drop it |
| Double ownership of PIE-498 AC4 | Comment on PIE-498 before merge |
| Integration fixture fragility | Minimal PUT payload; reset `explode`; date notes |
| Non-ABC record-keeping still rebuilds on unknown | Out of PIE-501 AC3; note residual |

---

## Open decisions (resolved for implementers)

| Question | Decision for this PR |
|---|---|
| AC2 path? | **Pin test + comments** (minimum). Deliberate send = follow-up only. |
| Exception + no applied items? | Leave record-keeping alone (early return before delete). |
| Deliberate `UNKNOWN_SPAN` + applied items? | Still clear (unchanged; Todd stance). |
| Expand guard to non-ABC rebuild? | No for PIE-501. |

---

## Handoff prompt (copy for a fresh AI session)

```
Fix PIE-501: mid-leave birth-details confirmation re-runs BKE only as a
side effect of the profile history write, and that re-run can delete
already-applied ABC benefit time. Implement the apply-path guard and land
re-baselined regression tests.

Read and follow:
- @.ai/README.md and relevant @.ai/rules/ (backend + testing)
- Full plan (source of truth): @ai-docs/plan/pie-501-birth-details-confirmation-bke-rerun.md
- Ticket: https://ourtilt.atlassian.net/browse/PIE-501
- Related: https://ourtilt.atlassian.net/browse/PIE-498 (claim AC4 in PR + Jira comment)

## Do not re-investigate

1. Mid-leave confirmation DOES re-run BKE today via:
   LeaveViewSet.perform_update → profile_update → Profile.save →
   HistoricalProfile → post_create_historical_record_callback →
   leave_profile_change → run_rules_on_leave_change.
2. Birth-details block (leaves.py ~1116–1131) only notifies LSM + activity.
3. past_leave_change is completed-leave-only (~1204–1210).
4. Crash → spans None → contains_unknown_span → _apply_benefit deletes applied
   items via check_duplicate_clean_paycalc. Confirmed; needs guard.
5. Tests live on origin/dmwyatt/PIE-501/birth-details-rerun
   (daad333cbf, 58cf5796fc) — NOT on main; ~1981 commits behind.

## Mandatory implementation order

### A. Branch + bring tests + RE-BASELINE (before any prod change)
git fetch origin
Branch from main: pie-501-birth-details-bke-guard
Bring backend/legacy/views/tests/test_leave_birth_details_confirmation.py
(cherry-pick or copy-file+fix).

CRITICAL — PIE-510 (8fc6d38e4f) changed MPLA min start to
get_parental_pre_birth_span_floor(..., exclude_nesting_pre_birth=True).

Re-anchor + pin (single confirm after ForceRun):
  before / no re-run → mpla_suggestion_starts == [estimated_due_date]
  after + re-run → == [mid_leave.expected_leave_date]  # NOT actual_delivery

Healthy + crash (seed confirm, then second PUT changing only due date):
  MPLA start is ALREADY expected_leave_date after the seed confirm, so
  asserting it on the second PUT is tautological.
  get_parental_max_start_date / one_year_eligible_date are leave-field
  math — NOT a re-run proof (they change even if BKE never ran).
  Prefer ConcurrentRule.spans tied to leave.expected_due_date so persisted
  item dates move on a healthy second PUT. Else drop re-run proof on
  healthy/crash and rely on exception_msg + item identity; AC1 coverage
  stays in re-anchor/pin.

Run the four tests once before changing production code. Crash-deletes
test should still pass as a defect document.

### B. Apply-path guard (PIE-501 AC3 + PIE-498 AC4) — primary fix
In RuleService._apply_benefit (backend/benefits/services/rules.py ~944–1011):

  if rule_result.exception is not None and rule_result.spans is None:
      logger.warning(
          "Skipping paycalc apply after evaluation exception; "
          "preserving existing items",
          result_id=result.pk,
          leave_id=result.leave_id,
      )
      return False   # BEFORE unknown→() coercion AND BEFORE
                     # "not spans and not items" record-keeping delete

CRITICAL: early-return whenever that key matches. Do NOT add `and items`.
Paycalc-linked `items` excludes paycalc__isnull=True; requiring items
still wipes record-keeping.

Do NOT call check_duplicate_clean_paycalc in that case.
Do NOT key on contains_unknown_span (UNKNOWN_SPAN + later exception would
over-preserve vs d5b96138a7).
Do NOT key on bare exception alone (later-attr exceptions after good spans).
Do NOT put policy solely in check_duplicate_clean_paycalc.
Do NOT expand into non-ABC save_results rebuild for this ticket.

Required unit tests (all of them):
- crash shape: spans=None + exception + clear contains_unknown_span cache
  (do NOT use _setup_apply_benefit(..., with_spans=False) alone — spans=()
  is not the crash shape)
- exception+None spans + applied items → preserved
- exception+None spans + NO applied items → record-keeping not wiped
- good spans + later-attr exception → still applies
- deliberate UNKNOWN_SPAN, no exception → still clears applied
- no exception + empty/ineligible spans → existing delete/recreate unchanged
- published paycalc + crash → items preserved, no forced duplicate

### C. Flip integration crash test
Preserve applied items after guard; assert exception_msg + item identity.
Do not use MPLA suggestion start or bare get_parental_max_start_date as
second-PUT re-run proof. Prefer ConcurrentRule.spans from expected_due_date
on the healthy path for a persisted re-run signal.

### D. AC2 minimum only (default)
Keep pin test + add comments on EE birth-details block and EE/Admin/HR
profile_update sites. Do NOT implement deliberate leave_profile_change.send
unless explicitly asked.

## Out of scope
- FMLA _rolling_back_day_draw null balance (PIE-498 root cause)
- PIE-495 panel copy
- past_leave_change for active leaves
- Frontend
- Todd unknown-span applied-clear policy change
- Deliberate dispatch stretch

## Verify
pytest backend/benefits/services/tests/test_rules.py -q -k 'apply_benefit'
pytest backend/legacy/views/tests/test_leave_birth_details_confirmation.py -q
pytest backend/legacy/views/tests/test_leave_viewsets.py -q -k birth

## Done when
- Re-baselined confirmation tests green; crash case PRESERVES applied time
- All required unit exception-guard tests green
- PR links PIE-501 + PIE-498 AC4; Jira comment on PIE-498 claiming AC4
- PR states AC2 = pin+comments; notes published-paycalc no-dupe on crash
- PR notes accepted residual wipe paths (D4): MissingValue/spans None
  without exception; deliberate UNKNOWN_SPAN; non-ABC rebuild
- No force-push; commit only if the user asks
```

---

## Review history

- **2026-09-18 initial:** Drafted from Jira PIE-501/498 + codebase + remote
  PIE-501 branch + todd unknown-span commit.
- **2026-09-18 round 1:** PIE-510 MPLA assertion re-baseline; D1 early return;
  AC2 pin-only; Admin/HR comments; unit crash shape; published-paycalc;
  non-ABC scope; PIE-498 ownership; handoff alignment; cite `d5b96138a7`.
- **2026-09-18 round 2:** Healthy/crash second-PUT MPLA assert is tautological
  after seed confirm; tighten D1 key to `exception and spans is None`;
  handoff: unconditional early return / no `and items`; full unit checklist;
  Done-when includes D4 residual note. Floor claim verified: before =
  estimated_due_date; after+rerun = expected_leave_date.
- **2026-09-18 round 3:** Second-PUT proof must be a *persisted*
  due-date-sensitive signal (`ConcurrentRule.spans` from `expected_due_date`),
  not leave-field math; Goal 3 scoped to ABC `_apply_benefit`; handoff adds
  logger.warning, empty-spans baseline unit case, and `_setup_apply_benefit`
  footgun warning.
- **2026-09-18 round 4:** Rewrote handoff §A/B/C to match body (ConcurrentRule
  persisted signal; full unit list; logger.warning).
- **2026-09-18 round 5:** Reviewers returned **NO FINDINGS** — handoff aligned
  with Phase 0/1/2; plan ready for implementation handoff.
