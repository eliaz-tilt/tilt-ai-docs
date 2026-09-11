# Lane topology PR playbook (BKE 2.0)

Distilled from WA PFML, NJ TDI
([#11218](https://github.com/ourtilt/tilt-repo/pull/11218)), NJ FLI
([#11227](https://github.com/ourtilt/tilt-repo/pull/11227)), and NY PFL
(PIE-468). Use this before opening or updating a lane PR on `bke-integration`.

---

## What a good lane PR ships

1. **Catalog artifacts** (importable YAML)
   - `bke/catalog/banks/<code>.bank.yaml` — caps, tracking, pay role
   - `bke/catalog/topologies/<code>.topology.yaml` — lanes, waiting, scenarios,
     changelog
   - Usually **no** `tilt/rule@1` file on the lane path (WA PFML / NJ TDI
     precedent: benefit = topology + banks only)

2. **Routing levers** (Django migrations, one concern per migration when
   possible)
   - Shared levers from `0046_seed_wa_routing_levers` where applicable
     (`leaveType`, etc.)
   - Jurisdiction gate: prefer `workState` (uppercased profile snapshot) for
     WA-style programs
   - Program-specific facts in later migrations; **never reuse migration
     numbers** across parallel branches (renumber to next free slot before
     merge)

3. **BFF wiring** in `backend/benefits/rules/catalog/lanes.py`
   - `ROUTING_LEVER_KEYS_BY_TOPOLOGY` + `BANK_CODE_BY_TEMPLATE_UUID_BY_TOPOLOGY`
   - `routing_config_for_topology()` — raises on unknown codes (no silent WA
     fallback)
   - `topology_for_leave()` — jurisdiction + program flag; missing profile →
     `None` (fail closed)
   - `build_lane_evaluation_request(..., topology_code=...)` for shadow + Rule
     Studio

4. **Tests**
   - Lever realization per seeded SQL (import migration specs, do not copy SQL)
   - `topology_for_leave` flag gating + precedence when multiple flags could
     apply
   - `build_lane_evaluation_request` / `shadow_lane_decisions` on the
     **correct** topology
   - Kotlin `CatalogCorpusParseTest` + topology acceptance tests when scenarios
     exist
   - `just bke-import bke/catalog --evaluate` for scenario routing smoke

5. **PR body** (repo template + reviewer guide)
   - Issue link, flag ON/OFF table, locked decisions, out-of-scope table,
     post-merge steps
   - Call out semantics changes vs legacy BKE 1.0 even when intentional
   - Short reviewer guide paragraph (what to eyeball, not a file tour)

---

## Patterns that worked (PIE-439 and siblings)

### Encode eligibility as lane conditions, not a parallel rule file

NJ TDI deleted the redundant `nj-tdi.rule.yaml` once lanes owned awake/eligible
shape. Same pattern as WA PFML on the lane path.

### Fail closed via omitted facts

NULL survey answers → lever realization error → fact omitted → lane inactive
with an explainable reason. Do not COALESCE NULL into a false earnings or
jurisdiction fact unless legacy deliberately denied (document the difference in
the topology changelog).

### Changelog honesty

Split limitations into:

- **Schema gap** — catalog cannot express it today (example: NJ TDI 22-day retro
  wait in `lanes[].waiting` alone)
- **Deferred design** — schema could express it, but another program/PR owns it
  (example: NJ FLI bonding lives in `nj-fli`, not `nj-tdi`)
- **Blocked on data** — L&C wants it, survey/facts do not exist (COVID/PHE on
  Leave Survey 1.0)

Do not label a deferred seam as "schema cannot express" when `recoveryEnd` /
EventRef already exists (NJ TDI changelog fix in commit `93492bd`).

### Django overlay for true schema gaps (option A)

When the fold cannot re-open a served wait period:

- Keep the **standard** wait in topology YAML (7-day NJ TDI)
- Apply statute overlay in Django after bke evaluate (`apply_*_overlay` in
  `evaluate_lanes` + Rule Studio admin path)
- Mirror on legacy paycalc only if prod still uses that path; document per-env
  template seeding

### Topology-aware evaluate after every rebase

PIE-439's last commit (`a2ddc51`) fixed shadow/Rule Studio still using
WA-default lever maps after rebasing onto `bke-integration`. After any
merge/rebase, grep for:

- `build_lane_evaluation_request(leave)` without `topology_code`
- `WA_ROUTING_LEVER_KEYS` used when `topology_for_leave` returned non-WA
- Admin evaluate paths that skip program overlays

### Standalone helpers instead of legacy rule imports (preferred)

NY PFL `recoveryEnd` and `nyPflTenureMet` are SQL levers in migration `0048`
with docs pointing at legacy parity. No import of `NewYorkPFL` from
`benefits.rules.catalog.*`.

Extract shared date math into a **neutral** module
(`benefits.rules.catalog.<program>_*` or
`benefits.rules.<state>.<shared_helper>`) if both paths must match. Do not
instantiate `LegacyRule(None)` from catalog code.

---

## Mistakes to avoid (PIE-439 / dmwyatt feedback)

### Do not couple BKE 1.0 and 2.0 through catalog packages

[#11218 review](https://github.com/ourtilt/tilt-repo/pull/11218) (dmwyatt):

| Direction         | What happened                                                                                             | Why it hurts                                                                |
| ----------------- | --------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| BKE 2.0 → BKE 1.0 | `nj_tdi_recovery.py` imports `NewJerseyTDI`, calls `NewJerseyTDI(None).get_global_bonding_min_start_date` | Dead 1.0 rule becomes load-bearing for 2.0; `None` rule instance is fragile |
| BKE 1.0 → BKE 2.0 | `new_jersey/tdi.py` imports `nj_tdi_waiting` from catalog                                                 | Legacy rule now depends on lane-path package layout                         |

**Rule:** NJ TDI 1.0 is dark (flag off in prod). Either **leave 1.0 alone** or
**delete it in a separate PR**. Do not make 1.0 and 2.0 mutually import each
other.

**Fix pattern for recoveryEnd + med certs:**

1. Move date math to `benefits.rules.new_jersey.tdi_recovery.py` (or
   catalog-local pure functions with no `BaseBenefitRule` instance).
2. Legacy rule and `realize_recovery_end_lever` both call that helper.
3. Or keep V1 as SQL-only defaults and document med-cert extension as LS-handled
   (NY PFL choice).

### Do not share catalog overlay modules with legacy rules without a neutral layer

If paycalc and lane evaluate must share waiting-period math, put the math in a
small module under `benefits.rules.new_jersey/` (state domain), not under
`benefits.rules.catalog.*`.

### Migration numbering collisions

Parallel lane PRs will both add `0047_*`. Before merge into `bke-integration`:

1. Fetch latest base branch migrations
2. Renumber your program-specific migrations to the next free integer
3. Update test imports
   (`importlib.import_module("benefits.migrations.00XX_...")`)
4. Re-run merge locally; do not rely on GitHub conflict UI alone

### Rule file drift

Starting with a `tilt/rule@1` for Studio parity is fine in early commits; delete
it once lanes own eligibility, or reviewers will ask which source is
authoritative.

---

## Scope discipline (same bright line as BKE 1.0 activation PRs)

| Do                                                                             | Don't                                               |
| ------------------------------------------------------------------------------ | --------------------------------------------------- |
| Gate on collected profile/onboarding facts                                     | Stub statute slices with hard-coded defaults        |
| Document uncollected L&C items in changelog / follow-through                   | Encode COVID/PHE/chosen-family without survey facts |
| Deny unsupported caregiver enums in-engine                                     | Expand survey enums just to green a lane            |
| Document earnings thresholds in L&C copy; use `hasMet*Earnings` platform facts | Hardcode dollar thresholds in YAML conditions       |

---

## Jurisdiction routing checklist

When adding a third topology beside `wa-pfml`:

```text
topology_for_leave(leave):
  if working_state missing → None
  if state == NJ and enableBKENewJersey* → nj-* topology
  if state == NY and enableBKENewYork* → ny-* topology
  if state == WA and enableBkeLanes → wa-pfml
  else → None
```

Document precedence when multiple flags are on (NJ FLI PR: NJ beats WA when both
enabled).

Use consistent lever naming per program (`workState` vs `workingState`) only
when already shipped; do not rename in flight without a migration.

---

## Apply to your open PRs

| PR                  | Already aligned                                                                | Watch / update                                                                                                   |
| ------------------- | ------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| PIE-468 NY PFL      | SQL levers, no legacy import for recoveryEnd; topology maps; history mirroring | Confirm shadow/Rule Studio use `topology_code`; migration `0048` after rebase; no `NewYorkPFL` import in catalog |
| PIE-447 NJ FLI      | Catalog + lanes tests; changelog lists semantic deltas                         | TDI→FLI seam: do not import `NewJerseyTDI`; keep `recoveryEnd` as lever only                                     |
| DC/MA BKE 1.0 seams | Collected-data bright line (Dustin lens)                                       | Different path (legacy rules, not lane catalog) — see `reviewer/dustin.md`                                       |

---

## Pre-merge self-review (lane PRs)

- [ ] Catalog imports clean (`just bke-import bke/catalog --evaluate`)
- [ ] No `benefits.rules.catalog.*` imports in `benefits/rules/<state>/*.py`
      legacy rules
- [ ] No `benefits.rules.<state>.*` rule class imports in catalog
      realize/overlay code
- [ ] `topology_for_leave` + `build_lane_evaluation_request` + Rule Studio admin
      path agree
- [ ] Program overlay (if any) applied in **both** `evaluate_lanes` and admin
      evaluate
- [ ] Migration numbers sequential on latest `bke-integration`
- [ ] Topology changelog lists schema gaps vs deferred vs blocked-on-data
- [ ] PR template filled + Jira link + reviewer guide paragraph
- [ ] Flag registered in `settings.py` +
      `automation/flag_check/test_sync_local_flags.py`
