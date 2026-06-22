# Sumer — Ur III Cuneiform Tablet Pipeline

A Python pipeline for parsing CDLI ATF administrative tablets from the Ur III period (~2112–2004 BCE) into structured transactions, grain-quantity extractions, entity networks, and chronological summaries.

---

## Overview

The [CDLI](https://cdli.mpiwg-berlin.mpg.de/) (Cuneiform Digital Library Initiative) publishes bulk ATF exports of digitized cuneiform tablets. The Ur III corpus (~135,000 administrative texts) documents the world's earliest large-scale bureaucratic economy: grain rations, labor allocations, livestock transfers, silver debts, and institutional accounting across the empire of Ur-Namma, Šulgi, Amar-Suen, Šu-Suen, and Ibbi-Suen.

This pipeline:

- Parses raw ATF text into structured records (issuer, recipient, commodity, quantity, date)
- Extracts grain quantities in the Ur III sexagesimal capacity system, resolving to **sila3** (≈ 0.84 liters)
- Builds a directed weighted entity network (who gave grain/silver/animals to whom)
- Identifies patronymics and resolves name variants
- Exports CSV tables and a GEXF network file for downstream analysis

---

## Repository Layout

```
sumer/
├── atf_pipeline/          # Core Python package
│   ├── __init__.py        # Public API re-exports
│   ├── __main__.py        # python -m atf_pipeline entry point
│   ├── cli.py             # main() — full two-pass pipeline
│   ├── loaders.py         # ATF file/directory/export loaders
│   ├── extractor.py       # ATFExtractor — per-tablet dispatch
│   ├── extract_structure.py  # Record/entry structure extraction
│   ├── extract_quantity.py   # Metrological quantity parsing
│   ├── extract_dates.py   # Ur III date line parsing
│   ├── extract_entities.py   # Patronymics + entity roles
│   ├── patterns.py        # Shared compiled regexes
│   ├── models.py          # Dataclasses: Transaction, TabletSummary, etc.
│   ├── entities.py        # EntityScanner — cross-tablet entity graph
│   ├── normalize.py       # Name normalization / case-suffix merging
│   ├── chronology.py      # King → regnal year mapping
│   ├── network.py         # NetworkBuilder → GEXF export
│   └── export.py          # CSV export helpers
├── tests/                 # pytest test suite (142 tests)
│   ├── test_quantity.py
│   ├── test_structure.py
│   ├── test_dates.py
│   ├── test_entities.py
│   ├── test_parentage.py
│   ├── test_loaders_normalize.py
│   └── test_commodity.py
├── data/
│   └── cdli_export.txt    # CDLI bulk ATF export (not committed; ~87 MB)
└── output/                # Generated on pipeline run
    ├── transactions_all.csv
    ├── transactions_barley.csv
    ├── records.csv
    ├── entries.csv
    ├── tablets.csv
    ├── entities.csv
    ├── patronymics.csv
    └── barley_network.gexf
```

---

## Installation

Requires Python 3.9+. No external runtime dependencies beyond the standard library.

```bash
git clone https://github.com/asarodan/sumer.git
cd sumer
pip install -e .          # installs atf_pipeline as an editable package
```

For development (tests):

```bash
pip install pytest
pytest                    # runs all 142 tests
```

---

## Usage

### Full corpus pipeline

Place the CDLI bulk export at `data/cdli_export.txt` (download from <https://cdli.mpiwg-berlin.mpg.de/bulk-download>), then:

```bash
python -m atf_pipeline
```

Or point at a file or directory of individual ATF files:

```bash
python -m atf_pipeline data/cdli_export.txt
python -m atf_pipeline data/raw_atf/
```

Output CSVs and `barley_network.gexf` are written to `output/`.

### Programmatic API

```python
from atf_pipeline import ATFExtractor, load_cdli_export_file

corpus = load_cdli_export_file("data/cdli_export.txt")
extractor = ATFExtractor(default_king="Šulgi")

for tablet_id, lines in corpus.items():
    summary = extractor.extract_records(lines, tablet_id)
    for record in summary.records:
        for entry in record.entries:
            print(entry.qty_sila3, entry.recipient)
```

---

## The Ur III Grain Measurement System

All grain quantities are resolved to **sila3** (approximately 0.84 liters, the base unit):

| Unit     | ATF token    | In sila3     | Notes                        |
|----------|--------------|--------------|------------------------------|
| sila3    | `sila3`      | 1            | Base unit                    |
| ban2     | `ban2`       | 10           | "vessel"                     |
| barig    | `barig`      | 60           | 6 ban2                       |
| gur      | `asz` / `gur`| 300          | 5 barig; the standard jar    |
| gesz2    | `gesz2`      | 18 000       | 60 gur                       |
| gesz'u   | `gesz'u`     | 180 000      | 600 gur (10 gesz2)           |
| szar2    | `szar2`      | 1 080 000    | 3 600 gur (60 gesz2)         |
| szar'u   | `szar'u`     | 10 800 000   | 10 szar2                     |
| szargal  | `szargal`    | 64 800 000   | 60 szar2                     |

Scribes used **sexagesimal positional notation** within each unit tier. A quantity like `3(szar2) 2(gesz'u) 1(gesz2) 4(asz) 2(barig) 3(ban2) 1(disz) sila3` is parsed by summing:
```
3×1 080 000 + 2×108 000 + 1×18 000 + 4×300 + 2×60 + 3×10 + 1 = 3 477 631 sila3
```

### Implied-unit grain context (`context_gur`)

In grain-ration sections, scribes often omit the unit on individual distribution lines, expecting the reader to infer the scale from section context. For example:

```
3(gesz2) a-bu-ni              ← no unit; 3 gesz2 = 54 000 sila3 (= 180 gur)
4(gesz2) szu-{d}utu           ← no unit
sze gur                       ← section header confirming gur scale
szunigin 7(gesz2) 4(asz) sze gur   ← section total
```

The pipeline detects these "grain distribution" sections by pre-scanning for proven grain lines and sets `context_gur=True` for ambiguous lines within the section. Safeguards prevent this from misidentifying reed bundles (`sa gi`), labor totals (`a2-bi`), artisan inventories (`nig2-dag`), or worker ration rates (`geme2`, `gurusz`).

---

## Output Files

### `transactions_all.csv`

One row per identified transaction:

| Column       | Description                                   |
|--------------|-----------------------------------------------|
| `tablet_id`  | CDLI P-number (e.g. `P123456`)                |
| `issuer`     | Person issuing the commodity                  |
| `recipient`  | Person receiving it                           |
| `agent`      | Intermediary, if named                        |
| `commodity`  | Detected commodity string (`barley`, etc.)    |
| `qty`        | Quantity in sila3 (grain) or native unit      |
| `unit`       | Unit string                                   |
| `year`       | Regnal year (Šulgi 45, etc.)                  |
| `month`      | Lunar month number                            |
| `day`        | Day of month                                  |

### `entities.csv`

One row per unique entity (56 000+ in the full corpus), with occurrence count and detected roles.

### `patronymics.csv`

Name → father-name edges extracted from Sumerian patronymic constructions (`dumu PN` = "son of PN").

### `barley_network.gexf`

Directed weighted graph: nodes are entities, edges carry total barley transferred (in sila3). Import into [Gephi](https://gephi.org/) for visualization.

---

## Key Design Decisions

**Why resolve to sila3?** Keeping a single base unit avoids rounding errors when aggregating across mixed-unit records. All comparison and network-weight calculations operate on sila3 integers.

**Two-pass architecture:** Pass 1 extracts raw records and collects all attested names. Pass 2 normalizes names (merging grammatical case suffixes, e.g. `-ra` dative, `-e` ergative) using a vocabulary built from the full pass-1 name set. This prevents spurious merges when a bare form is not independently attested.

**Non-grain exclusion (`_RE_NON_GRAIN`):** Dozens of commodity terms share the sexagesimal number system with grain (wool weights, vessel counts, land measures, etc.). A compiled regex blocks those lines from grain parsing; lines are checked before attempting quantity extraction.

**CDLI determinatives:** Sumerian uses phonetic complements (e.g. `{gesz}` = wood, `{uruda}` = copper, `{u2}` = plant) as word-class markers. The pipeline uses their presence to distinguish commodity lines from personal names in ambiguous contexts.

---

## Running Tests

```bash
pytest -v
```

The test suite covers quantity parsing (sexagesimal edge cases, la2 subtraction, implied-unit context), structural extraction, date parsing, entity detection, name normalization, and ATF loading.

---

## Data Source

CDLI bulk export: <https://cdli.mpiwg-berlin.mpg.de/bulk-download>

The corpus used for development contains approximately 135,199 Ur III administrative tablets spanning ~2112–2004 BCE. The pipeline has been tuned against this corpus; other ATF periods (Old Babylonian, Sargonic, etc.) may require additional pattern adjustments.

---

## License

Research use. Please cite CDLI if you publish results derived from their data.
