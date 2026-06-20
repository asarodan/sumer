"""Ur III royal chronology reference data.

Year-name fragment lists: ALL listed substrings must appear for a match.
Fragments are given in ASCII ATF (sz = s with caron, etc.) as found in CDLI
exports.  More-specific (us2-sa "year after") patterns must appear before their
plain variants so the first-match-wins resolver assigns the right year.
"""

from typing import Dict, List, Tuple


_URNAMMA_FRAGS: Dict[int, List[str]] = {
    1:  ["nanna-e2-a"],
    2:  ["ki-en-gi ki-uri"],
    5:  ["bad3 uri5{ki}"],
}

_ŠULGI_FRAGS: Dict[int, List[str]] = {
    # us2-sa (year-after) entries BEFORE their base year so first-match-wins
    # correctly assigns the more specific "year after" label.
    44: ["us2-sa", "bad3 ma-da"],      # year after border wall (corpus: us2-sa...bad3 ma-da mu-du3)
    18: ["en {d}inanna", "ba-hun"],    # en of Inanna installed (check before less-specific Y3)
    48: ["us2-sa", "ha-ar-szi{ki}"],   # year after Harši campaign
    46: ["us2-sa", "ki-masz{ki}"],     # year after Kimaš campaign
    # base years follow their us2-sa counterparts
    2:  ["szul-gi-iri-mu-sze3"],       # "my city" year (corpus: 15+ occ of iri-mu compound)
    3:  ["en {d}inanna", "i3-pa3"],    # en of Inanna chosen by oracle
    23: ["ur-bi2-lum", "si-mu-ru-um", "kar2-har"],  # eastern campaign: Urbi'um/Lulubum/Simurrum/Karhar
    33: ["dingir kalam-ma", "sza-asz-ru"],  # "god of the land" destroyed Šašrum
    43: ["bad3 ma-da"],                # border wall built (after Y44 to catch plain vs us2-sa)
    45: ["ki-masz{ki}"],               # Kimaš campaign
    47: ["ha-ar-szi{ki}"],             # Harši campaign
}

_AMARSUEN_FRAGS: Dict[int, List[str]] = {
    # us2-sa entries before base years
    3:  ["us2-sa", "ur-bi2-"],             # year after Urbilum; ur-bi2- prefix covers all spelling variants
    7:  ["us2-sa", "sza-asz", "mu-hul"],   # year after Šašrum; sza-asz covers all spelling variants
    # base years
    2:  ["ur-bi2-"],                       # Urbilum destroyed; ur-bi2- matches lum/i3-lum/ba-hul variants
    4:  ["gu-za", "{d}en-lil2", "in-dim2"],  # made throne for Enlil (corpus: 17 occ)
    6:  ["sza-asz", "mu-hul"],             # Šašrum destroyed; covers sza-asz-ru{ki} and sza-asz-szu2-ru-um variants
    8:  ["en eridu{ki} ba-hun"],           # en of Eridu installed (corpus: 200+ occ via en-nun-e formula)
    9:  ["hu-uh2-nu-ri{ki}"],              # Huhunuri campaign
}

_ŠUSUEN_FRAGS: Dict[int, List[str]] = {
    # us2-sa entries before their base years
    3:  ["us2-sa", "bad3 mar-tu"],     # year after Martu wall (corpus: 9+ occ)
    9:  ["us2-sa", "ma2-gur8"],       # year after great boat (covers both ma2-gur8-mah and ma2-gur8 mah)
    # base years
    2:  ["bad3 mar-tu"],               # Martu wall "Muriq-Tidnim" built (corpus: 66+49 occ)
    4:  ["za-ab-sza-li{ki}"],          # Zabšali destroyed (corpus: 365 occ)
    5:  ["si-ma-num2{ki}"],            # Simanam destroyed (corpus: 30+ occ)
    6:  ["e2 {d}szara2", "umma{ki}"],  # Šara temple at Umma built (corpus: 122 occ)
    7:  ["na-ru2-a"],                  # great stele (na-ru2-a-mah / na-ru2-a mah space variant)
    8:  ["ma2-gur8"],                  # great boat (ma2-gur8-mah / ma2-gur8 mah space variant)
}

_IBBISUEN_FRAGS: Dict[int, List[str]] = {
    2:  ["si-mu-ru-um{ki}", "mu-hul"], # Simurrum destroyed (corpus: 51+35 occ)
    3:  ["dalla mu-un-na-an-e3-a"],    # Nanna's heart displayed (corpus: 33 occ)
    4:  ["nun-me-te-an-na"],           # built Nun-me-te-anna for Nanna (corpus: 13 occ)
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
