"""Corpus-wide entity roster scanner."""

import csv
import logging
import os
from typing import Dict, Optional

from atf_pipeline.models import TabletSummary
from atf_pipeline.normalize import Normalizer

logger = logging.getLogger(__name__)


class EntityScanner:
    """
    Scan TabletSummary objects and build a roster of every named individual
    or institution that appears anywhere in the corpus.

    Tracks:
      - How many times the entity appears across all tablets
      - How many distinct tablets they appear on
      - Which roles they fill (issuer, recipient, agent)
    """

    def __init__(self, normalizer: Optional["Normalizer"] = None) -> None:
        self._norm = normalizer
        # canonical_name → {tablets, roles, appearances}
        self._roster: Dict[str, Dict] = {}
        # canonical_name → {canonical_father: count} (parentage / homonym data)
        self._fathers: Dict[str, Dict[str, int]] = {}

    def add_patronymics(self, pairs) -> None:
        """Record (name, father) parentage pairs, normalising both sides so the
        father set matches the canonical roster keys."""
        for name, father in pairs:
            nm = (self._norm.normalize_name(name) if self._norm else name) or name
            fa = (self._norm.normalize_name(father) if self._norm else father) or father
            self._fathers.setdefault(nm, {})
            self._fathers[nm][fa] = self._fathers[nm].get(fa, 0) + 1

    @property
    def homonym_count(self) -> int:
        """Number of names attested with two or more distinct fathers."""
        return sum(1 for fa in self._fathers.values() if len(fa) >= 2)

    def _add(self, raw_name: str, role: str, tablet_id: str) -> None:
        name = raw_name.strip()
        if not name or len(name) < 2:
            return
        canonical = (
            self._norm.normalize_name(name) if self._norm else None
        ) or name
        if canonical not in self._roster:
            self._roster[canonical] = {
                "tablets": set(),
                "roles": set(),
                "appearances": 0,
            }
        self._roster[canonical]["tablets"].add(tablet_id)
        self._roster[canonical]["roles"].add(role)
        self._roster[canonical]["appearances"] += 1

    def scan(self, summary: TabletSummary) -> None:
        for rec in summary.records:
            if rec.issuer:
                self._add(rec.issuer, "issuer", summary.tablet_id)
            if rec.agent:
                self._add(rec.agent, "agent", summary.tablet_id)
            for entry in rec.entries:
                if entry.recipient:
                    self._add(entry.recipient, "recipient", summary.tablet_id)

    def export_csv(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=[
                "entity", "appearances", "tablet_count", "roles",
                "n_fathers", "fathers"
            ])
            w.writeheader()
            for name, data in sorted(
                self._roster.items(), key=lambda x: -x[1]["appearances"]
            ):
                fathers = self._fathers.get(name, {})
                # Most-attested fathers first; this is the parentage evidence
                # for telling apart distinct individuals who share this name.
                ranked = sorted(fathers.items(), key=lambda x: -x[1])
                w.writerow({
                    "entity":       name,
                    "appearances":  data["appearances"],
                    "tablet_count": len(data["tablets"]),
                    "roles":        "|".join(sorted(data["roles"])),
                    "n_fathers":    len(fathers),
                    "fathers":      "|".join(f"{f}({c})" for f, c in ranked),
                })
        logger.info("Entity roster: %s (%d entities)", filepath, len(self._roster))

    @property
    def entity_count(self) -> int:
        return len(self._roster)

    @property
    def total_appearances(self) -> int:
        return sum(d["appearances"] for d in self._roster.values())
