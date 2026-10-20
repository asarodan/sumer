"""Immutable data models for the Ur III extraction pipeline.

A tablet is parsed into a :class:`TabletSummary` (tablet -> records -> entries)
and, in the flat pass, into :class:`Transaction` objects suitable for the
network builder.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class UrIIIDate:
    king: Optional[str] = None
    year_number: Optional[int] = None
    year_name: Optional[str] = None
    month: Optional[str] = None
    day: Optional[int] = None

    def in_range(self, king: str, year_min: int, year_max: int) -> bool:
        if self.king and king.lower() not in self.king.lower():
            return False
        if self.year_number is not None:
            return year_min <= self.year_number <= year_max
        return False

    def __str__(self) -> str:
        parts: List[str] = []
        if self.king:
            parts.append(self.king)
        if self.year_number is not None:
            parts.append(f"yr {self.year_number}")
        elif self.year_name:
            parts.append(f'mu "{self.year_name[:48]}"')
        if self.month:
            parts.append(f"iti {self.month}")
        if self.day is not None:
            parts.append(f"u4 {self.day}")
        return " | ".join(parts) if parts else "date unknown"


@dataclass
class Transaction:
    tablet_id: str
    issuer: Optional[str] = None
    recipient: Optional[str] = None
    agent: Optional[str] = None        # giri3 / ugula responsible party
    quantity: Optional[float] = None   # normalised to sila3
    unit: Optional[str] = None
    commodity: Optional[str] = None
    date: Optional[UrIIIDate] = None
    raw_date: Optional[str] = None
    line_ref: Optional[str] = None
    tx_type: Optional[str] = None      # "transfer" | "allocation" | "labor"


# Hierarchical model: Tablet -> Record -> Entry

@dataclass
class RecordEntry:
    """One line item within an administrative record."""
    entry_idx:  int
    recipient:  Optional[str]   = None
    quantity:   Optional[float] = None
    unit:       Optional[str]   = None
    commodity:  Optional[str]   = None


@dataclass
class TabletRecord:
    """
    One administrative act within a tablet.

    record_type values:
      "transfer"   — bilateral: confirmed issuer AND recipient
      "receipt"    — unilateral receipt (szu ba-ti without a ki NAME-ta, or vice-versa)
      "allocation" — szabra → engar field/grain distribution (N entries)
      "ration"     — N(asz) NAME ration list without engar marker
      "labor"      — gurusz worker-day account
      "record"     — quantity/name noted but no transfer formula found (static entry)
    """
    record_idx:  int
    record_type: str
    issuer:      Optional[str]       = None
    agent:       Optional[str]       = None
    date:        Optional[UrIIIDate] = None
    raw_date:    Optional[str]       = None
    entries:     List[RecordEntry]   = field(default_factory=list)

    @property
    def n_entries(self) -> int:
        return len(self.entries)


@dataclass
class TabletSummary:
    """Top-level container: one tablet, its type, and all its records."""
    tablet_id:   str
    tablet_type: str
    records:     List[TabletRecord] = field(default_factory=list)

    @property
    def n_records(self) -> int:
        return len(self.records)

    @property
    def n_entries(self) -> int:
        return sum(r.n_entries for r in self.records)
