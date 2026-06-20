"""Ur III cuneiform tablet extraction pipeline.

Parses CDLI ATF administrative tablets into structured transactions and a
directed-weighted exchange network.  The single-file module was split into
focused submodules; this package re-exports the original public API so that
``from atf_pipeline import ATFExtractor`` (and friends) keep working.
"""

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s [%(name)s]: %(message)s",
)

from atf_pipeline.chronology import KING_YEAR_MAP
from atf_pipeline.cli import main
from atf_pipeline.entities import EntityScanner
from atf_pipeline.export import export_hierarchy_csv, export_transactions_csv
from atf_pipeline.extractor import ATFExtractor
from atf_pipeline.loaders import (
    load_atf_file,
    load_cdli_export_file,
    load_corpus,
    parse_cdli_export,
)
from atf_pipeline.models import (
    RecordEntry,
    TabletRecord,
    TabletSummary,
    Transaction,
    UrIIIDate,
)
from atf_pipeline.network import (
    NetworkBuilder,
    compute_metrics,
    export_to_gexf,
)
from atf_pipeline.normalize import Normalizer

__all__ = [
    "ATFExtractor",
    "Normalizer",
    "NetworkBuilder",
    "EntityScanner",
    "UrIIIDate",
    "Transaction",
    "RecordEntry",
    "TabletRecord",
    "TabletSummary",
    "KING_YEAR_MAP",
    "parse_cdli_export",
    "load_cdli_export_file",
    "load_atf_file",
    "load_corpus",
    "compute_metrics",
    "export_to_gexf",
    "export_hierarchy_csv",
    "export_transactions_csv",
    "main",
]
