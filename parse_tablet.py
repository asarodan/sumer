#!/usr/bin/env python3
"""
parse_tablet.py — Quick ATF tablet parser

Usage:
    python3 parse_tablet.py < tablet.atf
    python3 parse_tablet.py tablet.atf
    echo "&P123 ..." | python3 parse_tablet.py

Paste or pipe raw ATF text; get back the transactions and entries
the pipeline finds.
"""
import re
import sys
from atf_pipeline import ATFExtractor

def fmt_qty(q, u):
    if q is None:
        return "—"
    if q == int(q):
        return f"{int(q):,} {u}"
    return f"{q:,.2f} {u}"

def run(atf_text: str):
    ext = ATFExtractor()
    lines = atf_text.splitlines()

    # Pull tablet ID from &P... header
    tablet_id = "UNKNOWN"
    for l in lines:
        m = re.match(r"&(P\d+)", l.strip())
        if m:
            tablet_id = m.group(1)
            break

    txns  = ext.extract_transactions(lines, tablet_id)
    summ  = ext.extract_records(lines, tablet_id)

    print(f"\n{'═'*58}")
    print(f"  {tablet_id}  —  type: {summ.tablet_type}")
    print(f"{'═'*58}")

    if txns:
        print(f"\nFLAT TRANSACTIONS ({len(txns)}):")
        for i, t in enumerate(txns, 1):
            qty_str   = fmt_qty(t.quantity, t.unit)
            comm_str  = f"[{t.commodity}]" if t.commodity else ""
            from_str  = f"from {t.issuer}" if t.issuer else ""
            to_str    = f"→ {t.recipient}" if t.recipient else ""
            via_str   = f"via {t.agent}" if t.agent else ""
            parts = [p for p in [qty_str, comm_str, from_str, to_str, via_str] if p]
            print(f"  {i}. {' '.join(parts)}")
    else:
        print("\n  (no flat transactions found)")

    if summ.records:
        print(f"\nHIERARCHY ({len(summ.records)} record(s)):")
        for rec in summ.records:
            ctx = []
            if rec.issuer:    ctx.append(f"issuer={rec.issuer}")
            if rec.agent:     ctx.append(f"agent={rec.agent}")
            if rec.raw_date:  ctx.append(f"date={rec.raw_date[:40]}")
            print(f"  ▸ Record {rec.record_idx} [{rec.record_type}]"
                  + (f"  {', '.join(ctx)}" if ctx else ""))
            for e in rec.entries:
                qty_str  = fmt_qty(e.quantity, e.unit)
                comm_str = f"[{e.commodity}]" if e.commodity else ""
                rec_str  = f"→ {e.recipient}" if e.recipient else ""
                parts = [p for p in [qty_str, comm_str, rec_str] if p]
                print(f"      {e.entry_idx}. {' '.join(parts)}")
    else:
        print("\n  (no hierarchical records found)")

    print()

def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    # Split on tablet boundaries if multiple tablets are pasted
    tablets = re.split(r"(?=^&P)", text, flags=re.MULTILINE)
    for tablet in tablets:
        tablet = tablet.strip()
        if tablet:
            run(tablet)

if __name__ == "__main__":
    main()
