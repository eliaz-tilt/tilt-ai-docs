# Reviewer guide: `[None]` reaccrual sentinel & rule-eval failures

Distilled from Dustin Wyatt’s Datadog notebook + PR
[#11477](https://github.com/ourtilt/tilt-repo/pull/11477) review (dev DC PFL QA,
Aug 2026). Use when reviewing **tracking / span limiter** fixes or investigating
silent BKE rule failures.

Related: [Reviewing like Dustin](dustin.md) ·
[BKE rule creation](../bke/bke-rule-creation-guide.md)

---

## Symptom

- Datadog: `@logger:benefits.rules`
  `@event:"Failure evaluating benefits.rules…"`
- Exceptions swallowed by `_eval_expression` → rule produces **no result row**,
  not a user-visible error
- Common signatures when `HistoricalProfile.hire_date` is NULL:
  - `TypeError: unsupported operand type(s) for +: 'NoneType' and 'datetime.timedelta'`
    (`ROLLING_FORWARD_SUNDAY`)
  - `AttributeError: 'NoneType' object has no attribute 'year'` (calendar /
    rolling-back paths)

Leave id is `@extra.leave` (not `@leave`).

---

## Root cause

```text
get_benefit_period_dates (tracking/services/base.py:~936)
  → if not profile or not profile.hire_date: return None, None, [None]

SpanLimiter.prepare → _get_tracking_banks → reaccrual_dates = [None]

_segment_entitlements_by_reaccrual
  → reaccrual_date_func(None, …)  💥
```

`[None]` is an **honest documented sentinel** (“window undefined”). Consumers
must not treat it as a real reaccrual date.

Survey may have `hireDate` while `HistoricalProfile.hire_date` is NULL —
separate data/sync question.

---

## Fix pattern (approved in #11477)

| Layer                                                                                    | What to do                                                                                                            |
| ---------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| **`_get_tracking_banks`** (primary)                                                      | After `get_benefit_period_dates`, call `_resolve_reaccrual_dates_for_span_limiter`                                    |
| **Measured-forward** (`ROLLING_FORWARD`, `ROLLING_FORWARD_SUNDAY`, `ROLLING_FORWARD_24`) | Reuse `_get_rolling_forward_fallback_dates` — **same as** `can_benefit_accommodate_update` at `base.py:1548`          |
| **Non-measured-forward** (`CALENDAR_YEAR`, `ROLLING_BACK`, …)                            | Keep sentinel; `_segment_entitlements_by_reaccrual` skips `None` (no crash; no synthesized window)                    |
| **Types**                                                                                | Widen to `date \| None` on `SpanLimiter.reaccrual_dates`, `_get_tracking_banks` return, `_parent_remaining_by_window` |

### Do **not**

- Return `[]` from `_limit_spans_fixed_reaccrual` alone — reads as “covers zero
  days”, hides missing hire date, drops failure logs
- Emit `UNKNOWN_SPAN` from SpanLimiter — it limits existing spans; use fallback
  synthesis or let base `calculate_spans` handle schedule gaps
- Fix only in `get_benefit_period_dates` — changes meaning of `[None]` for
  reducers (`tracking/reducers.py:157`, `:377`, `:769`) that already guard
  `if None in (...)`

---

## DC PFL–specific: empty `leave_schedule`

`DCPFL.calculate_spans` indexed `leave_schedule[0]` before base guards.

**Pattern:** delegate to `super().calculate_spans(...)` when schedule empty so
base `require()` runs **before** empty-schedule → `UNKNOWN_SPAN` at
`benefits/rules/__init__.py:3213`.

Oregon PLO already had an early guard; prefer **super delegation** over
duplicating the reason string.

Put tests **inside** the class that carries `@pytest.mark.django_db()` — module
autouse fixtures (`template_dc_pfl`) need DB even for “standalone” tests.

---

## Test checklist

- [ ] `_segment_entitlements_by_reaccrual([None], …)` → `{}` (direct; deleting
      `continue` fails CI)
- [ ] `_resolve_reaccrual_dates_…` with `[None]` + measured-forward → real dates
      (not `[None]`)
- [ ] `_limit_spans_fixed_reaccrual` + `CALENDAR_YEAR` + `[None]` → no crash
      (may return `[]`)
- [ ] DC PFL empty schedule → `UNKNOWN_SPAN` via super path, inside `TestDCPFL`

---

## Dustin review lenses (this incident)

1. **Semantics:** missing hire date ≠ zero coverage — align with paycalc
   accommodation path for measured-forward
2. **Guard placement:** resolve where dates are still in hand
   (`_get_tracking_banks`), not deep in limiter
3. **UX / observability:** silent `[]` vs named missing data vs synthesized
   window
4. **Test coverage:** exercise the branch your guard protects (segmenter direct
   test, not only early-return in limiter)
5. **Types:** if code handles `None`, annotations must say `date | None` or
   guards look dead
6. **require() ordering:** empty-schedule handling must not skip base
   `require()` for return/start dates
7. **Scope:** parental_disability `leave_schedule=` copy-paste (`dc/pfl.py:209`,
   `oregon/plo.py:180`) → separate PR

---

## Datadog queries (dev)

```text
env:dev @logger:benefits.rules @event:"Failure evaluating benefits.rules.dc.pfl.DCPFL"
env:dev @logger:benefits.rules @event:"Failure evaluating benefits.rules.dc.pfl.DCPFL" "unsupported operand type"
env:dev @logger:benefits.rules status:error "has no attribute 'year'"
```

Traceback is on `custom.exception`, not `message`.

---

## Key files

| File                              | Role                                                                                                     |
| --------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `tracking/services/base.py:936`   | Returns `[None]` sentinel                                                                                |
| `tracking/services/base.py:1454`  | `_get_rolling_forward_fallback_dates`                                                                    |
| `benefits/rules/tracking.py`      | `_get_tracking_banks`, `_resolve_reaccrual_dates_for_span_limiter`, `_segment_entitlements_by_reaccrual` |
| `benefits/rules/dc/pfl.py`        | `calculate_spans` partial-day + empty schedule                                                           |
| `benefits/rules/__init__.py:3211` | Base empty-schedule → `UNKNOWN_SPAN`                                                                     |

---

## Open follow-ups

- Profile `hire_date` NULL while survey populated — dev test data or sync gap?
- Consolidate duplicated “No applicable leave schedules…” reason string (dc/pfl,
  oregon/plo, base)
- Parental disability partial-day branch passing wrong schedule to
  `find_full_leave_periods` — separate PR
