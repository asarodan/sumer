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

# Lines where the ENTIRE beginning is erased: "7. [...] person-name" or
# "7'. [...] person-name" (prime notation for uncertain obv/rev).
# No QTY_TOKEN is visible, but the missing text almost certainly held a
# quantity — any tablet with such a line is uncheckable (I6).
_LINE_START_ERASED = re.compile(r"^\d+[a-z']?\.\s*\[\.+\]")

# "$ broken" / "$ rest broken" / "$ beginning broken" — face or portion physically missing.
_BROKEN_FACE = re.compile(r"^\$\s+(?:rest\s+|beginning\s+)?broken\b", re.I)

# "la2-ia3" = deficit/balance-forward note — identifies running-balance and
# donkey-fodder accounts where the szunigin is not a simple item sum.
_LA2_IA3 = re.compile(r"\bla2-ia3\b", re.I)

# "sza3-bi-ta" = "from within it" — marks tablets where the opening stock
# quantity comes before the keyword and equals the szunigin total; summing
# the opening stock as a line item would double-count the total.
_SZA3_BI_TA = re.compile(r"\bsza3-bi-ta\b", re.I)

# Rate-multiplication tablets: szunigin = count × rate × duration, NOT sum(items).
# "-ta" after a capacity quantity marks a PER-UNIT RATE, not a payment:
#   "1(disz) sila3 sze-ta"     = 1 sila3 barley per animal per day
#   "6(asz) sze-numun gur-ta"  = 6 gur seed grain per bur of field
# "u4 N-sze3" marks an explicit DURATION (for N days) on a rate tablet.
# "GAN2" (field-area logogram) together with rates → field-area seed calc.
_RATE_TA = re.compile(
    r"\d+(?:/\d+)?\((?:asz|barig|ban2|sila3|gur|disz)[^)]*\)"
    r"(?:\s+(?:asz|barig|ban2|sila3|gur))?"   # optional interposed capacity unit: "1(disz) sila3 sze-ta"
    r"\s+\S*-ta\b",
    re.I,
)
_DURATION = re.compile(
    r"\bu4\s+"
    r"\d+(?:/\d+)?\([^)]+\)"                              # u4 N(unit)   e.g. "1(u)"
    r"(?:\s+la2\s+\d+(?:/\d+)?\([^)]+\))?"               # optional la2 M(unit) = minus M days
    r"(?:\s+\d+(?:/\d+)?\([^)]+\))?"                     # optional sub-unit e.g. "4(disz)" in "14 days"
    r"(?:-sze3|-a)\b",                                    # duration suffix
    re.I,
)
_GAN2_RATE = re.compile(r"\bGAN2\b.*\bgur-ta\b", re.I)

# Field-grain lines: "N(gur) sze GAN2-gu4" = barley harvested from a named field.
# The pipeline's _RE_NON_GRAIN blocks GAN2-labelled entries (correct — field grain
# needs separate accounting); but if the szunigin includes both ration grain AND
# field grain the tablet is uncheckable by design.
_SZE_GAN2 = re.compile(r"\bsze\b.*\bGAN2\b", re.I)

# "nam-N(unit) person-name" = group-of-N subtotal line (e.g. "nam-1(u) lu2-utu"
# = "group of 10, under lu2-utu").  Ration tablets with group subtotals have the
# pipeline summing both individual items and the subtotals → double-count.
_NAM_GROUP = re.compile(r"\bnam-\d+\(", re.I)

# "iti N-a-kam" (month-N-it-is) ordinal month label marks multi-period tablets
# where the szunigin covers only ONE period; entries from other periods follow
# the szunigin line and must not be summed.
_ITI_AKAM = re.compile(r"\biti\s+.*?-a-kam\b", re.I)

# Tablets with a @left (edge) face that contains a quantity: the left face in
# Ur III tablets repeats the largest single entry for quick reference; the
# pipeline counts it as an additional item, creating double-counting.
_LEFT_FACE_MARKER = re.compile(r"^@left\b", re.I)

# Non-grain pipeline commodities that should never be counted toward a "sze"
# (barley) szunigin total.  The pipeline correctly labels these via commodity=.
_NON_GRAIN_COMM = frozenset({"beer", "oil", "dates", "bread", "silver", "gold"})

# Reconciliation tolerance. Sexagesimal capacity arithmetic is exact, so we
# expect exact integer agreement; allow 1 sila3 for half-sila3 rounding.
_TOL = 1.0


def _has_left_face_quantity(lines) -> bool:
    """True if the tablet has a @left face section that contains a quantity.
    The left face in Ur III tablets repeats a summary entry; the pipeline
    counts it as a new item, creating double-counting with the main face."""
    in_left = False
    for ln in lines:
        s = ln.strip()
        if _LEFT_FACE_MARKER.match(s):
            in_left = True
            continue
        if s.startswith("@") and not _LEFT_FACE_MARKER.match(s):
            in_left = False
        if in_left and _QTY_TOKEN.search(s):
            return True
    return False


def _has_damaged_quantity(lines) -> bool:
    """True if any quantity-bearing line carries a damage mark, OR if any
    data line begins with '[...]' (quantity entirely erased) — either makes
    the tablet uncheckable (I6)."""
    for ln in lines:
        if _QTY_TOKEN.search(ln) and _DAMAGE.search(ln):
            return True
        if _LINE_START_ERASED.match(ln):
            return True
    return False


def _is_genre1(lines) -> bool:
    """False for tablet genres where szunigin ≠ sum(items):
      - broken face / rest broken: items missing on damaged portion
      - la2-ia3 notes:  running-balance / donkey-fodder account
      - sza3-bi-ta:     opening-stock tablet; first quantity IS the total
      - rate-multiplication tablets: szunigin = count × rate × days,
        detected by '-ta' rate suffixes or explicit 'u4 N-sze3' durations
        (animal-fodder, boat-hire, field-seed-rate calculations)
      - mixed-grain tablets: szunigin combines ration grain and field grain
        ("sze GAN2-gu4"); pipeline correctly excludes field-grain lines
      - group-subtotal tablets: "nam-N(unit) person" markers mean the tablet
        has group subtotals that the pipeline sums alongside individual items
      - multi-period tablets: "iti N-a-kam" ordinal month label means the
        szunigin covers only one period; later-period data must not be summed
    """
    has_rate = False
    has_duration = False
    for ln in lines:
        s = ln.strip()
        if _BROKEN_FACE.match(s):
            return False
        if _LA2_IA3.search(s) or _SZA3_BI_TA.search(s):
            return False
        if _GAN2_RATE.search(s):
            return False
        # A quantity line labelled "sze GAN2-gu4" (field grain) is excluded by
        # the pipeline; any tablet mixing field grain and ration grain in the
        # same szunigin total is uncheckable.
        if _QTY_TOKEN.search(s) and _SZE_GAN2.search(s):
            return False
        # "nam-N(unit) person" = named group subtotal: pipeline sums both
        # the individual lines and the group total → double-count.
        if _NAM_GROUP.search(s):
            return False
        # "iti N-a-kam" = ordinal month label: szunigin covers only that month;
        # additional quantities for other months must not be included in the sum.
        if _ITI_AKAM.search(s):
            return False
        if _RATE_TA.search(s):
            has_rate = True
        if _DURATION.search(s):
            has_duration = True
    # Both a per-unit rate AND an explicit duration → rate-multiplication tablet.
    if has_rate and has_duration:
        return False
    # @left face with a quantity → pipeline double-counts the edge entry.
    if _has_left_face_quantity(lines):
        return False
    return True


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

        # Genre-1 content check: exclude tablets whose structure means
        # szunigin ≠ sum(items) by design (broken face, balance accounts,
        # opening-stock / sza3-bi-ta tablets).
        if not _is_genre1(lines):
            tally["uncheckable_damaged"] += 1
            continue

        # Any damaged quantity line anywhere → uncheckable (I6): a missing or
        # uncertain item makes the sum an unfair comparison against the total.
        if _has_damaged_quantity(lines):
            tally["uncheckable_damaged"] += 1
            continue

        # Sum the pipeline's actual grain entries for this tablet.
        # Exclude entries the pipeline labelled as clearly non-grain commodities
        # (oil, beer, dates, bread, silver, gold): the szunigin covers "sze"
        # (barley) only, so mixing in other commodities would inflate the sum.
        summary = ext.extract_records(lines, tablet_id)
        item_sum = 0.0
        n_items = 0
        for rec in summary.records:
            for e in rec.entries:
                if (e.unit == "sila3" and e.quantity is not None
                        and e.commodity not in _NON_GRAIN_COMM):
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
