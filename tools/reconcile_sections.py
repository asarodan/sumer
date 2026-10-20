#!/usr/bin/env python3
"""
reconcile_sections.py — Section-level šunigin reconciliation.

The tablet-level harness (reconcile_szunigin.py) restricts itself to genre-1
tablets with exactly ONE šunigin, excluding 400+ multi-šunigin tablets from
arithmetic ground truth entirely.  But every šunigin closes its own section:
on a multi-total tablet each (line-items, closing šunigin) pair is an
independent arithmetic check the ancient scribe performed.  This tool splits
multi-šunigin tablets at their total lines and reconciles each segment
separately, applying the same fairness gates (damage, rate-tables,
balance-accounts, si-sa2 metrology) per segment.

Nesting degrades safely: on a subtotal…subtotal…grand-total tablet, the
grand total's own segment contains no line items and is reported
uncheckable rather than failed.

Usage:
    python3 tools/reconcile_sections.py [data/cdli_export.txt] [--examples N]
"""
import sys
from collections import Counter

sys.path.insert(0, ".")
sys.path.insert(0, "tools")

from atf_pipeline import ATFExtractor                      # noqa: E402
from atf_pipeline.loaders import load_cdli_export_file     # noqa: E402
import reconcile_szunigin as rs                            # noqa: E402


def split_at_szunigin(ext, lines):
    """Yield (segment_lines, szunigin_line) pairs; segment excludes the total."""
    seg = []
    for ln in lines:
        if ext._RE_SZUNIGIN.match(ln.strip()):
            yield seg, ln
            seg = []
        else:
            seg.append(ln)
    # trailing lines after the last total (colophon, date) are not a segment


# Commodity of a szunigin total line, for the consecutive-totals pattern
# (one mixed item block closed by one total per commodity).
def total_commodity(szu_body):
    import re
    if re.search(r"\bzi3\b|\bdabin\b|\besza\b", szu_body, re.I):
        return "flour"
    if re.search(r"\bziz2\b", szu_body, re.I):
        return "emmer"
    if re.search(r"\bgig\b", szu_body, re.I):
        return "wheat"
    if re.search(r"\bsze\b", szu_body, re.I):
        return "barley"
    return None


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
    unbalanced_ex, balanced_ex = [], []

    for tablet_id, lines in corpus.items():
        if any(rs._ARCHAIC.search(ln) for ln in lines):
            continue
        szu_lines = [ln for ln in lines if ext._RE_SZUNIGIN.match(ln.strip())]
        if len(szu_lines) < 2:
            continue  # single-total tablets belong to the parent harness
        # A physically broken face makes any segment boundary unreliable.
        if any(rs._BROKEN_FACE.match(ln.strip()) for ln in lines):
            tally["tablet_broken_face"] += 1
            continue

        tally["tablets_considered"] += 1
        body = ext._strip_secondary_sections(lines)

        # Per-tablet state for the two multi-total layouts:
        #  * consecutive per-commodity totals over ONE mixed item block —
        #    later totals arrive with empty segments and are checked against
        #    the last item block's per-commodity sums;
        #  * nested subtotals closed by a grand total — an empty-segment
        #    total is checked against the sum of the totals since the last
        #    grand match.
        prev_sums = None          # per-commodity sums of last item block
        prior_totals = []         # grain totals seen since last grand match

        for seg, szu_line in split_at_szunigin(ext, body):
            szu_clean = ext._strip_linenum(szu_line.strip())
            szu_body = rs._SZU_WORD.sub("", szu_clean).strip()

            # Direct single-grain-commodity totals only.
            comm = total_commodity(szu_body)
            if rs._EQUIV_BI.search(szu_body):
                tally["sec_equiv_total"] += 1
                continue
            if comm is None or rs._OTHER_COMM.search(szu_body):
                tally["sec_nongrain_total"] += 1
                continue
            if rs._SISA2.search(szu_body):
                tally["sec_sisa2"] += 1
                continue
            total_q, total_u = ext.extract_quantity(szu_body, context_gur=True)
            if total_q is None or total_u != "sila3":
                tally["sec_unparsed_total"] += 1
                continue
            if rs._DAMAGE.search(szu_body):
                tally["sec_damaged_total"] += 1
                continue

            tally["sec_grain_total"] += 1

            # Per-segment structure gates: rate tables, balance accounts and
            # opening-stock restatements make šunigin ≠ sum(items) by design.
            # A gated segment's ITEMS are uncheckable, but its total line is
            # legible and remains valid input to a later grand-over-subtotals
            # check (the scribe summed his subtotals whether or not we can
            # verify each block's items).
            seg_text = [ext._strip_linenum(l.strip()) for l in seg]
            if any(rs._RATE_TA.search(t) for t in seg_text):
                tally["sec_rate_table"] += 1
                prev_sums = None
                prior_totals.append(total_q)
                continue
            if any(rs._LA2_IA3.search(t) for t in seg_text) \
                    or any(rs._SZA3_BI_TA.search(t) for t in seg_text):
                tally["sec_balance_acct"] += 1
                prev_sums = None
                prior_totals.append(total_q)
                continue
            if rs._has_damaged_quantity(seg):
                tally["sec_damaged_items"] += 1
                prev_sums = None
                prior_totals.append(total_q)
                continue

            summary = ext.extract_records(seg, tablet_id)
            sums = {"barley": 0.0, "emmer": 0.0, "wheat": 0.0, "flour": 0.0,
                    "all": 0.0}
            n_items = 0
            for rec in summary.records:
                for e in rec.entries:
                    if e.unit != "sila3" or e.quantity is None:
                        continue
                    if e.commodity in rs._NON_GRAIN_COMM:
                        continue
                    n_items += 1
                    sums["all"] += e.quantity
                    if e.commodity in ("emmer", "wheat", "flour"):
                        sums[e.commodity] += e.quantity
                    else:
                        sums["barley"] += e.quantity

            if n_items == 0:
                # An empty-segment total is read against whichever layout the
                # scribe used: a per-commodity total over the previous item
                # block, or a grand total over the subtotals above it.  Either
                # arithmetic match verifies the extraction.
                percomm_ok = (prev_sums is not None and comm in prev_sums
                              and abs(prev_sums[comm] - total_q) <= rs._TOL)
                grand_ok = (len(prior_totals) >= 2
                            and abs(sum(prior_totals) - total_q) <= rs._TOL)
                if percomm_ok or grand_ok:
                    tally["sec_checkable"] += 1
                    tally["sec_balanced"] += 1
                    if percomm_ok:
                        tally["sec_balanced_percomm"] += 1
                    else:
                        tally["sec_balanced_grand"] += 1
                        prior_totals = []
                    continue
                if prev_sums is not None and comm in prev_sums:
                    # Both layouts available, neither balances: report against
                    # the per-commodity reading.
                    tally["sec_checkable"] += 1
                    tally["sec_unbalanced"] += 1
                    if len(unbalanced_ex) < want_examples:
                        unbalanced_ex.append((tablet_id, total_q,
                                              prev_sums[comm], 0,
                                              prev_sums[comm] - total_q))
                    continue
                tally["sec_no_items"] += 1
                continue

            # Segment with its own items: two-pass scope like the parent.
            if abs(sums["barley"] - total_q) <= rs._TOL:
                item_sum = sums["barley"]
            elif abs(sums["all"] - total_q) <= rs._TOL:
                item_sum = sums["all"]
            else:
                item_sum = sums["barley"] if comm == "barley" else sums.get(comm, 0.0)

            prev_sums = sums
            prior_totals.append(total_q)
            tally["sec_checkable"] += 1
            if abs(item_sum - total_q) <= rs._TOL:
                tally["sec_balanced"] += 1
                if len(balanced_ex) < want_examples:
                    balanced_ex.append((tablet_id, total_q, n_items))
            else:
                tally["sec_unbalanced"] += 1
                if len(unbalanced_ex) < want_examples:
                    unbalanced_ex.append(
                        (tablet_id, total_q, item_sum, n_items, item_sum - total_q))

    chk = tally["sec_checkable"]
    bal = tally["sec_balanced"]
    print("=" * 62)
    print("  SECTION-LEVEL SZUNIGIN RECONCILIATION (multi-total tablets)")
    print("=" * 62)
    print(f"  multi-szunigin tablets considered : {tally['tablets_considered']:,}")
    print(f"  (skipped: broken face)            : {tally['tablet_broken_face']:,}")
    print(f"  segments with direct grain total  : {tally['sec_grain_total']:,}")
    print(f"    rate-table segments (excluded)  : {tally['sec_rate_table']:,}")
    print(f"    balance-account segments (excl) : {tally['sec_balance_acct']:,}")
    print(f"    damaged items (uncheckable)     : {tally['sec_damaged_items']:,}")
    print(f"    no items (grand-over-subtotals) : {tally['sec_no_items']:,}")
    print("-" * 62)
    print(f"    CHECKABLE sections              : {chk:,}")
    print(f"    BALANCED                        : {bal:,}"
          f"  ({100 * bal / max(chk, 1):.1f}% of checkable)")
    print(f"      of which per-commodity totals : {tally['sec_balanced_percomm']:,}")
    print(f"      of which grand-over-subtotals : {tally['sec_balanced_grand']:,}")
    print(f"    unbalanced                      : {tally['sec_unbalanced']:,}")
    print("=" * 62)
    if unbalanced_ex:
        print("  unbalanced examples (tablet, scribe total, our sum, items, diff):")
        for t in unbalanced_ex:
            print(f"    {t[0]}: total={t[1]:,.0f} sum={t[2]:,.0f} "
                  f"items={t[3]} diff={t[4]:+,.0f}")


if __name__ == "__main__":
    main()
