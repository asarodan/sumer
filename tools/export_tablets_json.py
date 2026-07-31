"""Export a curated JSON of the richest grain tablets for the web visualizer.

Each tablet is reduced to its headline grain movement plus pre-computed
real-world equivalents (litres, kilograms, person-days of food, people fed for
a year), so the front-end is pure display with no metrology logic of its own.

Conversions (rounded, approximate — labelled as such in the UI):
  1 sila3  ~= 1 litre           (standard teaching approximation; ~0.84 L exact)
  1 litre  ~= 0.62 kg barley    (bulk density of barley grain)
  ration   = 2 sila3 / person / day   (the classic Ur III adult male barley ration)
  year     = 360 days                 (administrative year)

Usage:
  python3 tools/export_tablets_json.py [corpus.atf] [-o web/tablets.json] [-n 400]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re

from atf_pipeline import ATFExtractor, Normalizer, load_cdli_export_file

GRAIN_COMMS = {"barley", "emmer", "wheat", "flour", "bread", "beer", "dates"}
RATION_PER_DAY = 2.0      # sila3 per person per day
YEAR_DAYS = 360

_RE_DESIG = re.compile(r"^&P\d+\s*=\s*(.+?)\s*$")


def _designation(lines) -> str:
    if lines:
        m = _RE_DESIG.match(lines[0].strip())
        if m:
            return m.group(1)
    return ""


def _date_label(d) -> str | None:
    # Only surface a date the parser actually resolved to a year; the bare
    # king default is not trustworthy enough to print as fact.
    if d and d.king and d.year_number is not None:
        return f"{d.king} year {d.year_number}"
    return None


def build(corpus, top_n: int):
    ext = ATFExtractor(default_king="Šulgi")
    nz = Normalizer()
    # Fit the normaliser so actor names are merged consistently.
    raw_names = []
    extracted = {}
    for tid, lines in corpus.items():
        txs = ext.extract_transactions(lines, tid)
        extracted[tid] = txs
        for t in txs:
            raw_names += [t.issuer, t.recipient]
    nz.fit([n for n in raw_names if n])

    records = []
    for tid, txs in extracted.items():
        grain = [t for t in txs
                 if t.quantity and t.unit == "sila3" and t.commodity in GRAIN_COMMS]
        if not grain:
            continue
        head = max(grain, key=lambda t: t.quantity)          # headline movement
        total = sum(t.quantity for t in grain)
        issuer = nz.normalize_name(head.issuer)
        recipient = nz.normalize_name(head.recipient)
        date = _date_label(head.date)
        # Richness: how complete a story this tablet can tell.
        richness = 1 + bool(issuer) + bool(recipient) + bool(date)
        sila3 = round(head.quantity)
        records.append({
            "id": tid,
            "designation": _designation(corpus[tid]),
            "commodity": head.commodity,
            "sila3": sila3,
            "tablet_total_sila3": round(total),
            "litres": sila3,
            "kg": round(sila3 * 0.62),
            "person_days": round(sila3 / RATION_PER_DAY),
            "people_year": round(sila3 / (RATION_PER_DAY * YEAR_DAYS), 1),
            "issuer": issuer,
            "recipient": recipient,
            "date": date,
            "richness": richness,
        })

    # Rank by completeness first, then by scale (log so a few giants don't
    # dominate), so the gallery leads with vivid, well-attested tablets.
    records.sort(key=lambda r: (r["richness"], math.log10(max(r["sila3"], 1))),
                 reverse=True)
    return records[:top_n]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("corpus", nargs="?", default="data/cdli_export.txt")
    ap.add_argument("-o", "--output", default="web/tablets.json")
    ap.add_argument("-n", "--top", type=int, default=400)
    args = ap.parse_args()

    corpus = load_cdli_export_file(args.corpus)
    records = build(corpus, args.top)
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    payload = {
        "meta": {
            "count": len(records),
            "conversions": {
                "sila3_to_litre": 1.0,
                "litre_to_kg_barley": 0.62,
                "ration_sila3_per_day": RATION_PER_DAY,
                "year_days": YEAR_DAYS,
            },
            "note": "Quantities are parsed from CDLI ATF; equivalents are "
                    "approximate and for illustration.",
        },
        "tablets": records,
    }
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    print(f"wrote {len(records)} tablets -> {args.output}")


if __name__ == "__main__":
    main()
