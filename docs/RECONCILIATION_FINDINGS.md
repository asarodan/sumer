# Szunigin Reconciliation — First-Pass Findings

**Tool:** `tools/reconcile_szunigin.py`
**Question (design doc §7.1, roadmap step 2):** What fraction of the corpus
self-verifies — i.e. how large is the arithmetic "gold set"?
**Scope of this pass:** grain (`sze`) totals only, resolved to sila3.

---

## Headline numbers (full corpus, 135,199 tablets in the export)

Restricting to the cleanest case — Ur III (non-archaic), a **single direct
grain total** (`szunigin N sze gur`, not a `sze-bi` barley-equivalent total),
summed against the **pipeline's own extracted entries**:

| Bucket | Count |
|--------|------:|
| Multi-szunigin tablets (excluded — nested subtotals) | 428 |
| Single direct-grain-total tablets | **585** |
| · uncheckable — damaged quantity line (I6) | 351 |
| · uncheckable — no parseable items | 20 |
| · **checkable** | **214** |
| · · **balanced (gold)** | **92 (43.0%)** |
| · · unbalanced | 122 (57.0%) |

---

## What this means

1. **The self-verifying gold set is real but small and damage-limited.** Even in
   the single cleanest genre, **60% of candidates (351/585) are excluded by
   damage** before arithmetic is even possible. Damage, not parser quality, is
   the dominant limiter on the checkable population.

2. **The arithmetic check is a precision instrument, not a broad backbone.**
   The design doc's original framing ("the backbone of trust") over-claimed.
   The measurement shows ~92 fully self-verified grain tablets — a high-purity
   but narrow oracle, valuable as a regression seed and a trusted analytical
   core for *this genre*, not a foundation under the whole corpus.

3. **Genre is the hidden variable.** "Sum of grain lines = stated total" only
   holds for **genre 1: simple list + grand total** (e.g. P102053:
   6 + 3 + 5 + 2.2.5 = 16.2.5 gur ✓). Other genres need different equations and
   were observed directly:
   - **barley-equivalent ledgers** (P100759) — items are counts × feed-rate; the
     total is a `sze-bi` equivalent, not a sum of grain lines;
   - **field-area accounts** (P102012) — `sza3-bi-ta` breakdown of area × rate;
   - **header-total** (P100892) — the total sits at the top, not in a szunigin;
   - **multi-section accounts** (P100070) — nested subtotals + a grand total.

4. **The 57% unbalanced are now a prioritised parser-bug queue.** After damage
   exclusion, most failures are *small* differences (e.g. −14, −15, −117, −220
   sila3 on 4–12 entries) — the signature of a single missed or mis-parsed
   line-item, not a structural mismatch. These are concrete, falsifiable
   targets: each one is a tablet where the scribe tells us exactly how much we
   got wrong.

---

## Consequences for the design

- **Keep the arithmetic check, reframe its role.** It is the source of a
  high-trust *gold subset* and a *regression corpus*, and a *parser-error
  detector* — not a universal trust layer. (Design doc §7.1 updated.)
- **Genre classification is a prerequisite**, not an afterthought. Reconciliation
  must dispatch on genre (direct-sum vs equivalent-ledger vs area-rate vs
  header-total) before applying an equation. This is the natural next extension
  of the harness.
- **Damage coverage must be reported, never hidden** (design doc I6, §9.0): the
  60% damage-exclusion rate *is* a finding — it quantifies how much of even the
  cleanest genre is beyond quantitative reach.

---

## Reproduce

```bash
python3 -m tools.reconcile_szunigin --examples 10
```

Counts are deterministic for a given `data/cdli_export.txt`. Tolerance is 1 sila3
(sexagesimal capacity arithmetic is exact; the tolerance only absorbs half-sila3
rounding).
