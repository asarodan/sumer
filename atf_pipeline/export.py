"""CSV exporters for the flat-transaction and hierarchical outputs."""

import csv
import logging
import os
from typing import Dict, List

from atf_pipeline.models import TabletSummary, Transaction

logger = logging.getLogger(__name__)


def export_hierarchy_csv(
    summaries: List[TabletSummary],
    tablets_path: str,
    records_path: str,
    entries_path: str,
) -> None:
    """Write the three-tier hierarchy to separate CSV files."""
    os.makedirs(os.path.dirname(os.path.abspath(tablets_path)), exist_ok=True)

    with open(tablets_path, "w", newline="", encoding="utf-8") as ft, \
         open(records_path, "w", newline="", encoding="utf-8") as fr, \
         open(entries_path, "w", newline="", encoding="utf-8") as fe:

        wt = csv.DictWriter(ft, fieldnames=[
            "tablet_id", "tablet_type", "n_records", "n_entries", "date"
        ])
        wr = csv.DictWriter(fr, fieldnames=[
            "tablet_id", "record_idx", "record_type",
            "issuer", "agent", "n_entries", "date"
        ])
        we = csv.DictWriter(fe, fieldnames=[
            "tablet_id", "record_idx", "entry_idx",
            "recipient", "quantity", "unit", "commodity"
        ])
        wt.writeheader()
        wr.writeheader()
        we.writeheader()

        for s in summaries:
            date_str = str(s.records[0].date) if s.records and s.records[0].date else ""
            wt.writerow({
                "tablet_id":   s.tablet_id,
                "tablet_type": s.tablet_type,
                "n_records":   s.n_records,
                "n_entries":   s.n_entries,
                "date":        date_str,
            })
            for rec in s.records:
                wr.writerow({
                    "tablet_id":   s.tablet_id,
                    "record_idx":  rec.record_idx,
                    "record_type": rec.record_type,
                    "issuer":      rec.issuer or "",
                    "agent":       rec.agent or "",
                    "n_entries":   rec.n_entries,
                    "date":        str(rec.date) if rec.date else "",
                })
                for entry in rec.entries:
                    we.writerow({
                        "tablet_id":  s.tablet_id,
                        "record_idx": rec.record_idx,
                        "entry_idx":  entry.entry_idx,
                        "recipient":  entry.recipient or "",
                        "quantity":   entry.quantity if entry.quantity is not None else "",
                        "unit":       (entry.unit or "sila3") if entry.quantity is not None else "",
                        "commodity":  entry.commodity or "",
                    })

    logger.info(
        "Hierarchy: %d tablets → %d records → %d entries",
        len(summaries),
        sum(s.n_records for s in summaries),
        sum(s.n_entries for s in summaries),
    )


def export_transactions_csv(transactions: List[Transaction], filepath: str) -> None:
    if not transactions:
        logger.warning("No transactions to export: %s", filepath)
        return
    fieldnames = [
        "tablet_id", "tx_type", "issuer", "recipient", "agent",
        "quantity", "unit", "commodity",
        "date_king", "date_year_number", "date_year_name",
        "date_month", "date_day", "raw_date", "line_ref",
    ]
    def _row(tx: Transaction) -> Dict:
        d = tx.date
        return {
            "tablet_id":        tx.tablet_id,
            "tx_type":          tx.tx_type or "",
            "issuer":           tx.issuer or "",
            "recipient":        tx.recipient or "",
            "agent":            tx.agent or "",
            "quantity":         tx.quantity if tx.quantity is not None else "",
            "unit":             (tx.unit or "sila3") if tx.quantity is not None else "",
            "commodity":        tx.commodity or "",
            "date_king":        d.king if d else "",
            "date_year_number": d.year_number if d else "",
            "date_year_name":   d.year_name if d else "",
            "date_month":       d.month if d else "",
            "date_day":         d.day if d else "",
            "raw_date":         tx.raw_date or "",
            "line_ref":         tx.line_ref or "",
        }
    try:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for tx in transactions:
                writer.writerow(_row(tx))
        logger.info("CSV: %s (%d rows)", filepath, len(transactions))
    except OSError as exc:
        logger.error("Failed to write CSV to %s: %s", filepath, exc)
