# Plan: Benefit exhaustion must not block result span persistence

**Status:** Not implemented (verified 2026-09-16)  
**Primary files:** `backend/benefits/services/rules.py`  
**Secondary files:** `backend/benefits/utils/creation.py` (optional; see approach)  
**Tests:** `backend/benefits/services/tests/test_rules.py`, `backend/benefits/utils/tests/test_creation.py`

---

## Problem summary

When BKE persists benefit rule results via `RuleService.save_results()`, benefit automation calls `_apply_benefit()`. That path couples three concerns that should be independent:

1. **Paycalc duplication** (`check_duplicate_clean_paycalc`) — needed when editing a published paycalc, but only when spans actually change.
2. **Paycalc item application** (`create_item_from_benefit` with `paycalc`) — can fail (e.g. `DataException` from benefit exhaustion in `PaycalcItem.save()`).
3. **Result span persistence** (`create_item_from_benefit` without `paycalc`) — record-keeping `PaycalcItem` rows linked only to the `Result`.

### Current failure modes

| Failure point | What breaks | Retry behavior |
|---|---|---|
| `check_duplicate_clean_paycalc()` raises | No spans saved for that result; exception caught in per-result `automate=True` try/except (`rules.py:277-280`) | Each subsequent changed result retries duplication |
| `create_item_from_benefit(paycalc=...)` raises `DataException` | Early return in `_create_paycalc_items_from_spans`; record-keeping items never created (`rules.py:1117-1121`) | N/A per span loop |
| Non-`DataException` from paycalc item save | Uncaught in `_create_paycalc_items_from_spans`; bubbles to per-result try/except | Record-keeping items never created |

The non-automation path (`automate=False`, `rules.py:290-297`) already persists spans correctly via `_create_paycalc_items_from_spans(..., use_plan_paycalc=False)`.

### Acceptance criteria (from ticket)

1. Result spans (paycalc-unlinked `PaycalcItem` rows) must **always** be persisted when spans change, regardless of paycalc duplication or benefit-application errors.
2. Paycalc creation/duplication must be attempted **only once** per `save_results()` invocation; a failure must not be retried for each result.

---

## Implementation approach

### Design principles (from review)

- **Lazy paycalc prep**: only attempt duplication when a result's spans actually changed (`changed=True`), preserving today's no-op behavior when spans match existing items.
- **Span persistence is sacred**: record-keeping item creation must not share fate with paycalc errors; structure try/except accordingly.
- **Separate signals**: distinguish "spans persisted" from "paycalc items applied" for `benefits_were_changed`, `full_abc`, and `regenerate_paycalc_data`.
- **Minimal `creation.py` churn**: `check_duplicate_clean_paycalc` has a single production caller (`rules.py:992`); split helpers only if they improve testability, otherwise inline the once-per-run guard in `RuleService`.

---

### 1. Add per-run paycalc preparation state to `RuleService`

New instance attributes (initialized in `__init__`):

```python
self._paycalc_prep_attempted: bool = False
self._paycalc_prep_failed: bool = False
```

New method `_ensure_paycalc_editable(self, *, result: Result) -> Paycalc | None`:

- Called from `_apply_benefit` only when `changed=True`.
- If `_paycalc_prep_attempted`: return `self.paycalc` (no re-attempt).
- Sets `_paycalc_prep_attempted = True` before first attempt.
- Extracts only the duplication/initiation logic from `check_duplicate_clean_paycalc` (lines 86-97 of `creation.py`):
  - `initiate_base_paycalc_for_item(plan)` if no paycalc
  - `duplicate_published_paycalc_with_all_items(...)` if published
- On success: updates `self.paycalc`, returns it.
- On failure: sets `_paycalc_prep_failed = True`, records `result.reasoning["paycalc_preparation"]` (string, matching `paycalc_item_creation` format), logs exception. Then attempt `_get_latest_paycalc()` refresh; if a draft exists, clear `_paycalc_prep_failed` and use it.
- Returns `self.paycalc` (may still be published if prep failed and no draft exists).

Subsequent changed results skip duplication when `_paycalc_prep_attempted` is already `True` (whether success or failure).

Keep `check_duplicate_clean_paycalc` unchanged for `test_creation.py`; the per-result item deletion logic moves to a new private method on `RuleService`.

### 2. Extract per-result item cleanup (two scopes)

```python
def _clear_record_keeping_items(self, result: Result) -> None:
    """Delete paycalc-unlinked items for one result. Safe on any paycalc state."""

def _clear_paycalc_linked_items(self, result: Result) -> None:
    """Delete paycalc-linked items for one result on the current editable paycalc."""
```

- `_clear_record_keeping_items`: `result.paycalc_items.filter(paycalc__isnull=True).delete()` — used by **both** automation and non-automation paths.
- `_clear_paycalc_linked_items`: only when `self.paycalc` is `DRAFT` or `PUBLISH_PENDING` (i.e. after `_ensure_paycalc_editable` succeeded). Runs the paycalc-linked deletion from `check_duplicate_clean_paycalc` (PayPeriodCalcItem wide-delete + `paycalc.items.filter(result=result).delete()`).
- **Never** delete paycalc-linked items on a `PUBLISHED` paycalc. Today this is safe because `check_duplicate_clean_paycalc` duplicates first; the new flow must preserve that invariant by calling `_ensure_paycalc_editable` before `_clear_paycalc_linked_items`.
- Document that PayPeriodCalcItem deletion is paycalc-wide (existing behavior); `regenerate_paycalc_data()` at end of `save_results` rebuilds them.

### 3. Split item creation into two methods

Replace the dual-path logic in `_create_paycalc_items_from_spans` with:

```python
def _create_record_keeping_items_from_spans(self, *, rule_result, result) -> list[PaycalcItem]:
    """Create paycalc-unlinked items (one per span). Always called when spans change."""

def _create_paycalc_linked_items_from_spans(self, *, rule_result, result) -> list[PaycalcItem]:
    """Create paycalc-linked items (one per span). Skipped when prep failed."""
```

- `_create_record_keeping_items_from_spans`: `create_item_from_benefit(paycalc=None, ...)`. On `DataException`: record `result.reasoning["paycalc_item_creation"]`, stop. These should not hit exhaustion (no paycalc), but handle gracefully.
- `_create_paycalc_linked_items_from_spans`: `create_item_from_benefit(paycalc=self.paycalc, ...)`. On `DataException`: record reasoning, **continue to next span** (no early return). Catch only `DataException` here (not broad `Exception`) to avoid masking programming errors.
- Keep `_create_paycalc_items_from_spans` as a thin wrapper delegating to both methods for backward compat with `build_paycalc_items` (preview, `persist_items=False`).

### 4. Refactor `_apply_benefit`

When spans have changed:

```python
def _apply_benefit(self, *, rule_result, result) -> tuple[bool, bool]:
    """Returns (spans_changed, paycalc_applied)."""
    ...
    if not changed:
        # no change, delete record-keeping items only (matches rules.py:956-959)
        self._clear_record_keeping_items(result)
        return False, False

    # Phase 1: ensure editable paycalc (once per save_results run; best-effort)
    if not self._paycalc_prep_failed:
        self._ensure_paycalc_editable(result=result)

    # Phase 2: always persist record-keeping spans
    self._clear_record_keeping_items(result)
    self._create_record_keeping_items_from_spans(rule_result=rule_result, result=result)

    # Phase 3: paycalc application (only on editable paycalc)
    paycalc_applied = False
    if not self._paycalc_prep_failed and self.paycalc and self.paycalc.status in (
        Paycalc.PaycalcStatus.DRAFT,
        Paycalc.PaycalcStatus.PUBLISH_PENDING,
    ):
        self._clear_paycalc_linked_items(result)
        items = self._create_paycalc_linked_items_from_spans(
            rule_result=rule_result, result=result
        )
        paycalc_applied = len(items) > 0

    return True, paycalc_applied
```

Key ordering: **prep (once) → record-keeping cleanup + create (always) → paycalc-linked cleanup + create (only on draft)**. Duplication failure does not block span persistence; published paycalc is never mutated.

### 5. Update `save_results()` orchestration

Restructure the `automate=True` branch:

```python
if automate:
    result.paycalc_item_template_overrides["bke_auto_applied"] = True
    try:
        spans_changed, paycalc_applied = self._apply_benefit(
            rule_result=result, result=persisted
        )
    except Exception:
        logger.exception(...)
        spans_changed, paycalc_applied = False, False

    # Span persistence should not depend on the outer except; if _apply_benefit
    # is structured correctly, spans_changed reflects record-keeping success.
    self.benefits_were_changed = self.benefits_were_changed or paycalc_applied

    try:
        persisted.full_abc = paycalc_applied  # per-result, not cumulative global
        persisted.save(update_fields=["full_abc"])
    except Exception:
        logger.exception(...)
```

Semantics:

| Signal | Meaning | Consumer |
|---|---|---|
| `spans_changed` | Record-keeping items were updated | Informational / logging |
| `paycalc_applied` | At least one paycalc-linked item created for this result | `full_abc` on this `Result` |
| `benefits_were_changed` | Paycalc items changed (automation or drain-down) | `regenerate_paycalc_data()`, tasks |

Record-keeping-only updates do **not** set `benefits_were_changed` (no paycalc regeneration needed).

The `automate=False` else branch: replace inline delete + `_create_paycalc_items_from_spans` with `_clear_record_keeping_items` + `_create_record_keeping_items_from_spans` only. **Do not** call `_clear_paycalc_linked_items` here — when `automate=False`, paycalc-linked items must remain untouched (matches current `rules.py:294` behavior). Does not affect `benefits_were_changed` (unchanged from today).

### 6. Extract shared automate predicate (optional but recommended)

```python
def _should_automate_result(
    self, result: BenefitResult, earning_types: dict[EarningTypes, int]
) -> bool:
```

Shared by the per-result loop; avoids duplicating the earning-type / flag / `_determine_benefit_automation_for_result` logic if any pre-check is needed later.

---

## Test plan

### New integration tests in `test_rules.py` (via `save_results()`)

1. **`test_result_spans_persist_when_paycalc_duplication_fails`**
   - Mock `duplicate_published_paycalc_with_all_items` to raise.
   - Two benefit results with span changes.
   - Assert: duplication called once; both results have record-keeping items; no paycalc-linked items; `paycalc_preparation` in reasoning.

2. **`test_result_spans_persist_when_paycalc_item_exhausted`**
   - Mock `create_item_from_benefit` to raise `DataException` only when `paycalc` is set.
   - Assert: record-keeping items exist; `paycalc_item_creation` in reasoning; `full_abc` is False.

3. **`test_paycalc_duplication_called_once_for_multiple_changed_results`**
   - Published paycalc, two changed benefit results.
   - Assert: duplication mock called exactly once.

4. **`test_no_paycalc_duplication_when_spans_unchanged`**
   - Spans match existing items (regression: lazy prep must not duplicate on no-op runs).

5. **`test_record_keeping_persistence_does_not_trigger_regenerate`**
   - Paycalc prep fails; assert `regenerate_paycalc_data` not called (`benefits_were_changed` stays False).

6. **`test_full_abc_per_result_when_mixed_paycalc_success`**
   - Two results: one paycalc succeeds, one fails exhaustion.
   - Assert: per-result `full_abc` differs.

### Update existing tests

- `_apply_benefit` tests patching `check_duplicate_clean_paycalc` → retarget to `_ensure_paycalc_editable` or `_clear_paycalc_linked_items`.
- `test_result_paycalc_creation_error` — add companion test for paycalc-path failure with record-keeping success.
- `test_create_paycalc_items_from_spans` — verify wrapper still works for `build_paycalc_items` preview path.

### Regression checks

- `test_rules_drain_down.py` — drain-down after loop; verify prep failure + published paycalc still allows drain via `_get_latest_paycalc()`.
- `benefits/utils/tests/test_creation.py` — unchanged (wrapper kept).

---

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| PayPeriodCalcItem wide-delete per result | Existing behavior; `regenerate_paycalc_data` rebuilds at end |
| `full_abc` semantics change (per-result vs cumulative) | More correct than today's `bool(self.benefits_were_changed)` global; verify `LeaveEligibilityService.is_abc_leave()` expectations in tests |
| Stale `self.paycalc` after prep failure | Refresh via `_get_latest_paycalc()` on failure |
| `contains_unknown_span` with stale items | `_clear_record_keeping_items` + zero-span path still cleans record-keeping |
| Reasoning key overwrite on multi-span failure | Accept last-error for now; document as known limitation |

---

## Implementation checklist

- [ ] Add `_paycalc_prep_attempted` / `_paycalc_prep_failed` state and `_ensure_paycalc_editable()`
- [ ] Extract `_clear_record_keeping_items()` and `_clear_paycalc_linked_items()` from `check_duplicate_clean_paycalc` deletion logic
- [ ] Split `_create_record_keeping_items_from_spans` / `_create_paycalc_linked_items_from_spans`
- [ ] Refactor `_apply_benefit` with new ordering and return tuple
- [ ] Update `save_results()` for per-result `full_abc` and `benefits_were_changed` semantics
- [ ] Add/update tests per test plan
- [ ] Run `benefits/services/tests/test_rules.py` and `test_rules_drain_down.py`
- [ ] Open PR

---

## Out of scope

- Changing benefit exhaustion logic in `PaycalcItem.save()` / tracking reducers
- Frontend display of new `paycalc_preparation` reasoning key
- Retrying paycalc duplication across separate `save_results` invocations
- Refactoring `check_duplicate_clean_paycalc` public API (single caller; keep for tests)
