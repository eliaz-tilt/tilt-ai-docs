# BKE 1.0 vs 2.0 lane catalog — archived reviewer lens

**Archived from [`reviewer/dustin.md`](../../reviewer/dustin.md).** BKE 2.0 is
cancelled; keep this file for historical PR archaeology only.

---

From [PIE-439 NJ TDI #11218](https://github.com/ourtilt/tilt-repo/pull/11218)
(dmwyatt):

| Anti-pattern                        | Example                                                                       |
| ----------------------------------- | ----------------------------------------------------------------------------- |
| Catalog imports legacy rule class   | `nj_tdi_recovery.py` → `NewJerseyTDI(None).get_global_bonding_min_start_date` |
| Legacy rule imports catalog package | `new_jersey/tdi.py` → `benefits.rules.catalog.nj_tdi_waiting`                 |

Dark BKE 1.0 rules (flag off in prod) should stay untouched, or be **deleted in
a separate PR**. Do not make 1.0 and 2.0 mutually dependent across package
boundaries.

**Prefer:** pure helpers under `benefits.rules.<state>.*`, SQL levers in
migrations, or V1 scope that documents LS-handled gaps.

See also [lane-topology-pr-playbook.md](../guides/lane-topology-pr-playbook.md).

**Lane catalog PR checklist (historical):**

- [ ] No cross-imports between `benefits.rules.catalog.*` and legacy
      `benefits.rules.<state>.*` rule classes; shared math lives in a neutral
      helper
