"""
atf_pipeline.py

Pipeline for parsing Ur III cuneiform administrative tablets (ATF format)
from the CDLI corpus, extracting transactions from the Umma provincial
archive, and modelling them as a directed weighted network.

ATF format docs:  https://oracc.museum.upenn.edu/doc/help/editinginatf/
CDLI year names:  https://cdli.mpiwg-berlin.mpg.de/
BDTNS:            https://bdtns.filol.csic.es/

Encoding note: CDLI bulk exports use ASCII ATF transliteration.
  š → sz  (szu ba-ti, szunigin, szabra ...)
  ú/ū → u2
All regex patterns accept both ASCII ATF and Unicode forms.
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
# Year-name fragment lists: ALL listed substrings must appear for a match.
# Fragments given in ASCII ATF (sz = š, etc.) as found in CDLI exports.
# More-specific (us2-sa) patterns must appear before their plain variants
# in the dict so the first-match-wins loop resolves ambiguities correctly.

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

KING_YEAR_MAP: Dict[str, Tuple[str, Dict[int, List[str]]]] = {
    "ur-namma":        ("Ur-Namma",   _URNAMMA_FRAGS),
    "ur-{d}namma":     ("Ur-Namma",   _URNAMMA_FRAGS),
    # Šulgi – Unicode and ASCII ATF
    "šul-gi":          ("Šulgi",      _ŠULGI_FRAGS),
    "{d}šul-gi":       ("Šulgi",      _ŠULGI_FRAGS),
    "šulgi":           ("Šulgi",      _ŠULGI_FRAGS),
    "sulgi":           ("Šulgi",      _ŠULGI_FRAGS),
    "szul-gi":         ("Šulgi",      _ŠULGI_FRAGS),
    "{d}szul-gi":      ("Šulgi",      _ŠULGI_FRAGS),
    # Amar-Suen
    "amar-{d}suen":    ("Amar-Suen",  _AMARSUEN_FRAGS),
    "amar-suen":       ("Amar-Suen",  _AMARSUEN_FRAGS),
    # Šu-Suen – Unicode and ASCII ATF
    "šu-{d}suen":      ("Šu-Suen",    _ŠUSUEN_FRAGS),
    "šu-suen":         ("Šu-Suen",    _ŠUSUEN_FRAGS),
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


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

_RE_EXPORT_NOISE = re.compile(
    r"https?://cdli\.|Page\s+\d+\s+of\s+\d+|^\s*:\s*$", re.I
)
_RE_TABLET_HEADER = re.compile(r"^&(P\d+)\s*=")


def parse_cdli_export(text: str) -> Dict[str, List[str]]:
    """
    Parse a CDLI multi-tablet bulk export into {cdli_id: [atf_lines]}.
    Handles browser/PDF page headers and multi-tablet ATF dump files.
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
    """Load and parse a CDLI bulk ATF export text file."""
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            with open(filepath, "r", encoding=enc) as fh:
                text = fh.read()
            result = parse_cdli_export(text)
            if result:
                logger.info(
                    "Loaded CDLI export: %s (%s, %d tablets)",
                    filepath, enc, len(result),
                )
                return result
        except UnicodeDecodeError:
            continue
        except OSError as exc:
            logger.error("Cannot open %s: %s", filepath, exc)
            return {}
    logger.warning("No working encoding found for %s.", filepath)
    return {}


def load_atf_file(filepath: str) -> List[str]:
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            with open(filepath, "r", encoding=enc) as fh:
                return [line.rstrip("\n") for line in fh]
        except UnicodeDecodeError:
            continue
        except OSError as exc:
            logger.error("Cannot open %s: %s", filepath, exc)
            return []
    return []


def load_corpus(directory: str) -> Dict[str, List[str]]:
    """Load all *.atf files from a directory."""
    if not os.path.isdir(directory):
        logger.error("Corpus directory not found: %s", directory)
        return {}
    corpus: Dict[str, List[str]] = {}
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".atf"):
            continue
        lines = load_atf_file(os.path.join(directory, filename))
        if lines:
            corpus[filename] = lines
    logger.info("Loaded %d ATF files from %s", len(corpus), directory)
    return corpus


# ---------------------------------------------------------------------------
# ATF Extractor
# ---------------------------------------------------------------------------

class ATFExtractor:
    """
    Extract transaction records from Ur III administrative ATF tablets.

    Supported extraction patterns (in priority order):

    ISSUERS
      A. ki NAME-ta        Line starts with "ki NAME-ta" (ablative postposition)
      B. ki NAME           Line starts with "ki NAME" (abbreviated ablative)
      C. NAME ki / NAME ki2  Line ends with "ki" (older corpus convention)
      D. INST-ta           Institution name + ablative -ta (e2-X-ta, guru7-ta)
      E. kiszib3 NAME      Seal authority — used as fallback issuer

    RECIPIENTS
      F. NAME szu ba-ti    Inline receipt formula
      G. szu ba-ti alone   Standalone receipt → previous name line is recipient
      H. NAME i3-dab5      Alternative receipt formula
      I. N(u) sze NAME     Inline distribution (quantity + barley + name)
      J. ba-an-szum2       Dative "was given" with preceding -ra name

    FIELD ALLOCATIONS (whole-tablet scan)
      K. qty / NAME engar  Grain allocation to farmer; szabra is issuer
         repeated pairs with deferred or leading szabra labels

    AGENTS
      L. giri3 NAME        Responsible official

    DATES
      - iti [month]        Month line
      - mu [year-name]     Year name (king identification via fragment matching)
      - u4 N(-kam)         Day line

    Quantity system (all normalised to sila3):
      szar2=1,080,000  gesz'u=180,000  gesz2=18,000  asz/gur=300
      barig=60  ban2=10  disz/sila3=1
      Fractional coefficients (1/2(disz) etc.) are handled.
    """

    _RE_LINENUM   = re.compile(r"^\d+[a-z]?[!?*'ʼ]?\.\s*(?:[a-z]\.\s*)?")

    # CDLI metrological tokens: integer and fractional coefficients
    _RE_QTY_CDLI  = re.compile(r"(\d+(?:/\d+)?)\((\w+[2']?)\)")
    _RE_QTY_PLAIN = re.compile(
        r"(\d+(?:\.\d+)?)\s+(gur|barig|ban2|sila3?|gin2|ma-na)", re.I
    )

    # Grain capacity system (sila3 per unit)
    _GRAIN_CONV: Dict[str, float] = {
        "szar2":  3600.0 * 300.0,
        "gesz'u":  600.0 * 300.0,
        "gesz2":    60.0 * 300.0,
        "asz":         300.0,
        "gur":         300.0,
        "barig":        60.0,
        "ban2":         10.0,
        "disz":          1.0,
        "sila3":         1.0,
        "sila":          1.0,
    }
    # Units that definitively mark a grain/capacity measurement
    # gesz2/gesz'u/szar2 are large sexagesimal grain units — unambiguous even alone
    _GRAIN_IND = frozenset({
        "gur", "barig", "ban2", "sila3", "sila", "asz",
        "gesz2", "gesz'u", "geszu", "szar2",
    })

    # Bare grain-unit words (not in N(unit) format) used as context markers
    _RE_BARE_GUR = re.compile(r"(?:^|\s)gur\b", re.I)

    # Labor/worker-day line indicators — these are NEVER grain quantities
    _RE_LABOR_LINE = re.compile(r"\bgurusz\b|\bgeme2\b", re.I)

    # Transfer-formula signals used for tablet-type classification
    _RE_TRANSFER_SIGNAL = re.compile(
        r"\bs[zž]u\s+ba-ti\b|\bki\s+\S+-ta\b|\bba-zi\b|\bi3-dab5\b", re.I
    )

    # Words that cannot be personal names
    _GRAIN_UNIT_WORDS = frozenset({
        "gur", "barig", "ban2", "sila3", "sila", "asz",
        "gesz2", "szar2", "ziz2", "gig",
    })

    # Commodities (ASCII ATF corpus)
    _RE_BARLEY = re.compile(r"\bsze(?!-gesz)\b|\bše\b|\bbarley\b|\bsze-ba\b", re.I)
    _RE_EMMER  = re.compile(r"\bziz2\b|\bemmer\b", re.I)
    _RE_WHEAT  = re.compile(r"\bgig\b|\bwheat\b", re.I)
    _RE_DATES  = re.compile(r"\bzu2-lum\b|\bdates?\b", re.I)
    _RE_FLOUR  = re.compile(r"\bzi3\b|\bzi3-gu\b|\bdabin\b|\bflour\b", re.I)
    _RE_BEER   = re.compile(r"\bkasz\b|\bdida\b|\bbeer\b", re.I)
    _RE_OIL    = re.compile(r"\bi3-gesz\b|\bsze-gesz-i3\b|\boil\b", re.I)
    _RE_SILVER = re.compile(r"\bku3-babbar\b|\bsilver\b", re.I)

    # --------------- Issuer patterns ---------------
    # A/B: ki NAME-ta or ki NAME at line start
    _RE_KI_TA    = re.compile(r"^ki#?\s+(.+?)-ta(?:\s|$)(?:#.*)?$")
    _RE_KI_ONLY  = re.compile(r"^ki#?\s+([a-z{}\-0-9\[\]]+(?:\s+[a-z{}\-0-9\[\]]+)*)\s*(?:#.*)?$", re.I)
    # C: NAME ki at line end (reject {ki} determinative)
    _RE_KI_ABL   = re.compile(r"^(.*?)\s+ki(?:2)?\s*(?:#.*)?$")
    _RE_KI_DET   = re.compile(r"\}\s*ki(?:2)?\s*(?:#.*)?$")
    # D: institution + -ta (e2-X-ta, guru7-ta, a-sza3 X-ta)
    _RE_INST_ABL = re.compile(
        r"^(e2-\S+|guru7\S*|a-sza3\s+\S+|sza3\s+\S+)-ta\s*(?:#.*)?$", re.I
    )
    # E: kiszib3 NAME (seal authority – fallback issuer); also inline mid-line
    _RE_KISZIB        = re.compile(r"^kiszib3#?\s+(.+?)(?:\s*(?:#.*)?)?$")
    _RE_KISZIB_INLINE = re.compile(r"\bkiszib3#?\s+([a-z{}\-0-9\[\]]+(?:\s+[a-z{}\-0-9\[\]]+)*?)(?:\s+(?:kiszib3|giri3|mu|iti|u3)\b|$)", re.I)

    # --------------- Recipient patterns ---------------
    # F: NAME szu/šu ba-ti on same line
    _RE_SHU_BATI  = re.compile(
        r"^(.*?)\s+s[zž]u#?\s+ba-(?:an-|ab-)?ti(?:\s+\S+)?\s*(?:#.*)?$"
    )
    # G: standalone szu/šu ba-ti (allow leading bracket damage like "[szu] ba-ti")
    _RE_SHU_ALONE = re.compile(r"^\[?s[zž]u#?\]?\s+ba-(?:ab-|an-)?ti\s*(?:#.*)?$")
    # H: NAME i3-dab5 / in-dab5 (received)
    _RE_IDAB5     = re.compile(r"^(.*?)\s+i(?:3-|n-)dab5\b")
    # I: N(u) sze NAME – inline ration distribution
    _RE_U_SZE     = re.compile(
        r"^(\d+)\(u\)\s+sze\s+(.+?)(?:\s+dumu(?:-ni|-munus)?)?\s*(?:#.*)?$"
    )
    # J: dative -ra for ba-an-szum2
    _RE_DATIVE_RA = re.compile(r"^(.+?)-ra\s*(?:#.*)?$")
    _RE_BA_AN_SUM = re.compile(r"\bba-an-s[zž]um2?\b")
    # K2: sa2-du11 NAME – regular/statutory payment to named institution or person
    _RE_SA2_DU11  = re.compile(r"^sa2-du11\s+(.+?)(?:\s*(?:#.*)?)?$", re.I)

    # --------------- Field allocation patterns ---------------
    _RE_SZABRA = re.compile(r"^(.+?)\s+s[zž]abra\b")
    _RE_ENGAR  = re.compile(r"^(.*?)\s+engar\b")

    # --------------- Agent ---------------
    _RE_GIRI3  = re.compile(r"^giri3#?\s+(.+?)(?:\s*(?:#.*)?)?$")
    _RE_UGULA  = re.compile(r"^ugula#?\s+(.+?)(?:\s*(?:#.*)?)?$")

    # --------------- Date ---------------
    _RE_ITI = re.compile(
        r"^(?:\d+[a-z]?[!?*'ʼ]?\.\s*)?iti\s+(\S+(?:\s+\S+)*?)"
        r"(?:\s+u4[-\s](\d+)(?:-kam)?)?\s*(?:#.*)?$",
        re.I,
    )
    _RE_MU  = re.compile(
        r"^(?:\d+[a-z]?[!?*'ʼ]?\.\s*)?mu\s+(.+?)(?:\s*#.*)?$", re.I
    )
    _RE_U4  = re.compile(r"\bu4[-\s](\d+)(?:-kam)?\b")

    # --------------- Section boundaries ---------------
    _RE_SZUNIGIN = re.compile(
        r"^\d+[a-z]?[!?*'ʼ]?\.\s*(?:szunigin|šunigin|szu-nigin2?|šu-nigin2?)\b",
        re.I,
    )

    # Lines that are not personal names
    _RE_NOT_NAME = re.compile(
        r"^\d|^[@$#]"
        r"|^(?:iti|mu|giri3|ki|ugula|kiszib3|szunigin|šunigin"
        r"|sze-ba|sza3-bi-ta|zi-ga|la2-ia3|nig2-ka9|sag-nig2"
        r"|engar|szabra|šabra|szu-a|sza3-gal"
        r"|nu-banda3|kuruszda|muhaldim|szusz3|dub-sar)\b"
        r"|^u4\s"           # date day token (u4 N-kam) — "day N"
        r"|^sze\s"          # commodity formula (sze ur5-ra, sze-ba etc.) — not a name
        r"|^asz\s"          # asz (unit/number) followed by space — not a name start
        r"|^dumu\s+\S",     # "son of NAME" parentage formula (not a standalone name)
        re.I,
    )

    # Administrative titles used for name+title recipient extraction
    _ADMIN_TITLES = re.compile(
        r"\b(?:szagina|muhaldim|sukkal|aszgab|nu-banda3|szabra|šabra|dub-sar|"
        r"kas4|lu2-kin-gi4-a|lu2-kinda)\b",
        re.I,
    )

    # -------------------------------------------------------------------------

    def __init__(self, default_king: Optional[str] = None) -> None:
        self._default_king = default_king

    def _strip_linenum(self, line: str) -> str:
        return self._RE_LINENUM.sub("", line).strip()

    @staticmethod
    def _is_content(line: str) -> bool:
        s = line.strip()
        return bool(s) and s[0].isdigit()

    _RE_TITLE_SUFFIX = re.compile(
        r"\s+(?:nu-banda3(?:-gu4)?|szabra|šabra|dub-sar|kuruszda|muhaldim"
        r"|szusz3|šuš3|kas4|sukkal|engar|agrig|simug|nagar|tibira|azlag2"
        r"|nu-kiri6|szidim|aszgab|zadim|bahar2|bahar3|ma2-lah5|lu2-kikken2"
        r"|aga3-us2|aga-us2|lu2-kin-gi4-a)\s*$",
        re.I,
    )

    _RE_TITLE_PREFIX = re.compile(
        r"^(?:nu-banda3(?:-gu4)?|kuruszda|muhaldim|szusz3|dub-sar"
        r"|lu2-kin-gi4-a|lu2-kinda)\s+",
        re.I,
    )

    @staticmethod
    def _clean_atf_name(name: str) -> str:
        """Strip damage markers and trailing grammatical suffixes from a name."""
        name = re.sub(r"\(\$[^)]*\$\)", "", name)   # CDLI editorial markers ($...$)
        name = re.sub(r"\([a-z][a-z0-9]*\)", "", name)  # sign variant: nig2-lagar(ba)→nig2-lagar
        name = re.sub(r"[!?*#]", "", name)
        name = re.sub(r"\[.*?\]", "", name)
        name = re.sub(r"-ta\s*$", "", name)
        name = re.sub(r"-sze3\s*$", "", name)        # terminative suffix — never part of a stored name
        # Strip Sumerian conjunction "and" when it prefixes a name: "u3 NAME" → "NAME"
        name = re.sub(r"^u3\s+", "", name, flags=re.I)
        # Strip genealogy suffix: "NAME dumu FATHER" → "NAME"
        name = re.sub(r"\s+dumu(?:-munus)?\b.+$", "", name, flags=re.I)
        # Strip leading title when followed by space: "nu-banda3 NAME" → "NAME"
        name = ATFExtractor._RE_TITLE_PREFIX.sub("", name)
        # Strip trailing administrative title: "NAME nu-banda3" → "NAME"
        name = ATFExtractor._RE_TITLE_SUFFIX.sub("", name)
        return re.sub(r"\s+", " ", name).strip()

    def _looks_like_name(self, clean: str) -> bool:
        """Heuristic: does this look like a standalone personal name line?"""
        if self._RE_NOT_NAME.match(clean):
            return False
        if re.search(r"\b(?:gur|barig|ban2|sila3|gin2)\b", clean):
            return False
        if re.search(r"\(\$", clean):      # CDLI editorial marker ($ blank space $)
            return False
        if len(clean) < 2 or len(clean) > 60:
            return False
        return True

    # --- quantity -----------------------------------------------------------

    def extract_quantity(self, line: str) -> Tuple[Optional[float], Optional[str]]:
        """
        Parse grain quantity; return (value_in_sila3, primary_unit).
        Non-grain lines (worker-days, animals, area) return (None, None).

        Handles the CDLI sexagesimal large-gur notation where counting units
        (u=10, gesz2=60, etc.) are relative to a bare 'gur' at line end:
          "5(u) sze gur"    → 50 gur  = 15,000 sila3
          "2(gesz2) sze gur" → 120 gur = 36,000 sila3
        """
        # Worker-day lines (gurusz / geme2) are never grain quantities
        if self._RE_LABOR_LINE.search(line):
            return None, None

        cdli = self._RE_QTY_CDLI.findall(line)
        if cdli:
            units = {u.lower() for _, u in cdli}
            # Check if a bare 'gur' appears as the unit context word (not as N(gur))
            bare_gur = bool(self._RE_BARE_GUR.search(line))
            if not (units & self._GRAIN_IND) and not bare_gur:
                return None, None
            total = 0.0
            first_unit = cdli[0][1].lower()
            for num_s, unit in cdli:
                ul = unit.lower()
                factor = self._GRAIN_CONV.get(ul)
                # In a bare-gur context, 'u' (the counting-ten unit) = 10 × gur
                if factor is None and bare_gur and ul == "u":
                    factor = 10.0 * 300.0   # 10 gur per 'u' unit
                if factor is None:
                    continue
                if "/" in num_s:
                    n, d = num_s.split("/", 1)
                    coeff = float(n) / float(d)
                else:
                    coeff = float(num_s)
                total += coeff * factor
            reported_unit = "gur" if bare_gur else first_unit
            return (total, reported_unit) if total > 0 else (None, None)

        m = self._RE_QTY_PLAIN.search(line)
        if m:
            return float(m.group(1)), m.group(2).lower()
        return None, None

    def _qty_from_u_sze(self, u_count: str) -> float:
        """N(u) sze → N×10 sila3 (small ration distribution format)."""
        return int(u_count) * 10.0

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

    # --- issuer extraction --------------------------------------------------

    def _extract_issuer(self, clean: str) -> Optional[str]:
        """
        Try all issuer patterns (A–D) in order; return name or None.
        Pattern E (kiszib3) is a fallback applied outside this method.
        """
        # A: ki NAME-ta (ablative with suffix)
        m = self._RE_KI_TA.match(clean)
        if m:
            cand = self._clean_atf_name(m.group(1))
            if len(cand) >= 2:
                return cand

        # B: ki NAME (abbreviated ablative, line-end, nothing after name)
        m = self._RE_KI_ONLY.match(clean)
        if m:
            cand = self._clean_atf_name(m.group(1))
            # Reject known non-ablative ki compounds (threshing floor su7, geographic masz)
            if (len(cand) >= 2
                    and not cand.startswith(("su7", "masz", "en-gi"))
                    and "{ki}" not in cand):
                return cand

        # C: NAME ki at line end
        if not self._RE_KI_DET.search(clean):
            m2 = self._RE_KI_ABL.match(clean)
            if m2:
                cand = self._clean_atf_name(m2.group(1))
                # Reject if candidate contains CDLI quantity tokens like 3(asz)
                if (len(cand) >= 2
                        and not cand.startswith(("$", "#"))
                        and not re.search(r"\d+\(", cand)):
                    return cand

        # D: institution name + -ta (without ki prefix)
        m3 = self._RE_INST_ABL.match(clean)
        if m3:
            cand = self._clean_atf_name(m3.group(1))
            if len(cand) >= 2:
                return cand

        return None

    # --- recipient extraction -----------------------------------------------

    def _extract_recipient_inline(self, clean: str) -> Optional[str]:
        """Pattern F: NAME szu ba-ti on same line."""
        m = self._RE_SHU_BATI.match(clean)
        if m:
            r = self._clean_atf_name(m.group(1))
            r = re.sub(r"-ra$", "", r).strip()
            if self._looks_like_name(r):
                return r
        return None

    def _extract_recipient_idab5(self, clean: str) -> Optional[str]:
        """Pattern H: NAME i3-dab5."""
        m = self._RE_IDAB5.match(clean)
        if m:
            cand = self._clean_atf_name(m.group(1).strip())
            # Strip trailing giri3 / sukkal clauses
            cand = re.sub(r"\s+giri3.*$", "", cand).strip()
            if self._looks_like_name(cand):
                return cand
        return None

    def _extract_recipient_u_sze(
        self, clean: str
    ) -> Tuple[Optional[str], Optional[float]]:
        """
        Pattern I: N(u) sze NAME — ration distribution.
        Returns (recipient_name, quantity_sila3) or (None, None).
        Rejects matches where the 'name' is actually a grain unit word
        (e.g. '5(u) sze gur' = 50 gur of barley, not a ration to 'gur').
        """
        m = self._RE_U_SZE.match(clean)
        if m:
            qty = self._qty_from_u_sze(m.group(1))
            name = self._clean_atf_name(m.group(2))
            if len(name) >= 2 and name.lower() not in self._GRAIN_UNIT_WORDS:
                return name, qty
        return None, None

    # --- agent extraction ---------------------------------------------------

    def _extract_agent(self, clean: str) -> Optional[str]:
        """Pattern L: giri3 NAME or ugula NAME."""
        for pat in (self._RE_GIRI3, self._RE_UGULA):
            m = pat.match(clean)
            if m:
                cand = self._clean_atf_name(m.group(1).strip())
                cand = re.sub(
                    r"\s+(?:dub-sar|sukkal|szagina|ensi2|szabra|ugula"
                    r"|nu-banda3|dumu\s+lugal|lu2\s+kin-gi4-a)\s*$", "", cand
                ).strip()
                if len(cand) >= 2:
                    return cand
        return None

    # --- date parsing -------------------------------------------------------

    def _resolve_king_year(self, year_str: str, date: "UrIIIDate") -> None:
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

    # --- tablet type classification -----------------------------------------

    @classmethod
    def _classify_tablet(cls, lines: List[str]) -> str:
        """
        Classify a tablet as 'transfer', 'labor', or 'allocation'.
        Labor accounts are characterised by many gurusz/geme2 lines
        and few or no transfer-formula lines.
        """
        labor = sum(1 for l in lines if cls._RE_LABOR_LINE.search(l))
        transfer = sum(1 for l in lines if cls._RE_TRANSFER_SIGNAL.search(l))
        engar = sum(1 for l in lines if re.search(r"\bengar\b", l, re.I))
        if engar >= 2:
            return "allocation"
        if labor >= 3 and labor >= transfer * 2:
            return "labor"
        return "transfer"

    # --- section splitting --------------------------------------------------

    def _split_sections(self, lines: List[str]) -> List[List[str]]:
        """Split tablet into sections at szunigin total lines only."""
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

    # --- bilateral transaction extraction -----------------------------------

    def _extract_from_section(
        self, section: List[str], tablet_id: str
    ) -> Optional[Transaction]:
        """
        Extract one bilateral transaction from a section.
        Uses patterns A–J in order; kiszib3 (E) is a last-resort fallback.
        """
        issuer:         Optional[str]   = None
        recipient:      Optional[str]   = None
        agent:          Optional[str]   = None
        quantity:       Optional[float] = None
        unit:           Optional[str]   = None
        commodity:      Optional[str]   = None
        pending_dative: Optional[str]   = None
        prev_name:      Optional[str]   = None
        kiszib_name:    Optional[str]   = None   # pattern E fallback
        first_linenum:  Optional[str]   = None

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

            # Pattern E candidate: kiszib3 NAME (save for fallback)
            # Match at line start OR inline (e.g. "1(gesz2) gur kiszib3 NAME")
            m_kiszib = self._RE_KISZIB.match(clean) or self._RE_KISZIB_INLINE.search(clean)
            if m_kiszib and kiszib_name is None:
                cand = self._clean_atf_name(m_kiszib.group(1))
                if len(cand) >= 2 and cand.lower() not in self._GRAIN_UNIT_WORDS:
                    kiszib_name = cand

            # Patterns A-D: issuer
            iss = self._extract_issuer(clean)
            if iss and issuer is None:
                issuer = iss
                # Do NOT reset prev_name here — the recipient often appears
                # on a line BEFORE the ki NAME-ta issuer line, and szu ba-ti
                # comes after. Clearing it would lose that recipient.
                continue

            # Agent (giri3 / ugula)
            ag = self._extract_agent(clean)
            if ag and agent is None:
                agent = ag

            # Pattern F: inline NAME szu ba-ti
            rec = self._extract_recipient_inline(clean)
            if rec and recipient is None:
                recipient = rec
                prev_name = None
                pending_dative = None
                continue

            # Pattern G: standalone szu ba-ti
            if self._RE_SHU_ALONE.match(clean) and recipient is None:
                recipient = prev_name or pending_dative
                prev_name = None
                pending_dative = None
                continue

            # Pattern H: NAME i3-dab5
            rec_h = self._extract_recipient_idab5(clean)
            if rec_h and recipient is None:
                recipient = rec_h
                prev_name = None
                continue

            # Pattern I: N(u) sze NAME — inline ration
            rec_i, qty_i = self._extract_recipient_u_sze(clean)
            if rec_i and recipient is None:
                recipient = rec_i
                if qty_i is not None and quantity is None:
                    quantity = qty_i
                    unit = "u"
                    commodity = commodity or "barley"
                prev_name = None
                continue

            # Pattern J: ba-an-szum2 with pending dative
            if self._RE_BA_AN_SUM.search(clean) and recipient is None:
                if pending_dative:
                    recipient = pending_dative
                    pending_dative = None
                continue

            # Pattern K2: sa2-du11 NAME — statutory payment, NAME is the recipient
            m_sa2 = self._RE_SA2_DU11.match(clean)
            if m_sa2 and recipient is None:
                cand = self._clean_atf_name(m_sa2.group(1).strip())
                # Apply same name-quality checks as the rest of the extractor
                if (self._looks_like_name(cand)
                        and not cand.endswith("-ta")
                        and not cand.endswith("-ka-ta")):
                    recipient = cand
                    # Don't continue — allow issuer/date to be set by later lines

            # Track dative -ra for pattern J
            m_dat = self._RE_DATIVE_RA.match(clean)
            if m_dat and not rec and not iss:
                cand = self._clean_atf_name(m_dat.group(1).strip())
                if self._looks_like_name(cand):
                    pending_dative = cand

            # Track previous name-like line for pattern G
            if self._looks_like_name(clean):
                prev_name = self._clean_atf_name(clean)
            elif not (self._RE_SHU_ALONE.match(clean)
                      or self._RE_BA_AN_SUM.search(clean)
                      or m_dat
                      or self._RE_NOT_NAME.match(clean)):
                # Don't reset on restricted keywords (titles like nu-banda3,
                # month/date lines, etc.) — they provide context but don't end
                # the "previous name" reference window.
                prev_name = None

        # Apply kiszib3 fallback for issuer (pattern E)
        if issuer is None and kiszib_name:
            issuer = kiszib_name

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
            tx_type="transfer",
        )

    # --- field allocation extraction ----------------------------------------

    def _extract_allocations(
        self, lines: List[str], tablet_id: str
    ) -> List[Transaction]:
        """
        Extract field-allocation transactions (szabra→engar grain distributions).

        Handles the deferred-label structure where the szabra (estate admin) is
        announced AFTER the szunigin total(s) that close his group.  Tablets with
        multiple commodities (barley + emmer + wheat) produce multiple consecutive
        szunigin lines before a single szabra label; the look-ahead scans up to
        five groups forward to find it.

        Each (szabra, engar, qty, commodity) tuple becomes one Transaction row.
        """
        date, raw_mu = self._parse_date(lines)

        events: List[Tuple[str, object]] = []
        for line in lines:
            s = line.strip()
            if not self._is_content(s):
                continue
            clean = self._strip_linenum(s)

            # Use the raw stripped line (still has line number) for szunigin
            # detection — _RE_SZUNIGIN requires a leading digit.
            if self._RE_SZUNIGIN.match(s):
                events.append(("total", None))
                continue

            m_szabra = self._RE_SZABRA.match(clean)
            if m_szabra:
                name = self._clean_atf_name(m_szabra.group(1))
                if name:
                    events.append(("szabra", name))
                continue

            if re.search(r"\bengar\b", clean):
                q_inline, u_inline = self.extract_quantity(clean)
                comm_inline = self._detect_commodity(clean)
                m_engar = self._RE_ENGAR.match(clean)
                raw_name = m_engar.group(1) if m_engar else ""
                name = re.sub(
                    r"^(?:\d+(?:/\d+)?\(\w+[2']*\)\s*)+", "", raw_name
                ).strip()
                name = re.sub(r"\s*(?:sze|gur|ziz2|gig)\s*$", "", name).strip()
                name = self._clean_atf_name(name)
                events.append(("engar", (name, q_inline, u_inline, comm_inline)))
                continue

            q, u = self.extract_quantity(clean)
            if q is not None:
                comm = self._detect_commodity(clean)
                events.append(("qty", (q, u, comm)))

        if sum(1 for e in events if e[0] == "engar") < 2:
            return []

        # Split into groups at szunigin boundaries
        groups: List[List[Tuple[str, object]]] = []
        current: List[Tuple[str, object]] = []
        for event in events:
            if event[0] == "total":
                groups.append(current)
                current = []
            else:
                current.append(event)
        if current:
            groups.append(current)

        results: List[Transaction] = []

        for i, group in enumerate(groups):
            issuer: Optional[str] = None

            # Look ahead through up to 5 groups to find the deferred szabra.
            # Tablets with multiple commodities have N consecutive szunigin
            # lines before the single szabra that labels them all.
            for j in range(i + 1, min(i + 6, len(groups))):
                if groups[j] and groups[j][0][0] == "szabra":
                    issuer = groups[j][0][1]  # type: ignore[assignment]
                    break

            # Fallback: szabra within this group (leading-label structure)
            if not issuer:
                for etype, edata in group:
                    if etype == "szabra":
                        issuer = edata  # type: ignore[assignment]
                        break
            if not issuer:
                continue

            pending_qty:  Optional[float] = None
            pending_unit: Optional[str]  = None
            pending_comm: Optional[str]  = None

            for etype, edata in group:
                if etype == "szabra":
                    continue
                if etype == "qty":
                    pending_qty, pending_unit, pending_comm = edata  # type: ignore[misc]
                elif etype == "engar":
                    name, q_inline, u_inline, comm_inline = edata  # type: ignore[misc]
                    qty  = q_inline  if q_inline  is not None else pending_qty
                    unit = u_inline  if q_inline  is not None else pending_unit
                    comm = comm_inline or pending_comm or "barley"
                    if qty is not None and name and len(name) >= 2:
                        results.append(Transaction(
                            tablet_id=tablet_id,
                            issuer=issuer,
                            recipient=name,
                            quantity=qty,
                            unit=unit,
                            commodity=comm,
                            date=date,
                            raw_date=raw_mu,
                            tx_type="allocation",
                        ))
                    if q_inline is None:
                        pending_qty = None

        return results

    # --- public interface ---------------------------------------------------

    def extract_transactions(
        self, lines: List[str], tablet_id: str
    ) -> List[Transaction]:
        """Extract all transactions from a tablet's ATF lines."""
        results: List[Transaction] = []
        tablet_type = self._classify_tablet(lines)

        # Allocation tablets: only run the allocation pass.
        # Running the bilateral pass on them produces ghost transactions from
        # szunigin total lines and double-counts individual engar entries.
        if tablet_type != "allocation":
            try:
                for section in self._split_sections(lines):
                    tx = self._extract_from_section(section, tablet_id)
                    if tx is not None:
                        if tx.tx_type == "transfer":
                            tx.tx_type = tablet_type
                        results.append(tx)
            except Exception as exc:
                logger.warning("Error in transfer pass for %s: %s", tablet_id, exc)

        # Allocation pass (whole-tablet scan)
        try:
            alloc = self._extract_allocations(lines, tablet_id)
            results.extend(alloc)
        except Exception as exc:
            logger.warning("Error in allocation pass for %s: %s", tablet_id, exc)

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
    Normalize personal names, administrative titles, and institutions.

    Strategy:
      1. Exact lookup (fastest).
      2. Whole-token substring scan (longest match, word-boundary aware).
      3. Fuzzy match via SequenceMatcher (fallback).
      4. Return cleaned original if no match.
    """

    TITLE_MAP: Dict[str, str] = {
        "ensi2":         "governor (ensi2)",
        "ensi":          "governor (ensi2)",
        "en":            "lord/high-priest",
        "szabra":        "estate-administrator (šabra)",
        "šabra":         "estate-administrator (šabra)",
        "agrig":         "steward (agrig)",
        "szusz3":        "livestock-official (šuš3)",
        "šuš3":          "livestock-official (šuš3)",
        "nu-banda3":     "inspector (nu-banda3)",
        "nu-banda":      "inspector (nu-banda3)",
        "nu-banda3-gu4": "cattle-inspector",
        "ugula":         "overseer (ugula)",
        "ugula-e2":      "household-overseer",
        "szagina":       "general (šagina)",
        "dub-sar":       "scribe (dub-sar)",
        "sukkal":        "secretary (sukkal)",
        "lu2-kin-gi4-a": "messenger",
        "lu2-kinda":     "barber",
        "engar":         "farmer/field-manager (engar)",
        "aszgab":        "leather-worker",
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
        "geme2":         "female-worker",
        "arad2":         "male-worker",
        "arad":          "male-worker",
        "munus":         "woman",
        "nita":          "man",
        "dumu":          "child/son-of",
        "dumu-munus":    "daughter-of",
        "gurusz":        "male-laborer",
        "kas4":          "courier (kas4)",
    }

    INSTITUTION_MAP: Dict[str, str] = {
        "e2-muhaldim":       "kitchen",
        "e2-uz-ga":          "sealed-storehouse",
        "e2-kiszib-ba":      "sealed-goods-office",
        "e2-duru5":          "village-household",
        "e2-kikken":         "mill-house",
        "e2":                "é (household)",
        "guru7":             "granary",
        "ka-guru7":          "granary-gate",
        "gur lugal":         "royal granary",
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
        "a-sza3":            "field",
        # Shara temple (common in Umma) — must be explicit to prevent fuzzy
        # match with 'szabra' (estate-administrator)
        "szara2":            "Shara-temple",
        "e2-szara2":         "Shara-temple",
    }

    NAME_MAP: Dict[str, str] = {
        "ur-{d}li9-si4":    "Ur-Lisi",
        "ur-li9-si4":       "Ur-Lisi",
        "arad-{d}nanna":    "Arad-Nanna",
        "arad-nanna":       "Arad-Nanna",
        "lugal-ezen":       "Lugal-ezen",
        "lugal-e2-mah-e":   "Lugal-emah",
        "lugal-e2-mah":     "Lugal-emah",
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
        "puzur4-{d}en-lil2":"Puzur-Enlil",
        "nig2-{d}ba-ba6":   "Nig-Baba",
        "lu2-du10-ga":      "Lu-duga",
        "lu2-sa6-ga":       "Lu-saga",
        "a-du-mu":          "Adumu",
        "a-gu":             "Agu",
        "szar-ru-um-i3-li2":"Sharrum-ili",
        "lu2-kal-la":       "Lukalla",
        "lugal-uszurx":     "Lugal-ushur",
        "gu-du-du":         "Gu-dudu",
        "ur-{d}nin-su":     "Ur-Ninsu",
        "ur-nigar{gar}":    "Ur-nigar",
        "lugal-amar-ku3":   "Lugal-amaku",
        "i3-kal-la":        "Ikalla",
        "szesz-saga":       "Shesh-saga",
        # Shara-deity personal names (Umma patron deity)
        "ur-{d}szara2":     "Ur-Shara",
        "ur-szara2":        "Ur-Shara",
        "inim-szara2":      "Inim-Shara",
        "lu2-szara2":       "Lu-Shara",
        "lugal-szuba3-gi":  "Lugal-shubagi",
        # Common Umma officials
        "lugal-ma2-gur8-re":"Lugal-magure",
        "lugal-nig2-lagar-e":"Lugal-nig2-lagare",
        "lugal-{gesz}gigir":"Lugal-gigir",
        "lu2-bala-saga":    "Lu-balasaga",
        "ur-sa6-ga":        "Ur-saga",
    }

    def __init__(self, fuzzy_threshold: float = 0.85) -> None:
        self.fuzzy_threshold = fuzzy_threshold
        self._all: Dict[str, str] = {}
        # Clean keys so determinatives ({d}, {gesz}, etc.) are stripped,
        # matching the cleaned input in normalize_name lookups.
        for src in (self.TITLE_MAP, self.INSTITUTION_MAP, self.NAME_MAP):
            for k, v in src.items():
                self._all[self._clean(k)] = v

    def _clean(self, name: str) -> str:
        name = name.lower().strip()
        name = re.sub(r"[!?*#]", "", name)
        name = re.sub(r"\[.*?\]", "", name)
        name = re.sub(r"\{[^}]+\}", "", name)
        return re.sub(r"\s+", " ", name).strip()

    def _fuzzy_match(self, name: str) -> Optional[str]:
        best_ratio = 0.0
        best: Optional[str] = None
        for key, canonical in self._all.items():
            ratio = SequenceMatcher(None, name, key).ratio()
            if ratio > best_ratio:
                best_ratio, best = ratio, canonical
        return best if best_ratio >= self.fuzzy_threshold else None

    def normalize_name(self, name: Optional[str]) -> Optional[str]:
        if not name:
            return name
        cleaned = self._clean(name)
        if cleaned in self._all:
            return self._all[cleaned]
        # Word-boundary-aware substring scan (longest key wins)
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
                tx.issuer, tx.recipient,
                weight=weight, count=1,
                commodity=tx.commodity or "",
            )
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
        metrics["pagerank"] = metrics["in_degree_centrality"]
    return metrics


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_to_gexf(G: nx.DiGraph, filepath: str) -> None:
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
            "unit":             "sila3" if tx.quantity is not None else "",
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    import sys
    output_dir = "output/"

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        corpus = (load_cdli_export_file(arg) if os.path.isfile(arg)
                  else load_corpus(arg) if os.path.isdir(arg)
                  else {})
        if not corpus:
            logger.error("Nothing loaded from: %s", arg)
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
    commodity_counts:    Dict[str, int]    = {}

    for tablet_id, lines in corpus.items():
        for tx in extractor.extract_transactions(lines, tablet_id):
            tx = normalizer.normalize_transaction(tx)
            all_transactions.append(tx)
            if tx.commodity:
                commodity_counts[tx.commodity] = commodity_counts.get(tx.commodity, 0) + 1
            if tx.commodity == "barley":
                barley_transactions.append(tx)

    n_total   = len(all_transactions)
    n_barley  = len(barley_transactions)
    n_tablets = len(set(tx.tablet_id for tx in all_transactions))
    n_complete = sum(1 for tx in all_transactions if tx.issuer and tx.recipient)
    n_complete_barley = sum(1 for tx in barley_transactions if tx.issuer and tx.recipient)

    logger.info("Extracted %d transactions from %d tablets; %d barley.",
                n_total, n_tablets, n_barley)

    print(f"\nExtraction summary")
    print(f"  Total transactions : {n_total}")
    print(f"  Tablets with data  : {n_tablets}/{len(corpus)} ({100*n_tablets//len(corpus)}%)")
    print(f"  Fully complete     : {n_complete}/{n_total} ({100*n_complete//max(n_total,1)}%)")

    print(f"\nCommodity breakdown:")
    for comm, cnt in sorted(commodity_counts.items(), key=lambda x: -x[1]):
        print(f"  {comm:15s}: {cnt}")

    by_comm: Dict[str, float] = {}
    for tx in all_transactions:
        if tx.quantity and tx.commodity:
            by_comm[tx.commodity] = by_comm.get(tx.commodity, 0) + tx.quantity
    total_sila3 = sum(tx.quantity for tx in all_transactions if tx.quantity)
    print(f"\nTotal sila3 across all tablets : {total_sila3:>20,.0f}")
    for comm, vol in sorted(by_comm.items(), key=lambda x: -x[1]):
        print(f"  {comm:<15s}             : {vol:>20,.0f}")

    sulgi_slice = [
        tx for tx in barley_transactions
        if tx.date and tx.date.in_range("Šulgi", 45, 48)
    ]
    logger.info("Šulgi yr 45-48 barley: %d", len(sulgi_slice))

    builder = NetworkBuilder()
    G = builder.build(barley_transactions)

    print(f"\nBarley network")
    print(f"  Nodes : {G.number_of_nodes()}")
    print(f"  Edges : {G.number_of_edges()}")
    print(f"  Fully-resolved barley tx : {n_complete_barley}/{n_barley} "
          f"({100*n_complete_barley//max(n_barley,1)}%)")

    if G.number_of_nodes() > 0:
        metrics = compute_metrics(G)
        print(f"  Density : {metrics['density']:.4f}")
        print(f"  Weakly conn. comps : {metrics['num_weakly_connected_components']}")

        print("\nTop 5 by PageRank:")
        pr = sorted(metrics["pagerank"].items(), key=lambda x: x[1], reverse=True)
        for node, val in pr[:5]:
            print(f"  {node}: {val:.4f}")

        print("\nTop 5 by betweenness (brokers):")
        bc = sorted(metrics["betweenness_centrality"].items(), key=lambda x: x[1], reverse=True)
        for node, val in bc[:5]:
            print(f"  {node}: {val:.4f}")

        print("\nTop 5 by in-degree (major recipients):")
        idc = sorted(metrics["in_degree_centrality"].items(), key=lambda x: x[1], reverse=True)
        for node, val in idc[:5]:
            print(f"  {node}: {val:.4f}")

    os.makedirs(output_dir, exist_ok=True)
    export_to_gexf(G, os.path.join(output_dir, "barley_network.gexf"))
    export_transactions_csv(all_transactions,    os.path.join(output_dir, "transactions_all.csv"))
    export_transactions_csv(barley_transactions, os.path.join(output_dir, "transactions_barley.csv"))
    if sulgi_slice:
        export_transactions_csv(sulgi_slice, os.path.join(output_dir, "transactions_sulgi_45-48.csv"))


if __name__ == "__main__":
    main()
