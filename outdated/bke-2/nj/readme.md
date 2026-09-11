# New Jersey BKE 2.0 notes

| Ticket      | PR                                                        | Doc                                                                                            |
| ----------- | --------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| PIE-439 TDI | [#11218](https://github.com/ourtilt/tilt-repo/pull/11218) | [PIE-439 retrospective](../guides/pie-439-nj-tdi-retrospective.md)                             |
| PIE-447 FLI | [#11227](https://github.com/ourtilt/tilt-repo/pull/11227) | [PIE-447 reviewer guide](../guides/pie-447-nj-fli-reviewer-guide.md) · L&C: [fli.md](./fli.md) |

Shared playbook:
[../guides/lane-topology-pr-playbook.md](../guides/lane-topology-pr-playbook.md)

---

## Reviewer guide — PIE-447 after bke-integration merge

**Pure BKE 2.0.** This PR adds NJ FLI on the lane path (catalog + BFF levers +
flag gating). It does **not** entangle legacy `NewJerseyPFL` or `NewJerseyTDI`.
If catalog code imports either, treat that as a regression.

After merging #11334, NJ FLI no longer uses hardcoded topology routing in
`lanes.py`. Discovery works like every other jurisdiction: bke resolves `nj-fli`
from the topology header, the manifest names which facts to realize, and bank
YAML `benefitRef` maps leave history. The only FLI-specific Django knob is
filtering resolved topologies when `enableBKENewJerseyPFL` is off.

**Do not ask for** `topology_for_leave` or per-program Python bank maps — that
was the pre-integration shape and conflicts with integration.

**Do ask** whether catalog lanes match L&C for V1, whether NULL earnings fail
closed, and whether birthing `recoveryEnd` semantics are documented against
future TDI seam work (see topology changelog — not a blocker to merge FLI
alone).

Full narrative for reviewers:
[pie-447-nj-fli-reviewer-guide.md](../guides/pie-447-nj-fli-reviewer-guide.md).
