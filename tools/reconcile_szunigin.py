#!/usr/bin/env python3
"""
reconcile_szunigin.py — Arithmetic self-check harness (design doc §7.1).

Measures how often a tablet's parsed grain line-items reconcile with the
scribe's own `szunigin` (grand total). A match means the ancient accountant
and our parser independently agree: a self-verified "gold" section.

This is a MEASUREMENT tool, not part of the pipeline. It answers the single
question the whole rock-solid-data plan turns on: what fraction of the corpus
self-verifies?

Scope of this first cut: GRAIN totals only (szunigin ... sze ... gur/sila3),
resolved to sila3. Animal/other commodities are a later pass. Sections whose
total or contributing lines carry damage marks are reported separately as
UNCHECKABLE — never counted as failures (design invariant I6).

Usage:
    python3 tools/reconcile_szunigin.py [data/cdli_export.txt] [--examples N]
"""
import re
import sys
from collections import Counter

from atf_pipeline import ATFExtractor
from atf_pipeline.loaders import load_cdli_export_file

# Damage / uncertainty marks that make a numeric line unsummable (I6).
_DAMAGE = re.compile(r"[\[\]#]|(?<![a-z])x(?![a-z])", re.I)
# Strip the leading "szunigin" keyword (line number already removed).
_SZU_WORD = re.compile(r"^\[?(?:szunigin2?|šunigin2?|szu-nigin2?|šu-nigin2?)\b[#!?]*\s*", re.I)
# A grain total mentions sze and resolves in a capacity unit.
_HAS_SZE = re.compile(r"\bsze\b", re.I)
# Exclude multi-commodity totals (kasz/ninda/i3 on the same szunigin line) —
# those need per-commodity splitting we don't attempt in this first cut.
_OTHER_COMM = re.compile(r"\b(kasz|ninda|i3|naga|zu2-lum|tug2|siki|ku3)\b", re.I)
# Archaic curved-number notation "(asz@c)", "(ban2@c)" marks Early Dynastic /
# Old Sumerian tablets in the bulk export. Their multi-commodity beer/emmer
# accounting does not follow Ur III conventions; exclude from this measurement.
_ARCHAIC = re.compile(r"@c\b", re.I)
# "X-bi N unit" = "its X-equivalent" conversion note (sze-bi, kas-bi, ninda-bi,
# imgaga3-bi, ...). These restate a quantity already counted elsewhere; they are
# never additive line-items. The pipeline skips them; so must the harness.
_EQUIV_BI = re.compile(r"\b\S+-bi\b", re.I)

# A CDLI capacity/count token, e.g. "4(asz)", "1(ban2)", "2(gesz2)".
_QTY_TOKEN = re.compile(r"\d+(?:/\d+)?\((?:asz|barig|ban2|sila3|gur|gesz2|gesz'u|szar2|szar'u|u|disz)[^)]*\)", re.I)

# Reconciliation tolerance. Sexagesimal capacity arithmetic is exact, so we
# expect exact integer agreement; allow 1 sila3 for half-sila3 rounding.
_TOL = 1.0


def _has_damaged_quantity(lines) -> bool:
    """True if any quantity-bearing line also carries a damage mark — such a
    tablet cannot be fairly reconciled (a missing/uncertain item, I6)."""
    for ln in lines:
        if _QTY_TOKEN.search(ln) and _DAMAGE.search(ln):
            return True
    return False


def main() -> None:
    argv = sys.argv[1:]
    want_examples = 0
    if "--examples" in argv:
        i = argv.index("--examples")
        want_examples = int(argv[i + 1])
        del argv[i:i + 2]
    positional = [a for a in argv if not a.startswith("--")]
    path = positional[0] if positional else "data/cdli_export.txt"

    ext = ATFExtractor()
    corpus = load_cdli_export_file(path)

    tally = Counter()
    balanced_ex, unbalanced_ex = [], []

    # Genre-1 isolation: a single direct grain total summed against the
    # pipeline's own extracted entries. We measure whether the PARSER's output
    # reconciles, not a naive re-derivation, so animal-rate and equivalent
    # lines are already classified correctly upstream.
    for tablet_id, lines in corpus.items():
        # Skip Early Dynastic / archaic-notation tablets (non-Ur III).
        if any(_ARCHAIC.search(ln) for ln in lines):
            continue

        # Collect the tablet's szunigin total line(s).
        szu_lines = [ln for ln in lines if ext._RE_SZUNIGIN.match(ln.strip())]
        if not szu_lines:
            continue

        szu_clean = ext._strip_linenum(szu_lines[0])
        szu_body = _SZU_WORD.sub("", szu_clean).strip()

        # Direct grain total only: must mention sze, resolve to sila3, and NOT be
        # a "sze-bi" barley-EQUIVALENT total (those restate non-grain items) or a
        # multi-commodity total.
        if _EQUIV_BI.search(szu_body):          # "szunigin sze-bi N gur" → genre 2/3
            continue
        if not _HAS_SZE.search(szu_body) or _OTHER_COMM.search(szu_body):
            continue
        total_q, total_u = ext.extract_quantity(szu_body, context_gur=True)
        if total_q is None or total_u != "sila3":
            continue

        # Genre-1 purity: exactly ONE szunigin total on the tablet (no nested
        # subtotals / grand-total double-counting).
        if len(szu_lines) > 1:
            tally["multi_szunigin"] += 1
            continue

        tally["grain_sections"] += 1

        # Any damaged quantity line anywhere → uncheckable (I6): a missing or
        # uncertain item makes the sum an unfair comparison against the total.
        if _has_damaged_quantity(lines):
            tally["uncheckable_damaged"] += 1
            continue

        # Sum the pipeline's actual grain entries for this tablet.
        summary = ext.extract_records(lines, tablet_id)
        item_sum = 0.0
        n_items = 0
        for rec in summary.records:
            for e in rec.entries:
                if e.unit == "sila3" and e.quantity is not None:
                    item_sum += e.quantity
                    n_items += 1

        if n_items == 0:
            tally["uncheckable_no_items"] += 1
            continue

        tally["checkable"] += 1
        diff = item_sum - total_q
        if abs(diff) <= _TOL:
            tally["balanced"] += 1
            if len(balanced_ex) < want_examples:
                balanced_ex.append((tablet_id, total_q, item_sum, n_items))
        else:
            tally["unbalanced"] += 1
            if len(unbalanced_ex) < want_examples:
                unbalanced_ex.append(
                    (tablet_id, total_q, item_sum, n_items, diff)
                )

    # ---- Report ----
    gs = tally["grain_sections"]
    chk = tally["checkable"]
    bal = tally["balanced"]
    print("=" * 60)
    print("  SZUNIGIN GRAIN RECONCILIATION  (genre-1: single direct total)")
    print("=" * 60)
    print(f"  Multi-szunigin tablets (excluded): {tally['multi_szunigin']:,}")
    print(f"  Single direct-grain-total tablets: {gs:,}")
    print(f"    uncheckable (damaged total) : {tally['uncheckable_damaged']:,}")
    print(f"    uncheckable (no items)      : {tally['uncheckable_no_items']:,}")
    print(f"    checkable                   : {chk:,}")
    print("-" * 60)
    if chk:
        print(f"    BALANCED   : {bal:,}  ({bal/chk*100:.1f}% of checkable)")
        print(f"    unbalanced : {tally['unbalanced']:,}  "
              f"({tally['unbalanced']/chk*100:.1f}%)")
    print("=" * 60)

    if want_examples:
        print("\n  Sample BALANCED (gold) sections:")
        for tid, t, s, n in balanced_ex:
            print(f"    {tid}: total={t:,.0f}  items={s:,.0f}  ({n} entries)")
        print("\n  Sample UNBALANCED sections:")
        for tid, t, s, n, d in unbalanced_ex:
            print(f"    {tid}: total={t:,.0f}  items={s:,.0f}  "
                  f"diff={d:+,.0f}  ({n} entries)")


if __name__ == "__main__":
    main()
