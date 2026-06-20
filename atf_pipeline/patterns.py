"""Compiled regular expressions and metrological conversion tables shared by
the extractor mixins.

All extraction patterns live here as class attributes on :class:`ExtractorBase`
so that ``self._RE_*`` / ``cls._RE_*`` resolve through the MRO from any mixin,
and the tables can be reviewed in one place without scrolling through parsing
logic.
"""

import re
from typing import Dict, List


class ExtractorBase:
    """Holds every compiled pattern and conversion table for the extractor."""

    _RE_LINENUM   = re.compile(r"^\d+(?:-\d+)?[a-z]?[!?*'ʼ]?\.\s*(?:[a-z]\.\s*)?")

    # CDLI metrological tokens: integer and fractional coefficients.
    # Unit names can contain an apostrophe (gesz'u = 600-gur), so [\w']+ is used
    # rather than \w+[2']? which would stop at the apostrophe and miss the trailing u.
    _RE_QTY_CDLI  = re.compile(r"(\d+(?:/\d+)?)\(([\w'@]+)\)")
    # Plain numeric quantity ("100 gur", "3.5 sila3").  The negative lookbehind
    # blocks digits that are glued to a letter — Sumerian sign readings carry a
    # trailing index number (e3, du11, ku3, gesz2, KWU147…), and without this a
    # phrase like "sze gesz e3 gur" would be misread as "3 gur".
    _RE_QTY_PLAIN = re.compile(
        r"(?<![A-Za-z])(\d+(?:\.\d+)?)\s+(gur|barig|ban2|sila3?|gin2|ma-na)", re.I
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
    # Pure sexagesimal counter for workers and other non-grain quantities:
    # gesz2 = 60, u = 10, disz = 1 (not multiplied by any grain factor).
    _LABOR_CONV: Dict[str, float] = {
        "szar2":  3600.0,
        "gesz'u":  600.0,
        "gesz2":    60.0,
        "u":        10.0,
        "disz":      1.0,
    }
    # Units that definitively mark a grain/capacity measurement.
    # gesz2/gesz'u/szar2 intentionally excluded: they are generic sexagesimal
    # counting words used for timber pieces, wool mina-groups, area sar-groups,
    # and labor day-groups as well as grain gur-groups.  They only signal grain
    # when a bare gur/sila3 context word OR a smaller grain subunit (asz/barig/ban2)
    # also appears on the same line.
    _GRAIN_IND = frozenset({
        "gur", "barig", "ban2", "sila3", "sila", "asz",
    })

    # Bare unit context words (not in N(unit) format).
    # Allow "[" before the unit — CDLI uses [gur] when the sign is damaged
    # but the reading is certain.  Without this, "[gur]" fails to signal gur
    # context and collapses the whole entry to sila3 scale.
    _RE_BARE_GUR   = re.compile(r"(?:^|\s|\[)gur\b", re.I)
    _RE_BARE_SILA3 = re.compile(r"(?:^|\s|\[)sila3?\b", re.I)
    _RE_BARE_GIN2  = re.compile(r"(?:^|\s|\[)gin2\b", re.I)

    # Animals — require the animal word to be bounded by whitespace (not hyphens),
    # so names like "lugal-amar-ku3" or compounds "gu4-de3" never match.
    _RE_ANIMAL     = re.compile(
        r"(?:(?<=\s)|^)(?:gu4|udu|sila4|masz2?|ansze)(?=\s|$)", re.I
    )
    # Animal count token: N(unit) ANIMAL_WORD — unit must be a simple counting unit,
    # NOT a grain-capacity indicator (asz/barig/ban2/gur/gesz2 won't reach this path
    # because _GRAIN_IND guard fires first).
    _RE_QTY_ANIMAL = re.compile(
        r"(\d+(?:/\d+)?)\((\w+[2']?)\)\s+(?:gu4|udu|sila4|masz2?|ansze)(?=\s|$)", re.I
    )

    # Non-grain commodity markers: when any of these appear on a line, the
    # quantity tokens refer to something other than grain capacity and must
    # not be converted through the grain factor table.
    #   siki       = wool / textile fibre
    #   {gesz}     = wood/tree determinative (e.g. {gesz}ma-nu = ma-nu timber)
    #   sig4       = bricks
    #   ma-na      = mina (weight unit, never a grain unit)
    #   kin sahar  = earthwork / canal-digging (area in sar/gin2, not grain)
    #   esze3/iku/GAN2 = agricultural area units
    _RE_NON_GRAIN = re.compile(
        r"\bsiki\b|\{gesz\}|\bsig4\b|\bma-na\b|\bkin\s+sahar\b"
        r"|\besze3\b|\biku\b|\bGAN2\b"
        r"|\bdug\b"        # dug = vessel/jug — pottery accountability, not liquid measure
        r"|\btu7\b"        # tu7 = soup/broth — liquid inventory, not grain
        r"|\bku6\b"        # ku6 = fish — never a grain context
        r"|\bgu4-gesz\b|\bab2-mah2\b|\bdur3\b|\beme6\b"  # livestock compounds
        r"|\bgu2\b",       # gu2 = talent (60 minas weight); N(asz) gu2 = N talents of
                           # reed/timber/wool — the asz token is NOT a gur here
        re.I,
    )

    # "sze-bi" = "its barley (equivalent)" — an accounting conversion note that
    # follows a processed-product entry (bran, malt) to record the grain value.
    # It is not a separate delivery and must be skipped when collecting entries.
    _RE_SZE_BI = re.compile(r"^sze-bi\b", re.I)

    # Labor/worker-day line indicators — these are NEVER grain quantities
    _RE_LABOR_LINE = re.compile(r"\bgurusz\b|\bgeme2\b", re.I)
    # Labor total: szunigin N gurusz (total worker count)
    _RE_LABOR_TOTAL = re.compile(
        r"s[zž]u-?nigin2?\s+(.*?)\s+gurusz\b", re.I
    )

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
    # esza = eša fine flour; dabin = barley flour; zi3 = generic flour
    _RE_FLOUR  = re.compile(r"\bzi3\b|\bzi3-gu\b|\bdabin\b|\besza\b|\bflour\b", re.I)
    _RE_BREAD  = re.compile(r"\bninda\b|\bbread\b", re.I)
    _RE_BEER   = re.compile(r"\bkasz\b|\bdida\b|\bbeer\b", re.I)
    # i3-gesz/sze-gesz-i3 = sesame oil; i3-szah2 = lard; i3-udu = sheep tallow.
    # All booked here under the fats/oils commodity bucket.
    _RE_OIL    = re.compile(
        r"\bi3-gesz\b|\bsze-gesz-i3\b|\bi3-szah2\b|\bi3-udu\b|\boil\b", re.I
    )
    _RE_SILVER = re.compile(r"\bku3-babbar\b|\bsilver\b", re.I)
    # Operation-description phrases that contain "sze" but are NOT commodity markers:
    # "sze gesz ra(-a)" = threshing, "sze de2-a" = pouring grain, "sze e3" = grain outgo
    # "sze ur5-ra" = grain loan formula
    _RE_OP_DESC = re.compile(
        r"\bsze\s+(?:gesz\s+ra|de2(?:-a)?|e3(?:-a)?|ur5-ra)\b", re.I
    )
    # Per-person rate specifiers at end of distribution lines:
    #   "1(barig)-ta", "sila3-ta", "1(gesz2) 1(u) 5(disz) sila3-ta"
    # The rate encodes how much each worker received; strip it before summing
    # the main quantity to avoid adding 60+ extra sila3 per tablet.
    _RE_RATE_SPEC = re.compile(
        r"(?:\d+(?:/\d+)?\([^)]+\)\s+)*(?:\d+(?:/\d+)?\([^)]+\)|\w+)-ta\b",
        re.I,
    )
    # Ordinal "Nth time/installment": "a-ra2 2(disz)-kam" — the N is never a
    # commodity count, only an installment counter.
    _RE_ARA2_KAM = re.compile(
        r"\ba-ra2\s+\d+(?:/\d+)?\([^)]+\)-kam\b", re.I
    )
    # Commodity/unit keywords stripped when isolating a trailing recipient name
    # on sze gub-ba distribution lines ("1(asz) 1(barig) gur ur-e2-mah")
    _RE_COMM_KW = re.compile(
        r"\b(?:sze|gur|sila3|gin2|barig|ban2|gesz2|asz|gig|ziz2)\b", re.I
    )

    # --------------- Issuer patterns ---------------
    # A/B: ki NAME-ta or ki NAME at line start
    # The ablative -ta is the right edge of the name; anything after it is the
    # debit clause ("ki na-sa6-ta ba-zi" = "expended from Nasa"), so allow — and
    # discard — a trailing verb phrase rather than failing to match it.  The
    # non-greedy (.+?) still stops at the first -ta that is followed by a space
    # or end, so a name carrying an internal -ta- ("in-ta-e3-a-ta") is kept whole.
    _RE_KI_TA    = re.compile(r"^ki#?\s+(.+?)-ta(?:\s+.*)?$")
    # Trailing administrative verb/formula that follows an abbreviated ablative
    # issuer name (pattern B has no -ta to bound the name):
    #   "ki {d}iszkur-illat ba-zi" → issuer is {d}iszkur-illat, ba-zi is the verb.
    # Note: this only strips a verb that trails a *separate* name word; "ki
    # ba-zi-ta" (the person Bazi) is captured by pattern A as "ba-zi" untouched.
    _RE_ISSUER_TRAIL = re.compile(
        r"\s+(?:ba-(?:an-)?zi(?:-ge)?|i3-dab5|in-dab5|s[zž]u\s+ba-ti)\s*$", re.I
    )
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
    # F: NAME szu/šu ba-ti on same line (allow bracket-damage on "an": ba-[an-ti])
    _RE_SHU_BATI  = re.compile(
        r"^(.*?)\s+s[zž]u#?\s+ba-(?:\[?an-\]?|ab-)?ti(?:\s+\S+)?\s*(?:#.*)?$"
    )
    # G: standalone szu/šu ba-ti (allow leading bracket damage like "[szu] ba-ti")
    _RE_SHU_ALONE = re.compile(r"^\[?s[zž]u#?\]?\s+ba-(?:ab-|\[?an-\]?)?ti\s*(?:#.*)?$")
    # H: NAME i3-dab5 / in-dab5 (received); allow bracket damage: i3-[dab5]
    _RE_IDAB5     = re.compile(r"^(.*?)\s+i(?:3-|n-)(?:dab5|\[dab5\])\b")
    # H2: N(asz) NAME – ration list without engar marker (multi-recipient tablet)
    _RE_ASZ_NAME  = re.compile(
        r"^(\d+(?:/\d+)?)\(asz\)\s+([a-z{}\-0-9\[\]]+(?:\s+[a-z{}\-0-9\[\]]+)*?)"
        r"(?:\s*(?:#.*))?$", re.I
    )
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
