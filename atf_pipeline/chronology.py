"""Ur III royal chronology reference data.

Year-name entries are ordered lists of (year_number, fragments) pairs:
ALL listed substrings must appear in the (lower-cased) year-name for a match,
and the FIRST matching entry wins.  More-specific patterns (us2-sa "year
after", a-ra2 "Nth time", multi-toponym campaigns) must therefore precede
their plain base-year counterparts.  A year may appear more than once when
scribes used alternative names for it (e.g. AS3 = "us2-sa Urbilum" or
"throne of Enlil").

Fragments are ASCII ATF (sz for š, etc.) as found in CDLI exports.

Year numbers follow the standard chronology (Sallaberger, OBO 160/3; CDLI
year-name lists).  Formulas attested under more than one king (e.g.
"sza-asz-ru ba-hul" = Šulgi 42 and Amar-Suen 6; "en {d}nanna kar-zi-da
ba-hun" = Šulgi 43 and Amar-Suen 9) are listed under every king that used
them: the resolver treats a king-less match under multiple kings as
ambiguous and leaves the year unresolved rather than guessing.
"""

from typing import Dict, List, Tuple

YearEntry = Tuple[int, List[str]]


_URNAMMA: List[YearEntry] = [
    (1,  ["nanna-e2-a"]),
    (2,  ["ki-en-gi ki-uri"]),
    (5,  ["bad3 uri5{ki}"]),
]

_SZULGI: List[YearEntry] = [
    # -- late-reign campaign cluster (most attested at Drehem) --------------
    (48, ["ha-ar-szi", "ki-masz"]),          # Harši, Kimaš, Hurti in one day
    (48, ["us2-sa", "ki-masz", "a-ra2"]),    # us2-sa Kimaš 2-kam variant
    (47, ["us2-sa", "ki-masz"]),             # year after Kimaš
    (46, ["ki-masz"]),                       # Kimaš & Hurti destroyed
    (28, ["us2-sa", "ha-ar-szi"]),           # year after Harši
    (27, ["ha-ar-szi"]),                     # Harši destroyed
    (45, ["ur-bi2-lum", "kar2-har"]),        # Urbilum-Simurrum-Lulubum-Karhar
    (44, ["si-mu-ru-um", "1(u) la2 1(disz)"]),  # Simurrum+Lulubum 9th time
    (32, ["si-mu-ru-um", "a-ra2 3"]),        # Simurrum 3rd time
    (26, ["si-mu-ru-um", "a-ra2 2"]),        # Simurrum 2nd time
    (26, ["us2-sa", "si-mu-ru-um"]),         # year after Simurrum (variant)
    (25, ["si-mu-ru-um"]),                   # Simurrum destroyed
    (31, ["kar2-har", "a-ra2"]),             # Karhar 2nd (a-ra2 2) time
    (24, ["kar2-har"]),                      # Karhar destroyed
    (35, ["us2-sa", "an-sza-an"]),           # year after Anšan
    (34, ["an-sza-an"]),                     # Anšan destroyed
    # -- construction / cultic years ----------------------------------------
    (38, ["us2-sa", "bad3 ma-da"]),          # year after the wall of the land
    (37, ["bad3 ma-da"]),                    # wall of the land built
    (40, ["us2-sa", "puzur4-isz-{d}da-gan"]),# year after Puzriš-Dagan
    (39, ["puzur4-isz-{d}da-gan"]),          # Puzriš-Dagan (Drehem) built
    (33, ["dingir kalam-ma", "sza-asz-ru"]), # "god of the land" / Šašrum year
    (42, ["sza-asz", "hul"]),                # Šašrum destroyed (also AS6!)
    (43, ["kar-zi-da"]),                     # en of Nanna of Karzida (also AS9!)
    (43, ["en ga-esz"]),                     # Gaeš variant of the same year
    (18, ["en {d}inanna", "ba-hun"]),        # en of Inanna installed
    (3,  ["en {d}inanna", "i3-pa3"]),        # en of Inanna chosen by omen
    (2,  ["szul-gi-iri-mu-sze3"]),           # "my city" year
]

_AMARSUEN: List[YearEntry] = [
    (3, ["us2-sa", "ur-bi2-"]),              # year after Urbilum
    (2, ["ur-bi2-", "hul"]),                 # Urbilum destroyed (verb anchor
                                             # keeps Š45's multi-city campaign,
                                             # verb im-mi-ra, from colliding)
    (3, ["gu-za", "{d}en-lil2"]),            # throne of Enlil fashioned
    (4, ["en-mah-gal-an-na"]),               # en of Nanna installed
    (5, ["en-unu6-gal"]),                    # en of Inanna of Uruk installed
    (7, ["us2-sa", "sza-asz"]),              # year after Šašrum
    (6, ["sza-asz", "hul"]),                 # Šašrum destroyed (also Š42!)
    (7, ["hu-uh2-nu-ri"]),                   # Huhnuri campaign
    (7, ["hu-hu-nu-ri"]),                    # spelling variant
    (8, ["en eridu"]),                       # en of Eridu installed
    (9, ["kar-zi-da"]),                      # en of Nanna of Karzida (also Š43!)
    (9, ["en ga-esz"]),                      # Gaeš variant of the same year
]

_SZUSUEN: List[YearEntry] = [
    (5, ["us2-sa", "bad3 mar-tu"]),          # year after the Martu wall
    (4, ["bad3 mar-tu"]),                    # Martu wall "Muriq-Tidnim" built
    (3, ["us2-sa", "ma2", "{d}en-ki"]),      # year after Enki's boat
    (2, ["ma2-dara3-abzu"]),                 # boat "Ibex of the Abzu" caulked
    (2, ["ma2", "{d}en-ki", "du8"]),         # short form "ma2 {d}en-ki ba-ab-du8"
    (4, ["us2-sa", "si-ma-num2"]),           # year after Simanum
    (3, ["si-ma-num2"]),                     # Simanum destroyed
    (7, ["za-ab-sza-li", "hul"]),            # Zabšali destroyed (IS5 uses tuku)
    (6, ["na-ru2-a"]),                       # great stele erected
    (9, ["us2-sa", "ma2-gur8"]),             # year after the barge
    (8, ["ma2-gur8"]),                       # great barge fashioned
    (9, ["e2 {d}szara2"]),                   # Šara temple at Umma built
]

_IBBISUEN: List[YearEntry] = [
    (2,  ["{d}inanna", "masz-e i3-pa3"]),    # en of Inanna of Uruk chosen
    (5,  ["za-ab-sza-li", "tuku"]),          # governor of Zabšali marriage
    (4,  ["en-am-gal-an-na"]),               # en of Inanna installed
    (15, ["dalla mu-un-na-an-e3"]),          # Nanna manifested himself
    (16, ["nun-me-te-an-na"]),               # "royal ornament of heaven"
]

# Ibbi-Suen formulas that in practice always carry the king's name and whose
# toponyms recur in earlier reigns (Simurrum = Š25/26/32/44; Huhnuri = AS7).
# They are matched only when the king is explicit, never in king-less search,
# so a bare "si-mu-ru-um ba-hul" still resolves to Šulgi 25.
_IBBISUEN_EXPLICIT: List[YearEntry] = [
    (3,  ["si-mu-ru-um", "hul"]),            # Simurrum destroyed
    (9,  ["hu-uh2-nu-ri"]),                  # Huhnuri, bolt of Anšan
]

# King-name detection keys → (canonical name, year table).
KING_YEAR_MAP: Dict[str, Tuple[str, List[YearEntry]]] = {
    "ur-namma":        ("Ur-Namma",   _URNAMMA),
    "ur-{d}namma":     ("Ur-Namma",   _URNAMMA),
    # Šulgi – Unicode and ASCII ATF
    "šul-gi":          ("Šulgi",      _SZULGI),
    "{d}šul-gi":       ("Šulgi",      _SZULGI),
    "šulgi":           ("Šulgi",      _SZULGI),
    "sulgi":           ("Šulgi",      _SZULGI),
    "szul-gi":         ("Šulgi",      _SZULGI),
    "{d}szul-gi":      ("Šulgi",      _SZULGI),
    # Amar-Suen
    "amar-{d}suen":    ("Amar-Suen",  _AMARSUEN),
    "amar-suen":       ("Amar-Suen",  _AMARSUEN),
    # Šu-Suen – Unicode and ASCII ATF
    "šu-{d}suen":      ("Šu-Suen",    _SZUSUEN),
    "šu-suen":         ("Šu-Suen",    _SZUSUEN),
    "szu-{d}suen":     ("Šu-Suen",    _SZUSUEN),
    "szu-suen":        ("Šu-Suen",    _SZUSUEN),
    # Ibbi-Suen
    "ibbi-{d}suen":    ("Ibbi-Suen",  _IBBISUEN_EXPLICIT + _IBBISUEN),
    "ibbi-suen":       ("Ibbi-Suen",  _IBBISUEN_EXPLICIT + _IBBISUEN),
    "ibi-{d}suen":     ("Ibbi-Suen",  _IBBISUEN_EXPLICIT + _IBBISUEN),
    "i-bi2-{d}suen":   ("Ibbi-Suen",  _IBBISUEN_EXPLICIT + _IBBISUEN),
}

# One (canonical, table) pair per king, for king-less year-name search.
KING_TABLES: List[Tuple[str, List[YearEntry]]] = [
    ("Ur-Namma",  _URNAMMA),
    ("Šulgi",     _SZULGI),
    ("Amar-Suen", _AMARSUEN),
    ("Šu-Suen",   _SZUSUEN),
    ("Ibbi-Suen", _IBBISUEN),
]
