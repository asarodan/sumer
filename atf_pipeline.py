"""
atf_pipeline.py

Pipeline for parsing Ur III cuneiform administrative tablets (ATF format)
from the CDLI corpus, extracting barley ration transactions from the Umma
provincial archive, and modelling them as a directed weighted network.

ATF format docs:  https://oracc.museum.upenn.edu/doc/help/editinginatf/
CDLI year names:  https://cdli.mpiwg-berlin.mpg.de/
BDTNS:            https://bdtns.filol.csic.es/
"""

import csv
import logging
import os
import re
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

import networkx as nx

logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s]: %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Ur III chronological reference data
# ---------------------------------------------------------------------------
# Year-name fragment lists: ALL listed substrings must appear in the year-name
# line for a match.  Verify year numbers against CDLI / BDTNS before use.

_URNAMMA_FRAGS: Dict[int, List[str]] = {
    1:  ["nanna-e2-a"],
    2:  ["ki-en-gi ki-uri"],
    5:  ["bad3 uri5{ki}"],
}

_ŠULGI_FRAGS: Dict[int, List[str]] = {
    1:  ["lugal-uri5{ki}-ma"],
    3:  ["en-{d}inanna"],
    # Years 45-48 are the primary target range for Umma barley records
    45: ["ki-maški{ki}", "hu-ur5-ti{ki}"],
    46: ["ús2-sa ki-maški{ki}"],
    47: ["har-ši{ki}"],
    48: ["ús2-sa har-ši{ki}"],
    # NOTE: bad3 mar-tu ba-du3 is Šu-Suen 4, not Šulgi 44 — see _ŠUSUEN_FRAGS
}

_AMARSUEN_FRAGS: Dict[int, List[str]] = {
    1:  ["uri2{ki}-a"],
    2:  ["en-{d}inanna"],
    6:  ["ša-aš-šu{ki}"],
    9:  ["hu-uh2-nu-ri{ki}"],
}

_ŠUSUEN_FRAGS: Dict[int, List[str]] = {
    1:  ["ma2 {d}en-zu"],
    3:  ["šu-{d}suen bad3"],
    4:  ["bad3 mar-tu ba-du3"],   # Amorite wall built (moved from erroneous Šulgi 44)
    6:  ["za-ab-ša-li{ki}"],      # Zabšali campaign (moved from erroneous SS 4)
}

# Maps lowercase ATF king-name variant → (canonical display name, year-frag dict)
KING_YEAR_MAP: Dict[str, Tuple[str, Dict[int, List[str]]]] = {
    "ur-namma":      ("Ur-Namma",   _URNAMMA_FRAGS),
    "ur-{d}namma":   ("Ur-Namma",   _URNAMMA_FRAGS),
    "šul-gi":        ("Šulgi",      _ŠULGI_FRAGS),
    "{d}šul-gi":     ("Šulgi",      _ŠULGI_FRAGS),
    "šulgi":         ("Šulgi",      _ŠULGI_FRAGS),
    "sulgi":         ("Šulgi",      _ŠULGI_FRAGS),
    "amar-{d}suen":  ("Amar-Suen",  _AMARSUEN_FRAGS),
    "amar-suen":     ("Amar-Suen",  _AMARSUEN_FRAGS),
    "šu-{d}suen":    ("Šu-Suen",    _ŠUSUEN_FRAGS),
    "šu-suen":       ("Šu-Suen",    _ŠUSUEN_FRAGS),
    "ibbi-{d}suen":  ("Ibbi-Suen",  {}),
    "ibbi-suen":     ("Ibbi-Suen",  {}),
    "ibi-{d}suen":   ("Ibbi-Suen",  {}),
}


# ---------------------------------------------------------------------------
# Transliteration normalisation
# ---------------------------------------------------------------------------

def normalize_atf(line: str) -> str:
    """
    Convert CDLI legacy ASCII transliteration digraphs to Unicode equivalents
    so that standard text-dump exports are handled identically to Unicode ATF.

    Conversions applied (case-preserving):
      sz / SZ  →  š / Š   (CDLI ASCII representation of esh/shin)

    Called on every input line before pattern matching and on every name
    string before normalisation lookups, ensuring ASCII corpus downloads
    do not silently bypass regex filters or fragment matching.
    """
    # sz is exclusively used as the ASCII digraph for š in Sumerian ATF;
    # no independent s+z sequence exists in standard CDLI transliteration.
    line = line.replace("SZ", "Š").replace("sz", "š")
    return line


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class UrIIIDate:
    """Structured Ur III administrative date (king + regnal year + month + day)."""
    king: Optional[str] = None
    year_number: Optional[int] = None
    year_name: Optional[str] = None   # full mu-line content
    month: Optional[str] = None       # iti month name
    day: Optional[int] = None         # u4 day number

    def in_range(self, king: str, year_min: int, year_max: int) -> bool:
        """True if this date falls within [year_min, year_max] for the given king."""
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
    quantity: Optional[float] = None   # normalised to sila3
    unit: Optional[str] = None         # primary metrological unit as written
    commodity: Optional[str] = None
    date: Optional[UrIIIDate] = None
    raw_date: Optional[str] = None     # verbatim mu-line from tablet
    line_ref: Optional[str] = None     # first content line number


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

def load_atf_file(filepath: str) -> List[str]:
    """
    Load an ATF file, trying multiple encodings to handle CDLI corpus variation.
    Returns a list of lines (trailing newlines stripped), or [] on any failure.
    """
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            with open(filepath, "r", encoding=enc) as fh:
                return [line.rstrip("\n") for line in fh]
        except UnicodeDecodeError:
            continue
        except OSError as exc:
            logger.error("Cannot open %s: %s", filepath, exc)
            return []
    logger.warning("No working encoding found for %s; skipping.", filepath)
    return []


def load_corpus(directory: str) -> Dict[str, List[str]]:
    """Load all *.atf files from a directory. Returns {filename: [lines]}."""
    if not os.path.isdir(directory):
        logger.error("Corpus directory not found: %s", directory)
        return {}

    corpus: Dict[str, List[str]] = {}
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".atf"):
            continue
        path = os.path.join(directory, filename)
        lines = load_atf_file(path)
        if lines:
            corpus[filename] = lines
        else:
            logger.warning("Skipped empty or unreadable file: %s", filename)

    logger.info("Loaded %d ATF files from %s", len(corpus), directory)
    return corpus


# ---------------------------------------------------------------------------
# ATF Extractor
# ---------------------------------------------------------------------------

class ATFExtractor:
    """
    Extract transaction records from Ur III administrative ATF tablets.

    ATF line-type conventions observed here:
      &Pxxxxxx = ...      tablet CDLI ID and name
      @tablet / @obverse / @reverse / @edge / @column   structural markers
      N. [content]        numbered content lines (N may have suffix a-z, !, ?, *)
      $ ...               editorial remark (skipped)
      # ...               note / transliteration (skipped)

    Issuer/recipient heuristics (Ur III Umma administrative practice):
      Issuer:     content line ending with " ki" or " ki2"
                  (Sumerian ablative postposition, "disbursed from X")
                  Guard: the sequence }{ki} is a place-name determinative, not ablative.
      Recipient:  content line containing "šu ba-ti" ("received") — name precedes marker.
                  Also handles multi-line case where name is on the preceding line and
                  "šu ba-ti" appears alone on the next.
                  Dative + ba-an-šum2 pattern also captured.

    Quantity conversion (approximate, for network edge weights):
      1 gur = 300 sila3 | 1 barig = 60 sila3 | 1 ban2 = 10 sila3
    """

    # Strip leading line numbers like "1.", "2a.", "3!.", "4?."
    _RE_LINENUM = re.compile(r"^\d+[a-z]?[!?*]?\.\s*")

    # Metrological quantities
    # CDLI notation: 5(barig) 3(ban2) 2(sila3)
    _RE_QTY_CDLI  = re.compile(r"(\d+)\((\w+)\)")
    # Simple notation: 5 gur / 30 sila3
    _RE_QTY_PLAIN = re.compile(
        r"(\d+(?:\.\d+)?)\s+(gur|barig|ban2|sila3?|gin2|ma-na)", re.I
    )

    # Commodities
    _RE_BARLEY = re.compile(r"\bše\b|she\b|\bbarley\b",  re.I)
    _RE_EMMER  = re.compile(r"\bziz2\b|\bemmer\b",        re.I)
    _RE_DATES  = re.compile(r"\bzu2-lum\b|\bdates?\b",    re.I)
    _RE_FLOUR  = re.compile(r"\bzig3\b|\bflour\b",        re.I)

    # Issuer: line ends with " ki" or " ki2" (ablative)
    _RE_KI_ABL = re.compile(r"^(.*?)\s+ki(?:2)?\s*(?:#.*)?$")
    # Guard: reject if ki immediately follows closing brace (place determinative)
    _RE_KI_DET = re.compile(r"\}\s*ki(?:2)?\s*(?:#.*)?$")

    # Recipient: "NAME šu ba-ti" on same line
    _RE_SHU_BATI  = re.compile(r"^(.*?)\s+šu\s+ba-ti(?:\s+\S+)?\s*(?:#.*)?$")
    # Standalone šu ba-ti / šu ba-an-ti line
    _RE_SHU_ALONE = re.compile(r"^šu\s+ba-(?:an-)?ti\s*(?:#.*)?$")
    # i3-dab5 ("took in custody / received") — high-frequency Umma receipt verb
    _RE_I3_DAB5       = re.compile(r"^(.*?)\s+i3-dab5\s*(?:#.*)?$")
    _RE_I3_DAB5_ALONE = re.compile(r"^i3-dab5\s*(?:#.*)?$")
    # Dative postposition: name ends in -ra
    _RE_DATIVE_RA = re.compile(r"^(.+?)-ra\s*(?:#.*)?$")
    # "was given": ba-an-šum2 / ba-an-šum
    _RE_BA_AN_SUM = re.compile(r"\bba-an-šum2?\b")

    # Date: month line  "iti [month]" optionally followed by "u4 N(-kam)"
    _RE_ITI = re.compile(
        r"^(?:\d+[a-z]?[!?*]?\.\s*)?iti\s+(\S+(?:\s+\S+)*?)"
        r"(?:\s+u4[-\s](\d+)(?:-kam)?)?\s*(?:#.*)?$",
        re.I,
    )
    # Year name line: "mu ..."
    _RE_MU = re.compile(
        r"^(?:\d+[a-z]?[!?*]?\.\s*)?mu\s+(.+?)(?:\s*#.*)?$", re.I
    )
    # Standalone day: "u4 N(-kam)"
    _RE_U4 = re.compile(r"\bu4[-\s](\d+)(?:-kam)?\b")

    # Section boundary: šu-nigin2 / šunigin (totalling line)
    _RE_ŠUNIGIN = re.compile(r"^\d+[a-z]?[!?*]?\.\s*šu-nigin2?\b")

    # ---------------------------------------------------------------------------

    def __init__(self, default_king: Optional[str] = None) -> None:
        """
        Parameters
        ----------
        default_king : str, optional
            Canonical king name assumed when year names don't contain an
            explicit royal name token.  Useful when parsing a corpus known
            to fall within a single reign, e.g. ``"Šulgi"`` for the core
            Umma archive.
        """
        self._default_king = default_king

    def _strip_linenum(self, line: str) -> str:
        return self._RE_LINENUM.sub("", line).strip()

    @staticmethod
    def _is_content(line: str) -> bool:
        s = line.strip()
        return bool(s) and s[0].isdigit()

    # --- quantity -----------------------------------------------------------

    def extract_quantity(self, line: str) -> Tuple[Optional[float], Optional[str]]:
        """
        Parse quantity from a line; return (value_in_sila3, primary_unit).
        CDLI metrological tokens are summed and converted to sila3.
        """
        cdli = self._RE_QTY_CDLI.findall(line)
        if cdli:
            total = 0.0
            first_unit = cdli[0][1].lower()
            conversions = {"gur": 300.0, "barig": 60.0, "ban2": 10.0}
            for num_s, unit in cdli:
                total += float(num_s) * conversions.get(unit.lower(), 1.0)
            return total, first_unit

        m = self._RE_QTY_PLAIN.search(line)
        if m:
            return float(m.group(1)), m.group(2).lower()

        return None, None

    # --- commodity ----------------------------------------------------------

    def _detect_commodity(self, line: str) -> Optional[str]:
        if self._RE_BARLEY.search(line): return "barley"
        if self._RE_EMMER.search(line):  return "emmer"
        if self._RE_DATES.search(line):  return "dates"
        if self._RE_FLOUR.search(line):  return "flour"
        return None

    # --- issuer / recipient -------------------------------------------------

    def _extract_issuer(self, clean: str) -> Optional[str]:
        """Return name from 'NAME ki' pattern, or None."""
        if self._RE_KI_DET.search(clean):
            return None  # {ki} is a place-name determinative, not ablative
        m = self._RE_KI_ABL.match(clean)
        if m:
            candidate = m.group(1).strip()
            if len(candidate) >= 2 and not candidate.startswith(("$", "#")):
                return candidate
        return None

    def _extract_recipient_inline(self, clean: str) -> Optional[str]:
        """
        Return name from same-line receipt formulas:
          - 'NAME šu ba-ti'  (received)
          - 'NAME i3-dab5'   (took in custody)
        """
        for pattern in (self._RE_SHU_BATI, self._RE_I3_DAB5):
            m = pattern.match(clean)
            if m:
                r = m.group(1).strip()
                r = re.sub(r"-ra$", "", r)  # strip trailing dative
                return r if len(r) >= 2 else None
        return None

    def _is_standalone_receipt(self, clean: str) -> bool:
        """True if the line is a bare receipt verb with no preceding name."""
        return bool(
            self._RE_SHU_ALONE.match(clean) or
            self._RE_I3_DAB5_ALONE.match(clean)
        )

    # --- date parsing -------------------------------------------------------

    def _resolve_king_year(self, year_str: str, date: "UrIIIDate") -> None:
        """
        Identify king and regnal year from a year-name string; mutates date.

        Pass 1: look for a king-name token inside the year string (full name).
        Pass 2: if no king was found but self._default_king is set, use it and
                try to match year fragments against that king's fragment dict.
        """
        lower = year_str.lower()

        # "Year After" marker: if present, only fragment sets that explicitly
        # require it are eligible — prevents base-year misattribution where
        # "mu ús2-sa ki-maški{ki} hu-ur5-ti{ki}" would otherwise match
        # Šulgi 45 (whose fragments are a subset of the year-after formula).
        has_usssa = "ús2-sa" in lower

        def _match_year(frags: Dict[int, List[str]]) -> Optional[int]:
            for yr_num, fragments in frags.items():
                frags_lower = [f.lower() for f in fragments]
                if has_usssa and not any("ús2-sa" in f for f in frags_lower):
                    continue  # skip base-year entries when year-after marker present
                if all(f in lower for f in frags_lower):
                    return yr_num
            return None

        # Pass 1: explicit king name in year string
        for key, (canonical, frags) in KING_YEAR_MAP.items():
            if key in lower:
                date.king = canonical
                date.year_number = _match_year(frags)
                return

        # Pass 2: assumed king from corpus context
        if self._default_king:
            date.king = self._default_king
            for key, (canonical, frags) in KING_YEAR_MAP.items():
                if canonical != self._default_king:
                    continue
                date.year_number = _match_year(frags)
                return

    def _parse_date(self, lines: List[str]) -> Tuple[Optional["UrIIIDate"], Optional[str]]:
        """Scan lines for date information; return (UrIIIDate, raw_mu_string)."""
        date = UrIIIDate()
        raw_mu: Optional[str] = None

        for line in lines:
            clean = normalize_atf(self._strip_linenum(line.strip()))

            m = self._RE_ITI.match(clean)
            if m:
                date.month = m.group(1).strip()
                if m.group(2):
                    date.day = int(m.group(2))

            m_day = self._RE_U4.search(clean)
            if m_day and date.day is None and not self._RE_ITI.match(clean):
                date.day = int(m_day.group(1))

            m = self._RE_MU.match(clean)
            if m:
                year_str = m.group(1).strip()
                date.year_name = year_str
                raw_mu = year_str
                self._resolve_king_year(year_str, date)

        if date.king or date.month or date.year_name:
            return date, raw_mu
        return None, None

    # --- section splitting --------------------------------------------------

    def _split_sections(self, lines: List[str]) -> List[List[str]]:
        """
        Divide tablet lines into logical record sections.
        Boundaries are šu-nigin2 totalling lines and @structural markers
        (excluding @tablet which wraps everything).
        """
        sections: List[List[str]] = []
        current: List[str] = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("@") and stripped not in ("@tablet",):
                if current:
                    sections.append(current)
                current = [line]
            elif self._RE_ŠUNIGIN.match(stripped):
                current.append(line)
                sections.append(current)
                current = []
            else:
                current.append(line)

        if current:
            sections.append(current)

        return sections if sections else [lines]

    # --- main extraction ----------------------------------------------------

    def _extract_from_section(
        self, section: List[str], tablet_id: str
    ) -> Optional[Transaction]:
        """
        Extract one Transaction from a section.
        Uses a single pass with look-ahead for multi-line šu ba-ti patterns.
        """
        issuer: Optional[str] = None
        recipient: Optional[str] = None
        quantity: Optional[float] = None
        unit: Optional[str] = None
        commodity: Optional[str] = None
        pending_dative: Optional[str] = None  # name from -ra line waiting for ba-ti/šum2
        first_linenum: Optional[str] = None

        content = [l.strip() for l in section if self._is_content(l.strip())]

        if not content:
            return None

        for i, line in enumerate(content):
            clean = normalize_atf(self._strip_linenum(line))

            if first_linenum is None:
                m = re.match(r"(\d+[a-z]?[!?*]?)\.", line)
                if m:
                    first_linenum = m.group(1)

            # Quantity / commodity — accumulate all allocation lines
            q, u = self.extract_quantity(clean)
            if q is not None:
                quantity = (quantity or 0.0) + q
                if unit is None:
                    unit = u  # record primary unit from first quantity line

            c = self._detect_commodity(clean)
            if c and commodity is None:
                commodity = c

            # Issuer
            iss = self._extract_issuer(clean)
            if iss and issuer is None:
                issuer = iss

            # Recipient: inline "NAME šu ba-ti"
            rec = self._extract_recipient_inline(clean)
            if rec and recipient is None:
                recipient = rec
                pending_dative = None

            # Recipient: standalone receipt verb → previous dative name
            # Covers both "šu ba-ti" and "i3-dab5"
            elif self._is_standalone_receipt(clean) and pending_dative and recipient is None:
                recipient = pending_dative
                pending_dative = None

            # "was given" ba-an-šum2 → previous dative name
            elif self._RE_BA_AN_SUM.search(clean) and pending_dative and recipient is None:
                recipient = pending_dative
                pending_dative = None

            # Track dative -ra name for next line
            m_dat = self._RE_DATIVE_RA.match(clean)
            if m_dat and not rec and not iss:
                cand = m_dat.group(1).strip()
                if len(cand) >= 2:
                    pending_dative = cand
                else:
                    pending_dative = None
            elif not (self._is_standalone_receipt(clean) or self._RE_BA_AN_SUM.search(clean)):
                if not m_dat:
                    pending_dative = None

        # Discard sections with no actionable data
        if quantity is None and issuer is None and recipient is None:
            return None

        date, raw_mu = self._parse_date(section)

        return Transaction(
            tablet_id=tablet_id,
            issuer=issuer,
            recipient=recipient,
            quantity=quantity,
            unit=unit,
            commodity=commodity,
            date=date,
            raw_date=raw_mu,
            line_ref=first_linenum,
        )

    def extract_transactions(
        self, lines: List[str], tablet_id: str
    ) -> List[Transaction]:
        """
        Parse all transactions from a tablet's ATF lines.
        A single tablet may contain multiple consecutive records.
        """
        results: List[Transaction] = []
        try:
            for section in self._split_sections(lines):
                tx = self._extract_from_section(section, tablet_id)
                if tx is not None:
                    results.append(tx)
        except Exception as exc:
            logger.warning("Error parsing tablet %s: %s", tablet_id, exc)
        return results

    def extract_transaction(self, lines: List[str], tablet_id: str) -> Transaction:
        """Single-transaction shim for backward compatibility."""
        txs = self.extract_transactions(lines, tablet_id)
        return txs[0] if txs else Transaction(tablet_id=tablet_id)


# ---------------------------------------------------------------------------
# Normalizer
# ---------------------------------------------------------------------------

class Normalizer:
    """
    Normalize personal names, administrative titles, and institutional
    identifiers found in the Ur III Umma provincial archive.

    Strategy:
      1. Exact lookup in compiled maps (fastest).
      2. Substring scan: check if the input *contains* a known key as a
         whole token — catches compound role strings like "Ur-Nanna šabra".
      3. Fuzzy match via SequenceMatcher against all known keys (fallback).
      4. Return a cleaned version of the original if no match found.
    """

    # Administrative titles and roles
    TITLE_MAP: Dict[str, str] = {
        # Rulers
        "ensi2":        "governor (ensi2)",
        "ensi":         "governor (ensi2)",
        "lugal":        "king",
        "en":           "lord/high-priest",
        # Estate officials
        "šabra":        "estate-administrator (šabra)",
        "agrig":        "steward (agrig)",
        "šuš3":         "livestock-official (šuš3)",
        "nu-banda3":    "inspector (nu-banda3)",
        "nu-banda":     "inspector (nu-banda3)",
        "ugula":        "overseer (ugula)",
        "ugula-e2":     "household-overseer",
        # Scribes and messengers
        "dub-sar":      "scribe (dub-sar)",
        "lu2-kin-gi4-a":"messenger",
        "lu2-kinda":    "barber",
        # Craft workers
        "muhaldim":     "cook (muhaldim)",
        "nar":          "musician",
        "azlag2":       "fuller",
        "simug":        "smith",
        "nagar":        "carpenter",
        "tibira":       "metalworker",
        "zadim":        "gem-cutter",
        "bahar2":       "potter",
        "tug2-du8":     "cloth-fuller",
        "lu2-kikken2":  "miller",
        "aga3-us2":     "soldier/guard",
        "aga-us2":      "soldier/guard",
        # Status
        "géme":         "female-worker",
        "arad2":        "male-worker",
        "arad":         "male-worker",
        "munus":        "woman",
        "nita":         "man",
        "dumu":         "child/son-of",
        "dumu-munus":   "daughter-of",
    }

    # Institutional building/location identifiers in the Umma archive
    INSTITUTION_MAP: Dict[str, str] = {
        "e2-muhaldim":   "kitchen",
        "é-muhaldim":    "kitchen",
        "e2-uz-ga":      "sealed-storehouse",
        "é-uz-ga":       "sealed-storehouse",
        "e2-kišib-ba":   "sealed-goods-office",
        "e2-duru5":      "village-household",
        "é-duru5":       "village-household",
        "e2":            "é (household)",
        "é":             "é (household)",
        # Major Umma archive institutions
        "gar-ša-an-na{ki}": "Karshana",
        "gar-ša-an-na":     "Karshana",
        "umma{ki}":         "Umma",
        "umma":             "Umma",
        "girsu{ki}":        "Girsu",
        "girsu":            "Girsu",
        "uri5{ki}":         "Ur",
        "nibru{ki}":        "Nippur",
        "nibru":            "Nippur",
        "isin{ki}":         "Isin",
        "a-dam-dun{ki}":    "Adadun",
    }

    # Known personal names in the Umma provincial archive.
    # Keys are lowercase ATF transliteration variants; values are display forms.
    # Extend with names from your specific corpus subset.
    NAME_MAP: Dict[str, str] = {
        # Governors and senior officials
        "ur-{d}li9-si4":   "Ur-Lisi",
        "ur-li9-si4":      "Ur-Lisi",
        "ur-lisi":         "Ur-Lisi",
        "arad-{d}nanna":   "Arad-Nanna",
        "arad-nanna":      "Arad-Nanna",
        "lugal-ezen":      "Lugal-ezen",
        # Common personal names
        "ur-{d}nanna":     "Ur-Nanna",
        "ur-nanna":        "Ur-Nanna",
        "ur-{d}suen":      "Ur-Suen",
        "ur-suen":         "Ur-Suen",
        "ur-{d}utu":       "Ur-Utu",
        "ur-utu":          "Ur-Utu",
        "ur-{d}dumu-zi":   "Ur-Dumuzi",
        "ur-dumu-zi":      "Ur-Dumuzi",
        "a-a-kal-la":      "Ayakalla",
        "a-a-kala":        "Ayakalla",
        "lu2-{d}nanna":    "Lu-Nanna",
        "lu2-nanna":       "Lu-Nanna",
        "lu2-{d}dumu-zi":  "Lu-Dumuzi",
        "lu2-dumu-zi":     "Lu-Dumuzi",
        "i3-li2-bi-la-ni": "Ili-bilani",
        "nam-ha-ni":       "Namhani",
        "šeš-kal-la":      "Shesh-kalla",
        "na-lu5":          "Nalu",
        "da-da":           "Dada",
        "a2-zi-da":        "Azida",
        "ur-mes":          "Ur-Mes",
        "ur-{d}mes":       "Ur-Mes",
        "šu-{d}suen":      "Shu-Suen (person)",
        "ab-ba-sa6-ga":    "Abba-saga",
        "lugal-sa6-ga":    "Lugal-saga",
    }

    def __init__(self, fuzzy_threshold: float = 0.82) -> None:
        self.fuzzy_threshold = fuzzy_threshold
        # Flat lookup for exact / fuzzy matching (titles + institutions + names)
        self._all: Dict[str, str] = {}
        self._all.update(self.TITLE_MAP)
        self._all.update(self.INSTITUTION_MAP)
        self._all.update(self.NAME_MAP)

    # --- internal helpers ---------------------------------------------------

    def _clean(self, name: str) -> str:
        """Lowercase, normalize ASCII transliteration, remove damage markers."""
        name = normalize_atf(name).lower().strip()
        name = re.sub(r"[!?*]", "", name)
        name = re.sub(r"\[.*?\]", "", name)
        name = re.sub(r"\s+", " ", name).strip()
        return name

    def _fuzzy_match(self, name: str) -> Optional[str]:
        """
        Fuzzy match within each semantic category separately, in priority order:
        personal names → institutions → titles.  Prevents cross-category
        contamination (e.g. a personal name matching a generic title).
        """
        for category in (self.NAME_MAP, self.INSTITUTION_MAP, self.TITLE_MAP):
            best_ratio = 0.0
            best: Optional[str] = None
            for key, canonical in category.items():
                ratio = SequenceMatcher(None, name, key).ratio()
                if ratio > best_ratio:
                    best_ratio, best = ratio, canonical
            if best_ratio >= self.fuzzy_threshold:
                return best
        return None

    # --- public interface ---------------------------------------------------

    def normalize_name(self, name: Optional[str]) -> Optional[str]:
        """
        Normalize a name or title string to a canonical form.
        Returns None for None / empty input.
        """
        if not name:
            return name

        cleaned = self._clean(name)

        # 1. Exact lookup
        if cleaned in self._all:
            return self._all[cleaned]

        # 2. Whole-token substring scan (handles "Ur-Nanna šabra"-style strings)
        #    Prefer longest matching key to avoid short false positives.
        best_key_len = 0
        best_canon: Optional[str] = None
        for key, canonical in self._all.items():
            if key in cleaned and len(key) > best_key_len:
                best_key_len, best_canon = len(key), canonical
        if best_canon and best_key_len >= 3:
            return best_canon

        # 3. Fuzzy match
        fuzzy = self._fuzzy_match(cleaned)
        if fuzzy:
            return fuzzy

        # 4. Return cleaned original
        return cleaned

    def normalize_transaction(self, tx: Transaction) -> Transaction:
        tx.issuer    = self.normalize_name(tx.issuer)
        tx.recipient = self.normalize_name(tx.recipient)
        return tx


# ---------------------------------------------------------------------------
# Network Builder
# ---------------------------------------------------------------------------

class NetworkBuilder:
    """Build a directed weighted NetworkX graph from a list of transactions."""

    def __init__(self) -> None:
        self.graph = nx.DiGraph()

    def add_transaction(self, tx: Transaction) -> None:
        if not tx.issuer or not tx.recipient:
            return
        weight = tx.quantity if tx.quantity else 1.0
        if self.graph.has_edge(tx.issuer, tx.recipient):
            self.graph[tx.issuer][tx.recipient]["weight"] += weight
            self.graph[tx.issuer][tx.recipient]["count"]  += 1
        else:
            self.graph.add_edge(
                tx.issuer,
                tx.recipient,
                weight=weight,
                count=1,
            )

    def build(self, transactions: List[Transaction]) -> nx.DiGraph:
        for tx in transactions:
            self.add_transaction(tx)
        return self.graph


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_metrics(G: nx.DiGraph) -> Dict:
    """Return standard network metrics for a directed graph."""
    return {
        "degree_centrality":      nx.degree_centrality(G),
        "in_degree_centrality":   nx.in_degree_centrality(G),
        "out_degree_centrality":  nx.out_degree_centrality(G),
        "betweenness_centrality": nx.betweenness_centrality(G, weight="weight"),
        "density":                nx.density(G),
        "num_weakly_connected_components": nx.number_weakly_connected_components(G),
    }


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_to_gexf(G: nx.DiGraph, filepath: str) -> None:
    """
    Export the transaction network to GEXF format for Gephi.
    Edge attributes 'weight' and 'count' are preserved.
    """
    try:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        nx.write_gexf(G, filepath)
        logger.info("Network exported to GEXF: %s", filepath)
    except OSError as exc:
        logger.error("Failed to write GEXF to %s: %s", filepath, exc)


def export_transactions_csv(transactions: List[Transaction], filepath: str) -> None:
    """Export the raw transaction list to CSV for further analysis."""
    if not transactions:
        logger.warning("No transactions to export.")
        return

    fieldnames = [
        "tablet_id", "issuer", "recipient",
        "quantity", "unit", "commodity",
        "date_king", "date_year_number", "date_year_name",
        "date_month", "date_day", "raw_date", "line_ref",
    ]

    def _row(tx: Transaction) -> Dict:
        d = tx.date
        return {
            "tablet_id":        tx.tablet_id,
            "issuer":           tx.issuer or "",
            "recipient":        tx.recipient or "",
            "quantity":         tx.quantity if tx.quantity is not None else "",
            "unit":             tx.unit or "",
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
        logger.info("Transactions exported to CSV: %s (%d rows)", filepath, len(transactions))
    except OSError as exc:
        logger.error("Failed to write CSV to %s: %s", filepath, exc)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    data_path   = "data/raw_atf/"
    output_dir  = "output/"

    corpus = load_corpus(data_path)
    if not corpus:
        logger.error("No ATF files loaded. Check that %s contains *.atf files.", data_path)
        return

    # Pass default_king for Umma archive tablets whose abbreviated year names
    # do not include an explicit royal name token (common in Šulgi-period records).
    extractor  = ATFExtractor(default_king="Šulgi")
    normalizer = Normalizer()

    all_transactions: List[Transaction] = []
    barley_transactions: List[Transaction] = []

    for tablet_id, lines in corpus.items():
        txs = extractor.extract_transactions(lines, tablet_id)
        for tx in txs:
            tx = normalizer.normalize_transaction(tx)
            all_transactions.append(tx)
            if tx.commodity == "barley":
                barley_transactions.append(tx)

    logger.info(
        "Extracted %d total transactions, %d barley.",
        len(all_transactions), len(barley_transactions),
    )

    # Optional: filter to Šulgi years 45-48
    sulgi_slice = [
        tx for tx in barley_transactions
        if tx.date and tx.date.in_range("Šulgi", 45, 48)
    ]
    logger.info("Šulgi years 45-48 barley transactions: %d", len(sulgi_slice))

    # Build network from all barley transactions
    builder = NetworkBuilder()
    G = builder.build(barley_transactions)

    print(f"\nNetwork summary")
    print(f"  Nodes : {G.number_of_nodes()}")
    print(f"  Edges : {G.number_of_edges()}")

    if G.number_of_nodes() > 0:
        metrics = compute_metrics(G)
        print(f"  Density              : {metrics['density']:.4f}")
        print(f"  Weakly conn. comps   : {metrics['num_weakly_connected_components']}")

        print("\nTop 5 by betweenness centrality:")
        bc = sorted(metrics["betweenness_centrality"].items(), key=lambda x: x[1], reverse=True)
        for node, val in bc[:5]:
            print(f"  {node}: {val:.4f}")

        print("\nTop 5 by in-degree centrality (major recipients):")
        idc = sorted(metrics["in_degree_centrality"].items(), key=lambda x: x[1], reverse=True)
        for node, val in idc[:5]:
            print(f"  {node}: {val:.4f}")

    # Exports
    os.makedirs(output_dir, exist_ok=True)
    export_to_gexf(G, os.path.join(output_dir, "barley_network.gexf"))
    export_transactions_csv(barley_transactions, os.path.join(output_dir, "transactions.csv"))
    if sulgi_slice:
        export_transactions_csv(
            sulgi_slice,
            os.path.join(output_dir, "transactions_sulgi_45-48.csv"),
        )


if __name__ == "__main__":
    main()
