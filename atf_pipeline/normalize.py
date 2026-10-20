"""Name / title / institution normalisation with fuzzy fallback."""

import re
from difflib import SequenceMatcher
from typing import Dict, Optional

from atf_pipeline.models import Transaction


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

    # Ergative -ke4 (and plural -ke4-ne) is a grammatical agreement marker that
    # is never part of a personal-name root, so it can always be stripped.
    _RE_ERGATIVE = re.compile(r"^(.+?)-ke4(?:-ne)?$")
    # Other case markers (genitive -ka, dative -ra, ablative -ta, terminative
    # -sze3) are ambiguous: a name can genuinely end in -ra (lu2-dingir-ra) or
    # -ka. These are stripped only when the bare form is independently attested.
    _RE_CASE_SUFFIX = re.compile(r"^(.+?)-(?:ka|ra|ta|sze3)$")

    def __init__(self, fuzzy_threshold: float = 0.85) -> None:
        self.fuzzy_threshold = fuzzy_threshold
        self._all: Dict[str, str] = {}
        # Only role titles and institutions are translated to English; personal
        # names are kept in canonical ATF transliteration so the output is one
        # consistent representation instead of a mix of anglicised (Lu-Shara)
        # and raw (lu2-nin-szubur) forms. NAME_MAP is retained for reference but
        # intentionally not loaded into the lookup.
        for src in (self.TITLE_MAP, self.INSTITUTION_MAP):
            for k, v in src.items():
                self._all[self._clean(k)] = v
        # Set of attested (cleaned) names; populated by fit() to gate the
        # evidence-based case-suffix merge. None until fit() is called.
        self._known_roots: Optional[set] = None

    def fit(self, names) -> None:
        """Record every attested name so that an ambiguous case suffix is only
        merged when the bare form occurs on its own elsewhere in the corpus."""
        self._known_roots = {self._clean(n) for n in names if n}

    def _merge_case_suffix(self, cleaned: str) -> str:
        m = self._RE_ERGATIVE.match(cleaned)
        if m:
            return m.group(1)
        if self._known_roots is not None:
            m = self._RE_CASE_SUFFIX.match(cleaned)
            if m and m.group(1) in self._known_roots:
                return m.group(1)
        return cleaned

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
        # Personal name (no title/institution match): canonical ATF, with
        # grammatical case suffixes folded so the same actor is one node.
        return self._merge_case_suffix(cleaned)

    def normalize_transaction(self, tx: Transaction) -> Transaction:
        tx.issuer    = self.normalize_name(tx.issuer)
        tx.recipient = self.normalize_name(tx.recipient)
        if tx.agent and "; " in tx.agent:
            parts = [self.normalize_name(p) for p in tx.agent.split("; ")]
            tx.agent = "; ".join(p for p in parts if p) or None
        else:
            tx.agent = self.normalize_name(tx.agent)
        return tx
