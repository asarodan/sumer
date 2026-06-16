"""
atf_pipeline.py

Pipeline for parsing Ur III cuneiform administrative tablets (ATF format)
from the CDLI corpus, extracting transactions from the Umma provincial
archive, and modelling them as a directed weighted network.

ATF format docs:  https://oracc.museum.upenn.edu/doc/help/editinginatf/
CDLI year names:  https://cdli.mpiwg-berlin.mpg.de/
BDTNS:            https://bdtns.filol.csic.es/

Encoding note: CDLI bulk exports use ASCII ATF transliteration
  š → sz  (e.g. šu ba-ti → szu ba-ti, šunigin → szunigin)
  ĝ → g (varies)  ú/ū → u2
All regex patterns in this file accept both ASCII ATF and Unicode forms.
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
# line for a match.  Fragments given in ASCII ATF (sz = š, etc.).

_URNAMMA_FRAGS: Dict[int, List[str]] = {
    1:  ["nanna-e2-a"],
    2:  ["ki-en-gi ki-uri"],
    5:  ["bad3 uri5{ki}"],
}

_ŠULGI_FRAGS: Dict[int, List[str]] = {
    1:  ["lugal-uri5{ki}-ma"],
    3:  ["en-{d}inanna"],
    18: ["en-{d}inanna nibru{ki}"],
    44: ["bad3 mar-tu ba-du3"],
    # Years 45-48: check us2-sa (year-after) variants BEFORE plain ki-masz
    # so the more-specific year 46/48 patterns match first.
    # Spellings verified against CDLI corpus: ki-masz{ki}, ha-ar-szi{ki}.
    48: ["us2-sa ha-ar-szi{ki}"],
    47: ["ha-ar-szi{ki}"],
    46: ["us2-sa ki-masz{ki}"],
    45: ["ki-masz{ki}"],
}

_AMARSUEN_FRAGS: Dict[int, List[str]] = {
    1:  ["uri2{ki}-a"],
    2:  ["en-{d}inanna"],
    6:  ["sza-asz-szu{ki}"],
    9:  ["hu-uh2-nu-ri{ki}"],
}

_ŠUSUEN_FRAGS: Dict[int, List[str]] = {
    1:  ["ma2 {d}en-zu"],
    2:  ["szu-{d}suen bad3"],
    3:  ["szu-{d}suen bad3"],
    4:  ["za-ab-sza-li{ki}"],
    5:  ["en {d}nanna"],
}

_IBBISUEN_FRAGS: Dict[int, List[str]] = {
    1:  ["i-bi2-{d}suen lugal"],
    2:  ["ibbi-{d}suen lugal"],
}

# Maps lowercase ATF king-name variant → (canonical display name, year-frag dict)
# Includes both Unicode (š) and ASCII ATF (sz) variants for robustness.
KING_YEAR_MAP: Dict[str, Tuple[str, Dict[int, List[str]]]] = {
    # Ur-Namma
    "ur-namma":        ("Ur-Namma",   _URNAMMA_FRAGS),
    "ur-{d}namma":     ("Ur-Namma",   _URNAMMA_FRAGS),
    # Šulgi – Unicode
    "šul-gi":          ("Šulgi",      _ŠULGI_FRAGS),
    "{d}šul-gi":       ("Šulgi",      _ŠULGI_FRAGS),
    "šulgi":           ("Šulgi",      _ŠULGI_FRAGS),
    "sulgi":           ("Šulgi",      _ŠULGI_FRAGS),
    # Šulgi – ASCII ATF
    "szul-gi":         ("Šulgi",      _ŠULGI_FRAGS),
    "{d}szul-gi":      ("Šulgi",      _ŠULGI_FRAGS),
    # Amar-Suen
    "amar-{d}suen":    ("Amar-Suen",  _AMARSUEN_FRAGS),
    "amar-suen":       ("Amar-Suen",  _AMARSUEN_FRAGS),
    # Šu-Suen – Unicode
    "šu-{d}suen":      ("Šu-Suen",    _ŠUSUEN_FRAGS),
    "šu-suen":         ("Šu-Suen",    _ŠUSUEN_FRAGS),
    # Šu-Suen – ASCII ATF (most common in CDLI exports)
    "szu-{d}suen":     ("Šu-Suen",    _ŠUSUEN_FRAGS),
    "szu-suen":        ("Šu-Suen",    _ŠUSUEN_FRAGS),
    # Ibbi-Suen
    "ibbi-{d}suen":    ("Ibbi-Suen",  _IBBISUEN_FRAGS),
    "ibbi-suen":       ("Ibbi-Suen",  _IBBISUEN_FRAGS),
    "ibi-{d}suen":     ("Ibbi-Suen",  _IBBISUEN_FRAGS),
    "i-bi2-{d}suen":   ("Ibbi-Suen",  _IBBISUEN_FRAGS),
}


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
    agent: Optional[str] = None       # giri3 responsible party
    quantity: Optional[float] = None  # normalised to sila3
    unit: Optional[str] = None        # primary metrological unit as written
    commodity: Optional[str] = None
    date: Optional[UrIIIDate] = None
    raw_date: Optional[str] = None    # verbatim mu-line from tablet
    line_ref: Optional[str] = None    # first content line number


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

# Noise patterns from CDLI web/PDF exports
_RE_EXPORT_NOISE = re.compile(
    r"https?://cdli\.|Page\s+\d+\s+of\s+\d+|^\s*:\s*$",
    re.I,
)
_RE_TABLET_HEADER = re.compile(r"^&(P\d+)\s*=")


def parse_cdli_export(text: str) -> Dict[str, List[str]]:
    """
    Parse a CDLI multi-tablet bulk export (e.g. CDLI search → ATF text or
    a browser/PDF save of https://cdli.earth/search?...&format=atf).

    Strips page headers/footers and splits on &Pxxxxxx tablet markers.
    Returns {cdli_id: [atf_lines]}.
    """
    tablets: Dict[str, List[str]] = {}
    current_id: Optional[str] = None
    current_lines: List[str] = []

    for raw in text.splitlines():
        stripped = raw.strip()

        if not stripped:
            if current_id is not None:
                current_lines.append("")
            continue

        if _RE_EXPORT_NOISE.search(stripped):
            continue

        m = _RE_TABLET_HEADER.match(stripped)
        if m:
            if current_id and current_lines:
                tablets[current_id] = current_lines
            current_id = m.group(1)
            current_lines = [stripped]
        elif current_id is not None:
            current_lines.append(stripped)

    if current_id and current_lines:
        tablets[current_id] = current_lines

    logger.info("Parsed %d tablets from CDLI export text.", len(tablets))
    return tablets


def load_cdli_export_file(filepath: str) -> Dict[str, List[str]]:
    """
    Load and parse a CDLI bulk ATF export text file (single file, many tablets).
    Tries common encodings automatically.
    Returns {cdli_id: [atf_lines]}.
    """
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            with open(filepath, "r", encoding=enc) as fh:
                text = fh.read()
            result = parse_cdli_export(text)
            if result:
                logger.info("Loaded CDLI export: %s (%s encoding, %d tablets)",
                            filepath, enc, len(result))
                return result
        except UnicodeDecodeError:
            continue
        except OSError as exc:
            logger.error("Cannot open %s: %s", filepath, exc)
            return {}
    logger.warning("No working encoding found for %s.", filepath)
    return {}


def load_atf_file(filepath: str) -> List[str]:
    """
    Load a single ATF file, trying multiple encodings.
    Returns list of lines (trailing newlines stripped), or [] on failure.
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

    ATF line-type conventions:
      &Pxxxxxx = ...      tablet CDLI ID and name
      @tablet / @obverse / @reverse / @edge / @column / @seal   structural markers
      N. [content]        numbered content lines (N may have suffix a-z, ', !, ?, *)
      $ ...               editorial remark (skipped for extraction)
      # ...               note / translation (skipped)

    Issuer/recipient heuristics for the Umma archive:

      Issuer:  Line beginning with "ki NAME-ta" (Sumerian ablative:
               "from the place of NAME"). The leading ki# variant (with
               damage marker) is also handled. The trailing -ta suffix
               is stripped when extracting the name.

      Recipient: "NAME szu/šu ba-ti" on the same line (inline form), OR
               NAME alone on one line followed by standalone "szu ba-ti"
               on the next (multi-line form). The dative -ra ending is
               also tracked for "ba-an-szum2" (was given) constructions.

      Agent:   "giri3 NAME" — the responsible official who supervised the
               transaction (not issuer or recipient but important for the
               administrative network).

    Quantity conversion (approximate, for network edge weights):
      1 gur = 300 sila3 | 1 barig = 60 sila3 | 1 ban2 = 10 sila3
      Fractional notations like 1/2(disz) and 2/3(disz) are handled.
    """

    # Strip leading line numbers: 1. 2a. 3!. 4?. 5'. 6'a.
    _RE_LINENUM = re.compile(r"^\d+[a-z]?[!?*'ʼ]?\.\s*(?:[a-z]\.\s*)?")

    # Metrological quantities – CDLI notation: 5(barig) 3(ban2) 2(sila3)
    # Handles integer and fractional coefficients: 1/2(disz) 2/3(disz) etc.
    _RE_QTY_CDLI  = re.compile(r"(\d+(?:/\d+)?)\((\w+[2']?)\)")
    # Simple prose notation: 5 gur / 30 sila3
    _RE_QTY_PLAIN = re.compile(
        r"(\d+(?:\.\d+)?)\s+(gur|barig|ban2|sila3?|gin2|ma-na)", re.I
    )

    # Commodities (ASCII ATF corpus)
    _RE_BARLEY  = re.compile(r"\bsze(?!-gesz)\b|\bše\b|\bbarley\b|\bsze-ba\b", re.I)
    _RE_EMMER   = re.compile(r"\bziz2\b|\bemmer\b", re.I)
    _RE_WHEAT   = re.compile(r"\bgig\b|\bwheat\b", re.I)
    _RE_DATES   = re.compile(r"\bzu2-lum\b|\bdates?\b", re.I)
    _RE_FLOUR   = re.compile(r"\bzi3\b|\bzi3-gu\b|\bdabin\b|\bflour\b", re.I)
    _RE_BEER    = re.compile(r"\bkasz\b|\bdida\b|\bbeer\b", re.I)
    _RE_OIL     = re.compile(r"\bi3-gesz\b|\bsze-gesz-i3\b|\boil\b", re.I)
    _RE_SILVER  = re.compile(r"\bku3-babbar\b|\bsilver\b", re.I)

    # Issuer pattern A (Unicode corpus): NAME ki or NAME ki2 at end of line
    _RE_KI_ABL  = re.compile(r"^(.*?)\s+ki(?:2)?\s*(?:#.*)?$")
    # Guard: {ki} is place-name determinative, not ablative
    _RE_KI_DET  = re.compile(r"\}\s*ki(?:2)?\s*(?:#.*)?$")
    # Issuer pattern B (ASCII ATF corpus): ki NAME-ta at start of line
    # Handles damage marker: ki# NAME-ta
    _RE_KI_TA   = re.compile(r"^ki#?\s+(.+?)-ta(?:\s|$)(?:#.*)?$")

    # Recipient: "NAME szu/šu ba-ti" on same line (ASCII and Unicode)
    _RE_SHU_BATI  = re.compile(
        r"^(.*?)\s+s[zž]u#?\s+ba-(?:an-)?ti(?:\s+\S+)?\s*(?:#.*)?$"
    )
    # Standalone szu/šu ba-ti / ba-ab-ti line
    _RE_SHU_ALONE = re.compile(
        r"^s[zž]u#?\s+ba-(?:ab-|an-)?ti\s*(?:#.*)?$"
    )
    # Dative postposition: name ends in -ra (for ba-an-szum2 constructions)
    _RE_DATIVE_RA = re.compile(r"^(.+?)-ra\s*(?:#.*)?$")
    # "was given": ba-an-szum2 / ba-an-šum2
    _RE_BA_AN_SUM = re.compile(r"\bba-an-s[zž]um2?\b")

    # Responsible party: giri3 NAME [title]
    _RE_GIRI3 = re.compile(r"^giri3#?\s+(.+?)(?:\s+(?:#.*)?)?$")

    # Date: month line "iti [month]" optionally followed by "u4 N(-kam)"
    _RE_ITI = re.compile(
        r"^(?:\d+[a-z]?[!?*'ʼ]?\.\s*)?iti\s+(\S+(?:\s+\S+)*?)"
        r"(?:\s+u4[-\s](\d+)(?:-kam)?)?\s*(?:#.*)?$",
        re.I,
    )
    # Year name line: "mu ..."
    _RE_MU = re.compile(
        r"^(?:\d+[a-z]?[!?*'ʼ]?\.\s*)?mu\s+(.+?)(?:\s*#.*)?$", re.I
    )
    # Standalone day: "u4 N(-kam)"
    _RE_U4 = re.compile(r"\bu4[-\s](\d+)(?:-kam)?\b")

    # Section boundary: szunigin / šunigin / szu-nigin2 (grand total line)
    _RE_SZUNIGIN = re.compile(
        r"^\d+[a-z]?[!?*'ʼ]?\.\s*(?:szunigin|šunigin|szu-nigin2?|šu-nigin2?)\b",
        re.I,
    )

    # Lines that are clearly not personal names (skip for recipient tracking)
    _RE_NOT_NAME = re.compile(
        r"^\d|^[@$#]|^(?:iti|mu|giri3|ki|ugula|kiszib3|szunigin|szunigin"
        r"|sze-ba|sza3-bi-ta|zi-ga|la2-ia3|nig2-ka9|sag-nig2)\b",
        re.I,
    )

    # ---------------------------------------------------------------------------

    def __init__(self, default_king: Optional[str] = None) -> None:
        """
        Parameters
        ----------
        default_king : str, optional
            Canonical king name assumed when year names lack an explicit royal
            name token.  Useful for corpora confined to a single reign, e.g.
            ``"Šulgi"`` for the core Umma barley archive.
        """
        self._default_king = default_king

    def _strip_linenum(self, line: str) -> str:
        return self._RE_LINENUM.sub("", line).strip()

    @staticmethod
    def _is_content(line: str) -> bool:
        s = line.strip()
        return bool(s) and s[0].isdigit()

    @staticmethod
    def _clean_atf_name(name: str) -> str:
        """Strip damage markers and trailing grammatical suffixes from a name."""
        name = re.sub(r"[!?*#]", "", name)
        name = re.sub(r"\[.*?\]", "", name)
        name = re.sub(r"-ta\s*$", "", name)   # ablative suffix
        name = re.sub(r"\s+", " ", name).strip()
        return name

    def _looks_like_name(self, clean: str) -> bool:
        """Heuristic: does this look like a standalone personal name line?"""
        if self._RE_NOT_NAME.match(clean):
            return False
        # Must not be a formula or commodity-only line
        if re.search(r"\b(?:gur|barig|ban2|sila3|gin2)\b", clean):
            return False
        if len(clean) < 2 or len(clean) > 60:
            return False
        return True

    # --- quantity -----------------------------------------------------------

    # Sumerian sexagesimal grain capacity system (all values in sila3):
    #   1 gur = 5 barig = 300 sila3
    #   1 barig = 6 ban2 = 60 sila3
    #   1 ban2 = 10 sila3
    #   asz = gur (the base count of gur containers)
    #   gesz2 = 60×gur, gesz'u = 600×gur, szar2 = 3600×gur
    _GRAIN_CONVERSIONS: Dict[str, float] = {
        "szar2":  3600.0 * 300.0,
        "gesz'u":  600.0 * 300.0,
        "gesz2":    60.0 * 300.0,
        "asz":         300.0,      # 1 gur (the asz sign is the gur container)
        "gur":         300.0,
        "barig":        60.0,
        "ban2":         10.0,
        "disz":          1.0,
        "sila3":         1.0,
        "sila":          1.0,
    }
    # Units that definitively indicate a grain/capacity measure
    _GRAIN_INDICATORS = frozenset({"gur", "barig", "ban2", "sila3", "sila", "asz"})

    def extract_quantity(self, line: str) -> Tuple[Optional[float], Optional[str]]:
        """
        Parse a Sumerian grain quantity from a line; return (value_in_sila3, primary_unit).

        Handles the full sexagesimal capacity system (szar2, gesz'u, gesz2, asz/gur,
        barig, ban2, sila3) including fractional coefficients (1/2(disz) etc.).
        Non-grain lines (worker-days, animals, area) are skipped — they're identified
        by the absence of any grain indicator unit in the token sequence.
        """
        cdli = self._RE_QTY_CDLI.findall(line)
        if cdli:
            units_found = {u.lower() for _, u in cdli}
            # Only process as grain if at least one definitive grain unit is present
            if not (units_found & self._GRAIN_INDICATORS):
                return None, None

            total = 0.0
            first_unit = cdli[0][1].lower()
            for num_s, unit in cdli:
                u = unit.lower()
                factor = self._GRAIN_CONVERSIONS.get(u)
                if factor is None:
                    continue  # skip non-grain tokens (u, gurusz, udu, iku, etc.)
                if "/" in num_s:
                    n, d = num_s.split("/", 1)
                    coeff = float(n) / float(d)
                else:
                    coeff = float(num_s)
                total += coeff * factor
            return (total, first_unit) if total > 0 else (None, None)

        m = self._RE_QTY_PLAIN.search(line)
        if m:
            return float(m.group(1)), m.group(2).lower()

        return None, None

    # --- commodity ----------------------------------------------------------

    def _detect_commodity(self, line: str) -> Optional[str]:
        if self._RE_BARLEY.search(line):  return "barley"
        if self._RE_EMMER.search(line):   return "emmer"
        if self._RE_WHEAT.search(line):   return "wheat"
        if self._RE_DATES.search(line):   return "dates"
        if self._RE_FLOUR.search(line):   return "flour"
        if self._RE_BEER.search(line):    return "beer"
        if self._RE_OIL.search(line):     return "oil"
        if self._RE_SILVER.search(line):  return "silver"
        return None

    # --- issuer / recipient / agent -----------------------------------------

    def _extract_issuer(self, clean: str) -> Optional[str]:
        """
        Return issuer name from either pattern:
          A) "ki NAME-ta" at line start  (standard in CDLI ASCII ATF)
          B) "NAME ki" at line end       (older Unicode corpus convention)
        """
        # Pattern A: ki NAME-ta
        m = self._RE_KI_TA.match(clean)
        if m:
            cand = self._clean_atf_name(m.group(1))
            if len(cand) >= 2 and not cand.startswith(("$", "#")):
                return cand

        # Pattern B: NAME ki (reject if {ki} determinative)
        if not self._RE_KI_DET.search(clean):
            m2 = self._RE_KI_ABL.match(clean)
            if m2:
                cand = self._clean_atf_name(m2.group(1))
                if len(cand) >= 2 and not cand.startswith(("$", "#")):
                    return cand

        return None

    def _extract_recipient_inline(self, clean: str) -> Optional[str]:
        """Return name from 'NAME szu ba-ti' on the same line."""
        m = self._RE_SHU_BATI.match(clean)
        if m:
            r = self._clean_atf_name(m.group(1))
            r = re.sub(r"-ra$", "", r).strip()
            return r if len(r) >= 2 else None
        return None

    def _extract_agent(self, clean: str) -> Optional[str]:
        """Return name from 'giri3 NAME' (responsible official)."""
        m = self._RE_GIRI3.match(clean)
        if m:
            cand = self._clean_atf_name(m.group(1).strip())
            # Strip trailing title words
            cand = re.sub(
                r"\s+(?:dub-sar|sukkal|szagina|ensi2|szabra|ugula|nu-banda3"
                r"|dumu\s+lugal|lu2\s+kin-gi4-a)\s*$", "", cand
            ).strip()
            return cand if len(cand) >= 2 else None
        return None

    # --- date parsing -------------------------------------------------------

    def _resolve_king_year(self, year_str: str, date: "UrIIIDate") -> None:
        """
        Identify king and regnal year from a year-name string; mutates date.

        Pass 1: look for a king-name token inside the year string.
        Pass 2: if no king found but self._default_king is set, use it and
                try fragment matching against that king's fragment dict.
        """
        lower = year_str.lower()

        for key, (canonical, frags) in KING_YEAR_MAP.items():
            if key in lower:
                date.king = canonical
                for yr_num, fragments in frags.items():
                    if all(frag.lower() in lower for frag in fragments):
                        date.year_number = yr_num
                        break
                return

        if self._default_king:
            date.king = self._default_king
            for key, (canonical, frags) in KING_YEAR_MAP.items():
                if canonical != self._default_king:
                    continue
                for yr_num, fragments in frags.items():
                    if all(frag.lower() in lower for frag in fragments):
                        date.year_number = yr_num
                        return

    def _parse_date(
        self, lines: List[str]
    ) -> Tuple[Optional["UrIIIDate"], Optional[str]]:
        """Scan lines for date information; return (UrIIIDate, raw_mu_string)."""
        date = UrIIIDate()
        raw_mu: Optional[str] = None

        for line in lines:
            clean = self._strip_linenum(line.strip())

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
        Boundaries are szunigin/šunigin total lines only — structural @markers
        are NOT used as boundaries because a single transaction routinely spans
        obverse, reverse, and multiple columns.
        """
        sections: List[List[str]] = []
        current: List[str] = []

        for line in lines:
            stripped = line.strip()
            if self._RE_SZUNIGIN.match(stripped):
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
        Uses a single pass with look-ahead / look-behind for multi-line
        szu ba-ti and dative patterns.
        """
        issuer:    Optional[str] = None
        recipient: Optional[str] = None
        agent:     Optional[str] = None
        quantity:  Optional[float] = None
        unit:      Optional[str] = None
        commodity: Optional[str] = None
        pending_dative: Optional[str] = None
        prev_name:      Optional[str] = None   # last standalone name-like line
        first_linenum:  Optional[str] = None

        content = [l.strip() for l in section if self._is_content(l.strip())]

        if not content:
            return None

        for line in content:
            clean = self._strip_linenum(line)

            if first_linenum is None:
                m = re.match(r"(\d+[a-z]?[!?*'ʼ]?)\.", line)
                if m:
                    first_linenum = m.group(1)

            # Quantity / commodity
            q, u = self.extract_quantity(clean)
            if q is not None and quantity is None:
                quantity, unit = q, u

            c = self._detect_commodity(clean)
            if c and commodity is None:
                commodity = c

            # Issuer
            iss = self._extract_issuer(clean)
            if iss and issuer is None:
                issuer = iss
                prev_name = None
                continue

            # Agent (giri3)
            ag = self._extract_agent(clean)
            if ag and agent is None:
                agent = ag

            # Recipient: inline "NAME szu ba-ti"
            rec = self._extract_recipient_inline(clean)
            if rec and recipient is None:
                recipient = rec
                prev_name = None
                pending_dative = None
                continue

            # Recipient: standalone "szu ba-ti" → use prev_name or pending_dative
            if self._RE_SHU_ALONE.match(clean) and recipient is None:
                if prev_name:
                    recipient = prev_name
                elif pending_dative:
                    recipient = pending_dative
                prev_name = None
                pending_dative = None
                continue

            # "was given": ba-an-szum2 → use pending_dative
            if self._RE_BA_AN_SUM.search(clean) and recipient is None:
                if pending_dative:
                    recipient = pending_dative
                    pending_dative = None
                continue

            # Track dative -ra name for ba-an-szum2 look-ahead
            m_dat = self._RE_DATIVE_RA.match(clean)
            if m_dat and not rec and not iss:
                cand = self._clean_atf_name(m_dat.group(1).strip())
                if len(cand) >= 2:
                    pending_dative = cand

            # Track previous name-like line for standalone szu ba-ti look-ahead
            if self._looks_like_name(clean):
                prev_name = self._clean_atf_name(clean)
            elif not (self._RE_SHU_ALONE.match(clean)
                      or self._RE_BA_AN_SUM.search(clean)
                      or m_dat):
                prev_name = None

        if quantity is None and issuer is None and recipient is None:
            return None

        date, raw_mu = self._parse_date(section)

        return Transaction(
            tablet_id=tablet_id,
            issuer=issuer,
            recipient=recipient,
            agent=agent,
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
        """Parse all transactions from a tablet's ATF lines."""
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

    TITLE_MAP: Dict[str, str] = {
        # Rulers
        "ensi2":         "governor (ensi2)",
        "ensi":          "governor (ensi2)",
        "lugal":         "king",
        "en":            "lord/high-priest",
        # Estate officials
        "szabra":        "estate-administrator (šabra)",
        "šabra":         "estate-administrator (šabra)",
        "agrig":         "steward (agrig)",
        "szusz3":        "livestock-official (šuš3)",
        "šuš3":          "livestock-official (šuš3)",
        "nu-banda3":     "inspector (nu-banda3)",
        "nu-banda":      "inspector (nu-banda3)",
        "ugula":         "overseer (ugula)",
        "ugula-e2":      "household-overseer",
        "szagina":       "general (šagina)",
        # Scribes and messengers
        "dub-sar":       "scribe (dub-sar)",
        "sukkal":        "secretary (sukkal)",
        "lu2-kin-gi4-a": "messenger",
        "lu2-kinda":     "barber",
        # Agricultural
        "engar":         "farmer/field-manager (engar)",
        "aszgab":        "leather-worker",
        # Craft workers
        "muhaldim":      "cook (muhaldim)",
        "nar":           "musician",
        "azlag2":        "fuller",
        "simug":         "smith",
        "nagar":         "carpenter",
        "tibira":        "metalworker",
        "zadim":         "gem-cutter",
        "bahar2":        "potter",
        "tug2-du8":      "cloth-fuller",
        "lu2-kikken2":   "miller",
        "aga3-us2":      "soldier/guard",
        "aga-us2":       "soldier/guard",
        # Labor status
        "geme2":         "female-worker",
        "arad2":         "male-worker",
        "arad":          "male-worker",
        "munus":         "woman",
        "nita":          "man",
        "dumu":          "child/son-of",
        "dumu-munus":    "daughter-of",
        "gurusz":        "male-laborer",
    }

    INSTITUTION_MAP: Dict[str, str] = {
        "e2-muhaldim":       "kitchen",
        "é-muhaldim":        "kitchen",
        "e2-uz-ga":          "sealed-storehouse",
        "é-uz-ga":           "sealed-storehouse",
        "e2-kiszib-ba":      "sealed-goods-office",
        "e2-duru5":          "village-household",
        "é-duru5":           "village-household",
        "e2-kikken":         "mill-house",
        "e2":                "é (household)",
        "é":                 "é (household)",
        # Umma archive geographic nodes
        "gar-sza-an-na{ki}": "Karshana",
        "gar-sza-an-na":     "Karshana",
        "umma{ki}":          "Umma",
        "umma":              "Umma",
        "girsu{ki}":         "Girsu",
        "girsu":             "Girsu",
        "uri5{ki}":          "Ur",
        "nibru{ki}":         "Nippur",
        "nibru":             "Nippur",
        "isin{ki}":          "Isin",
        "a-dam-dun{ki}":     "Adadun",
        "me-en-kar2":        "Menkara (field)",
        "la2-mah":           "Lahmah (field)",
        "la2-tur":           "Lahtur (field)",
    }

    NAME_MAP: Dict[str, str] = {
        # Governors and senior officials
        "ur-{d}li9-si4":    "Ur-Lisi",
        "ur-li9-si4":       "Ur-Lisi",
        "ur-lisi":          "Ur-Lisi",
        "arad-{d}nanna":    "Arad-Nanna",
        "arad-nanna":       "Arad-Nanna",
        "lugal-ezen":       "Lugal-ezen",
        "lugal-e2-mah-e":   "Lugal-emah",
        "lugal-e2-mah":     "Lugal-emah",
        # Common personal names
        "ur-{d}nanna":      "Ur-Nanna",
        "ur-nanna":         "Ur-Nanna",
        "ur-{d}suen":       "Ur-Suen",
        "ur-suen":          "Ur-Suen",
        "ur-{d}utu":        "Ur-Utu",
        "ur-utu":           "Ur-Utu",
        "ur-{d}dumu-zi":    "Ur-Dumuzi",
        "ur-dumu-zi":       "Ur-Dumuzi",
        "ur-{d}szara2":     "Ur-Shara",
        "ur-{gesz}gigir":   "Ur-gigir",
        "ur-mes":           "Ur-Mes",
        "ur-{d}mes":        "Ur-Mes",
        "a-a-kal-la":       "Ayakalla",
        "a-kal-la":         "Akalla",
        "a-tu":             "Atu",
        "lu2-{d}nanna":     "Lu-Nanna",
        "lu2-nanna":        "Lu-Nanna",
        "lu2-{d}dumu-zi":   "Lu-Dumuzi",
        "lu2-dumu-zi":      "Lu-Dumuzi",
        "lu2-{d}inanna":    "Lu-Inanna",
        "lu2-dingir-ra":    "Lu-dingira",
        "i3-li2-bi-la-ni":  "Ili-bilani",
        "inim-{d}inanna":   "Inim-Inanna",
        "nam-ha-ni":        "Namhani",
        "szesz-kal-la":     "Shesh-kalla",
        "na-lu5":           "Nalu",
        "da-da":            "Dada",
        "da-a-ga":          "Daga",
        "a2-zi-da":         "Azida",
        "ab-ba-sa6-ga":     "Abba-saga",
        "ab-ba-saga":       "Abba-saga",
        "lugal-sa6-ga":     "Lugal-saga",
        "lugal-nesag-e":    "Lugal-nesage",
        "szu-{d}suen":      "Shu-Suen (person)",
        "puzur4-{d}en-lil2":"Puzur-Enlil",
        "nig2-{d}ba-ba6":   "Nig-Baba",
        "lu2-du10-ga":      "Lu-duga",
        "lu2-sa6-ga":       "Lu-saga",
        "a-du-mu":          "Adumu",
        "a-gu":             "Agu",
        "szar-ru-um-i3-li2":"Sharrum-ili",
    }

    def __init__(self, fuzzy_threshold: float = 0.82) -> None:
        self.fuzzy_threshold = fuzzy_threshold
        self._all: Dict[str, str] = {}
        self._all.update(self.TITLE_MAP)
        self._all.update(self.INSTITUTION_MAP)
        self._all.update(self.NAME_MAP)

    def _clean(self, name: str) -> str:
        """Lowercase, remove damage markers, determinatives, and brackets."""
        name = name.lower().strip()
        name = re.sub(r"[!?*#]", "", name)
        name = re.sub(r"\[.*?\]", "", name)
        # Strip ATF determinatives {d} {ki} {gesz} etc. for lookup
        name = re.sub(r"\{[^}]+\}", "", name)
        name = re.sub(r"\s+", " ", name).strip()
        return name

    def _fuzzy_match(self, name: str) -> Optional[str]:
        best_ratio = 0.0
        best: Optional[str] = None
        for key, canonical in self._all.items():
            ratio = SequenceMatcher(None, name, key).ratio()
            if ratio > best_ratio:
                best_ratio, best = ratio, canonical
        return best if best_ratio >= self.fuzzy_threshold else None

    def normalize_name(self, name: Optional[str]) -> Optional[str]:
        """Normalize a name or title string to a canonical form."""
        if not name:
            return name

        cleaned = self._clean(name)

        if cleaned in self._all:
            return self._all[cleaned]

        # Whole-token substring scan (longest match wins).
        # Require the key to appear as a standalone token — not embedded inside
        # a compound name like "lugal-gigir" — by checking that it is not
        # immediately preceded or followed by a name-linking character (- or letter).
        best_key_len = 0
        best_canon: Optional[str] = None
        for key, canonical in self._all.items():
            if key not in cleaned:
                continue
            pat = r"(?<![a-z0-9\-{])" + re.escape(key) + r"(?![a-z0-9\-}])"
            if re.search(pat, cleaned) and len(key) > best_key_len:
                best_key_len, best_canon = len(key), canonical
        if best_canon and best_key_len >= 3:
            return best_canon

        fuzzy = self._fuzzy_match(cleaned)
        if fuzzy:
            return fuzzy

        return cleaned

    def normalize_transaction(self, tx: Transaction) -> Transaction:
        tx.issuer    = self.normalize_name(tx.issuer)
        tx.recipient = self.normalize_name(tx.recipient)
        tx.agent     = self.normalize_name(tx.agent)
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
                commodity=tx.commodity or "",
            )
        # Annotate nodes with commodity sets
        for node in (tx.issuer, tx.recipient):
            if "commodities" not in self.graph.nodes[node]:
                self.graph.nodes[node]["commodities"] = set()
            if tx.commodity:
                self.graph.nodes[node]["commodities"].add(tx.commodity)

    def build(self, transactions: List[Transaction]) -> nx.DiGraph:
        for tx in transactions:
            self.add_transaction(tx)
        return self.graph


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_metrics(G: nx.DiGraph) -> Dict:
    """Return standard network metrics for a directed graph."""
    metrics = {
        "degree_centrality":      nx.degree_centrality(G),
        "in_degree_centrality":   nx.in_degree_centrality(G),
        "out_degree_centrality":  nx.out_degree_centrality(G),
        "betweenness_centrality": nx.betweenness_centrality(G, weight="weight"),
        "density":                nx.density(G),
        "num_weakly_connected_components": nx.number_weakly_connected_components(G),
    }
    try:
        metrics["pagerank"] = nx.pagerank(G, weight="weight")
    except Exception:
        # pagerank requires scipy/numpy; fall back to in-degree centrality
        metrics["pagerank"] = metrics["in_degree_centrality"]
    return metrics


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_to_gexf(G: nx.DiGraph, filepath: str) -> None:
    """Export the transaction network to GEXF format for Gephi."""
    # Convert set attributes to strings (GEXF doesn't support sets)
    H = G.copy()
    for node in H.nodes():
        if "commodities" in H.nodes[node]:
            H.nodes[node]["commodities"] = ",".join(
                sorted(H.nodes[node]["commodities"])
            )
    try:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        nx.write_gexf(H, filepath)
        logger.info("Network exported to GEXF: %s", filepath)
    except OSError as exc:
        logger.error("Failed to write GEXF to %s: %s", filepath, exc)


def export_transactions_csv(transactions: List[Transaction], filepath: str) -> None:
    """Export the raw transaction list to CSV for further analysis."""
    if not transactions:
        logger.warning("No transactions to export.")
        return

    fieldnames = [
        "tablet_id", "issuer", "recipient", "agent",
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
            "agent":            tx.agent or "",
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
    import sys

    output_dir = "output/"

    # Accept an optional path argument: either a CDLI export text file or a
    # directory of .atf files.  Default falls back to data/raw_atf/.
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if os.path.isfile(arg):
            corpus = load_cdli_export_file(arg)
        elif os.path.isdir(arg):
            corpus = load_corpus(arg)
        else:
            logger.error("Path not found: %s", arg)
            return
    elif os.path.isfile("data/cdli_export.txt"):
        corpus = load_cdli_export_file("data/cdli_export.txt")
    else:
        corpus = load_corpus("data/raw_atf/")

    if not corpus:
        logger.error("No tablets loaded.")
        return

    extractor  = ATFExtractor(default_king="Šulgi")
    normalizer = Normalizer()

    all_transactions:    List[Transaction] = []
    barley_transactions: List[Transaction] = []
    commodity_counts: Dict[str, int] = {}

    for tablet_id, lines in corpus.items():
        txs = extractor.extract_transactions(lines, tablet_id)
        for tx in txs:
            tx = normalizer.normalize_transaction(tx)
            all_transactions.append(tx)
            if tx.commodity:
                commodity_counts[tx.commodity] = commodity_counts.get(tx.commodity, 0) + 1
            if tx.commodity == "barley":
                barley_transactions.append(tx)

    logger.info(
        "Extracted %d total transactions, %d barley.",
        len(all_transactions), len(barley_transactions),
    )

    print(f"\nCommodity breakdown:")
    for comm, cnt in sorted(commodity_counts.items(), key=lambda x: -x[1]):
        print(f"  {comm:15s}: {cnt}")

    # Šulgi years 45-48 barley slice
    sulgi_slice = [
        tx for tx in barley_transactions
        if tx.date and tx.date.in_range("Šulgi", 45, 48)
    ]
    logger.info("Šulgi years 45-48 barley transactions: %d", len(sulgi_slice))

    # Build network from all barley transactions
    builder = NetworkBuilder()
    G = builder.build(barley_transactions)

    print(f"\nBarley transaction network")
    print(f"  Nodes : {G.number_of_nodes()}")
    print(f"  Edges : {G.number_of_edges()}")

    if G.number_of_nodes() > 0:
        metrics = compute_metrics(G)
        print(f"  Density              : {metrics['density']:.4f}")
        print(f"  Weakly conn. comps   : {metrics['num_weakly_connected_components']}")

        print("\nTop 5 by PageRank (overall importance):")
        pr = sorted(metrics["pagerank"].items(), key=lambda x: x[1], reverse=True)
        for node, val in pr[:5]:
            print(f"  {node}: {val:.4f}")

        print("\nTop 5 by betweenness centrality (brokers):")
        bc = sorted(metrics["betweenness_centrality"].items(), key=lambda x: x[1], reverse=True)
        for node, val in bc[:5]:
            print(f"  {node}: {val:.4f}")

        print("\nTop 5 by in-degree centrality (major recipients):")
        idc = sorted(metrics["in_degree_centrality"].items(), key=lambda x: x[1], reverse=True)
        for node, val in idc[:5]:
            print(f"  {node}: {val:.4f}")

    os.makedirs(output_dir, exist_ok=True)
    export_to_gexf(G, os.path.join(output_dir, "barley_network.gexf"))
    export_transactions_csv(all_transactions,    os.path.join(output_dir, "transactions_all.csv"))
    export_transactions_csv(barley_transactions, os.path.join(output_dir, "transactions_barley.csv"))
    if sulgi_slice:
        export_transactions_csv(
            sulgi_slice,
            os.path.join(output_dir, "transactions_sulgi_45-48.csv"),
        )


if __name__ == "__main__":
    main()
