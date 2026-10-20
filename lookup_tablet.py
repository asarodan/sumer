#!/usr/bin/env python3
"""
lookup_tablet.py — Look up a tablet by P-number and run the parser on it.

Usage:
    python3 lookup_tablet.py P114416
    python3 lookup_tablet.py 114416
"""
import re
import sys
from atf_pipeline import ATFExtractor

DATA_FILE = "data/cdli_export.txt"

def fmt_qty(q, u):
    if q is None:
        return "—"
    if q == int(q):
        return f"{int(q):,} {u}"
    return f"{q:,.2f} {u}"

def find_tablet(pid: str, path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    for chunk in content.split("&P"):
        if not chunk.strip():
            continue
        num = chunk.split()[0].rstrip(",")
        if f"P{num}" == pid:
            return "&P" + chunk
    return ""

def run(pid: str):
    raw = find_tablet(pid, DATA_FILE)
    if not raw:
        print(f"Tablet {pid} not found in {DATA_FILE}")
        return

    # Print raw ATF
    print(f"\n{'─'*58}")
    print("RAW ATF:")
    print('─'*58)
    for line in raw.splitlines():
        if line.strip():
            print(f"  {line}")

    ext = ATFExtractor()
    lines = raw.splitlines()
    txns = ext.extract_transactions(lines, pid)
    summ = ext.extract_records(lines, pid)

    print(f"\n{'═'*58}")
    print(f"  {pid}  —  type: {summ.tablet_type}")
    print(f"{'═'*58}")

    if txns:
        print(f"\nFLAT TRANSACTIONS ({len(txns)}):")
        for i, t in enumerate(txns, 1):
            qty_str  = fmt_qty(t.quantity, t.unit)
            comm_str = f"[{t.commodity}]" if t.commodity else ""
            from_str = f"from {t.issuer}" if t.issuer else ""
            to_str   = f"→ {t.recipient}" if t.recipient else ""
            via_str  = f"via {t.agent}" if t.agent else ""
            parts = [p for p in [qty_str, comm_str, from_str, to_str, via_str] if p]
            print(f"  {i}. {' '.join(parts)}")
        total = sum(t.quantity for t in txns if t.unit == "sila3")
        if total:
            print(f"\n  TOTAL sila3: {total:,.0f}  ({total/300:,.1f} gur)")
    else:
        print("\n  (no flat transactions found)")

    if summ.records:
        print(f"\nHIERARCHY ({len(summ.records)} record(s)):")
        for rec in summ.records:
            ctx = []
            if rec.issuer:   ctx.append(f"issuer={rec.issuer}")
            if rec.agent:    ctx.append(f"agent={rec.agent}")
            if rec.raw_date: ctx.append(f"date={rec.raw_date[:40]}")
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
    if len(sys.argv) < 2:
        print("Usage: python3 lookup_tablet.py P114416")
        sys.exit(1)
    pid = sys.argv[1].strip()
    if not pid.startswith("P"):
        pid = "P" + pid
    run(pid)

if __name__ == "__main__":
    main()
