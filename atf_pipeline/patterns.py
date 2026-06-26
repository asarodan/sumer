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
    # A whitespace token that *begins* with a CDLI quantity (allowing a leading
    # "[" for bracket damage). Used to find allotment boundaries when splitting a
    # multi-commodity line into separate entries.
    _RE_QTY_TOKEN = re.compile(r"^\[?\d+(?:/\d+)?\([\w'@]+\)")
    # Plain numeric quantity ("100 gur", "3.5 sila3").  The negative lookbehind
    # blocks digits that are glued to a letter — Sumerian sign readings carry a
    # trailing index number (e3, du11, ku3, gesz2, KWU147…), and without this a
    # phrase like "sze gesz e3 gur" would be misread as "3 gur".
    _RE_QTY_PLAIN = re.compile(
        r"(?<![A-Za-z])(\d+(?:\.\d+)?)\s+(gur|barig|ban2|sila3?|gin2|ma-na)", re.I
    )

    # Grain capacity system (sila3 per unit)
    _GRAIN_CONV: Dict[str, float] = {
        "szargal": 216000.0 * 300.0,  # 64,800,000 sila3
        "szar'u":   36000.0 * 300.0,  # 10,800,000 sila3
        "szar2":    3600.0 * 300.0,
        "gesz'u":    600.0 * 300.0,
        "gesz2":      60.0 * 300.0,
        "asz":           300.0,
        "gur":           300.0,
        "barig":          60.0,
        "ban2":           10.0,
        "disz":            1.0,
        "sila3":           1.0,
        "sila":            1.0,
    }
    # Pure sexagesimal counter for workers and other non-grain quantities:
    # gesz2 = 60, u = 10, disz = 1 (not multiplied by any grain factor).
    _LABOR_CONV: Dict[str, float] = {
        "szargal": 216000.0,
        "szar'u":   36000.0,
        "szar2":    3600.0,
        "gesz'u":    600.0,
        "gesz2":      60.0,
        "u":          10.0,
        "disz":        1.0,
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
        r"\bsiki\b|(?<!-)\{gesz\}|\bsig4\b|\bma-na\b|\bkin\s+sahar\b"
        r"|\besze3\b|\biku\b|\bGAN2\b"
        r"|\bdug\b"        # dug = vessel/jug — pottery accountability, not liquid measure
        r"|\btu7\b"        # tu7 = soup/broth — liquid inventory, not grain
        r"|\bku6\b"        # ku6 = fish — never a grain context
        r"|\bgu4-gesz\b|\bab2-mah2\b|\bdur3\b|\beme6\b"  # livestock compounds
        r"|\bgu2(?!\s+i7)\b"   # gu2 = talent (60 minas weight); N(asz) gu2 = N talents of
                               # reed/timber/wool — the asz token is NOT a gur here.
                               # Exception: "gu2 i7" = canal bank (a location), not a weight.
        r"|\bsa\s+gi\b"        # sa gi = bundle(s) of reeds — large sexagesimal counts in
                               # sa gi tablets (szar2/gesz'u scale) are NOT grain gur.
        r"|\bsa\s+szum2\b"     # sa szum2-sikil = bundle(s) of leeks — same counting system
                               # as reed bundles but commodity is vegetables, not grain.
        r"|\ba2-bi\b"          # a2-bi = "its labor (value)" — appears in labor-day total
                               # lines "a2-bi u4 N(szar'u)" where N is days, not grain gur.
        r"|\bgi-bi\b"          # gi-bi = "its reeds" — reed-accounting marker; lines like
                               # "gi-bi 7(szar2) sa" give reed-bundle totals, not grain.
        r"|\bnig2-dag\b"       # nig2-dag = threshing board (carpenter/artisan inventory)
        r"|\bnig2-ki-luh\b"    # nig2-ki-luh = cleaning material / porcupine grass (not grain)
        r"|\bnig2\s+giri3\b"   # nig2 giri3 = "items via [responsible party]" — artisan-delivery
                               # count lines; the large sexagesimal N is an item count, not gur.
        r"|\bnig2-bi\b"        # nig2-bi N-am3 = scribal sub-total check note ("the total for it:
                               # N"); appears in artisan inventory accounts (e.g. Ontario 2, 323).
        r"|\bnig2\s+a-ra2\b"   # nig2 a-ra2 N-kam = "items, Nth delivery installment" — round
                               # counts in multi-delivery artisan accounts, not grain.
        r"|\blagab\b"          # lagab = compressed block/cake shape (garlic cake, bitumen cake);
                               # lagab N counts blocks, never grain-capacity measures.
        r"|\bmuszen\b"         # muszen = bird determinative/classifier; "N(szar2) pa muszen"
                               # = N bird-feathers — a large sexagesimal item count, never grain.
        r"|\bin-nu\b"          # in-nu = straw/thatch — measured in gur in the Ur III system
                               # but is a fodder commodity, NOT grain for human consumption.
        r"|\bbur3\b|\bbur'u\b" # bur3 (= 3 iku) and bur'u (= 10 bur3) are agricultural area
                               # units. Entries like "1(szar2) 2(bur'u) farmer-name" are
                               # field-area sub-entries, not gur-scale grain allocations.
                               # GAN2 (area summary word) is already blocked above; bur3/bur'u
                               # cover continuation lines that omit the GAN2 word.
        r"|(?<!-)\bszum2\b"    # szum2 = garlic/onion commodity; garlic tablets use capacity
                               # units (barig, ban2, sila3, gesz2) identical to grain, causing
                               # false positives when not blocked.  The verb "to give" is always
                               # hyphenated (ba-szum2, mu-szum2), so (?<!-) correctly exempts
                               # verbal conjugations.  Rare personal names starting with szum2-
                               # (e.g. szum2-i-li) will produce false negatives on grain lines,
                               # but this is an acceptable trade-off against the garlic FPs.
        r"|\bza-ha-din\b"      # za-ha-din = shallot/garlic variety (ATF form of Sumerian
                               # za-ha-di-na); "N(szar2) sa za-ha-din N gin2-ta" = bundle
                               # counts of shallots at N silver each — item counts, never grain.
        r"|\bin-bul5\b"        # in-bul5 = coarse thatch grass / reed debris (distinct from
                               # in-nu straw but same non-grain fodder category); appears in
                               # large sexagesimal gur-scale entries in fodder accounts.
        r"|(?<!-)\{u2\}"       # {u2} = plant/herb determinative ({u2}bur2, {u2}gug4, {u2}gil…).
                               # Like {gesz} for wood, a line measuring a plant commodity
                               # uses the same sexagesimal counters as grain but must not be
                               # counted as a grain/silver transaction.
        r"|\bki-la2-bi\b"      # ki-la2-bi = "its tare weight" — a weighing sub-entry giving the
                               # container/packaging weight deducted from a gross total.  These
                               # carry gin2 (shekel) or sar measurements of basket dimensions,
                               # never grain-capacity quantities.
        r"|\bpesz(?:-bi)?\b"   # pesz / pesz-bi = date palm frond; lines like "pesz-bi N gin2
                               # murgu2" give frond-width in shekel/sar units, not grain measures.
        r"|\bim-babbar2\b",    # im-babbar2 = gypsum/plaster; weighed in gin2, never a grain qty.
        re.I,
    )

    # "sze-bi" = "its barley (equivalent)" — an accounting conversion note that
    # follows a processed-product entry (bran, malt) to record the grain value.
    # It is not a separate delivery and must be skipped when collecting entries.
    # Variants caught:
    #   sze-bi            — standard form
    #   sze#-bi / sze!-bi / [sze]-bi  — CDLI damage markers between sze and -bi
    #   sze bala-bi       — "its barley balance equivalent" (field-yield accounts)
    #   sze-numun-bi      — "its seed grain equivalent" (conversion note, not a delivery)
    _RE_SZE_BI = re.compile(
        r"^\[?"               # optional leading restoration bracket
        r"sze"
        r"(?:[#!?]*\]?)"      # optional damage markers + optional closing bracket
        r"(?:-bi\b|-numun[#!?]*-bi\b|\s+bala[#!?]*-bi\b)",
        re.I,
    )

    # Accounting-balance lines: these are RESIDUALS (expected − delivered, or
    # carry-forward subtotals) that are already embedded in the totals above.
    # They must never contribute to a commodity total.
    #   la2-ia3   = deficit / shortfall (expected − delivered)
    #   sza3-bi-ta = "from its subtotal" — carry-forward already counted above
    #   diri       = surplus / excess (standalone at start or end of a quantity line)
    # \[? at line start: accounts for CDLI square-bracket damaged-text restorations.
    _RE_BALANCE_LINE = re.compile(
        r"^\[?la2[#!?]*\]?-\[?ia3\b"  # deficit at line start (handles [la2]-ia3 damage form)
        r"|^\[?sza3[#!?]*\]?-\[?bi[#!?0-9]*\]?-\[?ta[#!?<>\]]*\b"  # carry-forward (all damage forms: sza3-[bi]-ta, sza3-bi3-ta, sza3#-bi-<ta>)
        r"|^\[?diri\b"         # surplus at line start
        r"|\s+diri\s*$"        # surplus trailing a quantity: "N gur diri"
        r"|\bla2-ia3-am3\b"    # "it is the deficit" — copula suffix on total lines
        r"|^\[?sza3\s+sze\b"   # "inner-barley N gur" running-account balance
        r"|\bib2-tak4\b"       # ib2-tak4 = remainder/deficit balance
        r"|\bsu[#!?]*-\[?su\b"   # su-su repayment sub-entry in account tablets
        r"|\bgur-kam\b"        # "it is N gur" copular — debt/rate statement, not a delivery
        r"|^\[?nigin-ba\b"     # grand total ("overall balance") — already counted in szunigin above
        r"|^\(\$\s*blank\s+space\s*\$\)",  # right-indented subtotal on tablet
        re.I,
    )

    # Delivery-tally keyword: mu-kux(DU) = "was delivered into [granary]".
    # When combined with sze-bi (expected yield) and la2-ia3 (deficit), this
    # identifies a yield-balance ledger rather than a transaction tablet.
    _RE_MU_KUX = re.compile(r"\bmu-kux\b", re.I)

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

    # Words that cannot be personal names (checked exact/standalone in _looks_like_name).
    # These are capacity units, animals, raw materials, and commodity words that
    # appear on their own content lines but are never standalone personal names.
    # Compound names containing these syllables (e.g. "udu-ni-ba") are unaffected
    # because the check is an exact-string match, not a substring match.
    _GRAIN_UNIT_WORDS = frozenset({
        # Capacity units
        "gur", "barig", "ban2", "sila3", "sila", "asz",
        "gesz2", "szar2", "ziz2", "gig",
        # Animals / livestock
        "udu", "gu4", "masz2", "sila4", "ansze", "ab2", "amar",
        # Raw materials and commodities
        "i3", "uruda", "zabar", "siki", "na4", "gi", "mun",
        "naga", "ga", "ga-a", "gazi", "lal3", "zu2", "u2",
        "gesz", "ku3", "e2", "ur5", "a2",
        "tug2", "u8", "du8",
        # Grain/crop commodities
        "sze",
        # Accounting/administrative words (never standalone personal names)
        "ma2", "la2", "duh", "ug3", "sar", "ur", "saga", "sza3",
        "lu2", "dumu", "szu", "nig2",
        # Sumerian function words and role nouns (not personal names)
        "u3", "u4", "geme2", "dam",
        # Infrastructure nouns (not personal names)
        "tul2",   # well / water hole
        # Short grammatical/prefix elements never used as standalone personal names
        "nu",     # negation prefix ("not")
        "ba",     # verbal element (allocative)
        "ib2",    # verbal infix / reed basket
        # Administrative verbs that appear before szu ba-ti / i3-dab5 and can be
        # mistaken for a recipient name (e.g. "sa10 szu ba-ti" = "was purchased")
        "sa10",   # to buy/purchase
        "ar3",    # to grind (sa-ad line in grain accounts)
        "igi",    # in front of / witness particle (never standalone personal name)
        # Grain quality qualifiers that appear after commodity words
        # e.g. "N(asz) sze gur sag" where sag = principal/first-quality
        "sag",    # principal / first-quality (grain qualifier)
        # Grain varieties and processing states (appear after sze/gur)
        "munu4",  # malt
        "numun",  # seed grain (sze gur numun = seed barley)
        "sumun",  # old/last-year grain (sze sumun = old barley)
        "szim",   # aromatic/spice (szim gur = a measure of aromatic)
        # Reference formulas (commodity sub-entries)
        "i3-bi",  # "its oil" — sub-entry cross-reference, not a person
        # Grain quality / commodity modifiers
        "du",     # ordinary/common grade (sze du = ordinary barley; kasz du = ordinary beer)
        "har",    # ring/hoop of metal — object, not a person
        "gal",    # large/big (size qualifier: sila3 gal = large sila measure)
        "masz",   # interest / young goat (economic/animal term, not a standalone name)
        # Geographic and contextual terms
        "kur",    # mountain/foreign land (sze kur gur = barley from the highlands)
        "sza",    # heart/inside — function word, not a personal name
        "iri",    # city — geographic term, never a standalone personal name
        "kar",    # quay/harbor — geographic/institutional, not a person
        # Verbal elements and grammatical particles
        "nam",    # destiny/status (nominalized verbal noun, function word)
        "usz",    # 2nd quality (grain grade) or "to follow" — never a name
        "us2",    # to die/follow — function word
        "bi2",    # verbal infix
        "bal",    # to cross/deliver — verbal element in accounting
        "dab",    # to hold/take — verbal element (dab5 subscript dropped)
        "za3",    # side/border — spatial term
        # Livestock subtypes
        "ud5",    # female goat — livestock, not a person
        # Titles that appear standalone only as truncated damage fragments
        "nin",    # Lady/Mistress — title, appears alone only in nin-[...] fragments
        # Weight and container nouns
        "gu2",    # neck/weight unit/tribute — economic term
        "bur",    # deep bowl / area measure — vessel or measure, not a name
        # Verbal elements that appear after quantities
        "sur",    # to drip/press — verbal element in oil/spice accounts
        # Dairy/commodity allocation types (appear after quantities in ration tablets)
        # ga-UD@g in CDLI ATF = a type of milk/dairy allocation; @g modifier stripped
        # to ga-UD which normalizes to ga-ud. ga-ud-bi = "its ga-ud allocation".
        "ga-ud",
        "ga-ud-bi",
        # Administrative and institutional terms
        "nig2-ba",  # gift/allotment — administrative term, never a standalone name
        "ga2-nun",  # storehouse/granary — institution, appears in ga2-nun-ta (from the storehouse)
        # Administrative titles that appear standalone (not as personal names)
        "ensi2",    # governor title — standalone "ensi2" is a role reference, not a personal name
        "sanga",    # temple administrator — "giri3 sanga" = via the temple-administrator (title, not name)
        # Temporal/accounting formulas that appear in ki...ta source lines
        "za3-mu",   # beginning of year — "ki za3-mu-ta" = from the year's beginning (date formula)
        # Geographic/purpose terms extracted via ki...ta or giri3 lines
        "kaskal",   # road/journey — "sze kaskal-sze3" = flour for the road (purpose, not name)
        # Short function words/verbal elements
        "inim",     # word/command — function word, never a standalone personal name
        "tuku",     # to have/possess — verbal element, not a personal name
        # Commodity qualifiers
        "gibil",    # new/fresh — commodity modifier (kasz gibil = new beer)
        # Accounting formula for credit/loan transactions
        "ur5-ra",   # on credit/loan — "sze ur5-ra" = barley on loan (accounting formula, not a name)
        # English translations produced by normalization (should never appear as entities)
        "woman",    # English from TITLE_MAP "munus" → "woman" normalization
        "man",      # English from TITLE_MAP "nita" → "man" normalization
        "field",    # English from "a-sza3" appearing in ki...ta lines (belt-and-suspenders guard)
        # Common Sumerian nouns that appear in ki...ta source lines as location references
        "a-sza3",   # "field/agricultural land" — location noun, not a personal name
        # English role-title translations produced by TITLE_MAP normalization
        # These are job descriptions, not named individuals
        "musician", "carpenter", "fuller", "cloth-fuller", "potter",
        "smith", "barber", "metalworker", "female-worker", "male-worker",
        "leather-worker", "gem-cutter", "miller", "soldier/guard",
        "farmer/field-manager (engar)",
        # Commodity phrase components extracted as false recipients
        "imgaga3",  # salt commodity — "nig2-ar3-ra imgaga3" = ground salt
        "nig2-ar3-ra",  # ground/pounded flour — commodity description, not a name
        "i3-sag",   # fine/first-quality oil — commodity qualifier
        "masz2-bi",  # "its goat count" / interest accounting reference
        # Administrative title genitive forms (not personal names)
        "ensi2-ka",  # "of the governor" — genitive of ensi2; always institutional
        # Livestock subtypes used as false recipients
        "udu-nita",  # "male sheep" — livestock commodity subtype
        # Commodity sub-entry references with possessive
        "esir2-bi",  # "its bitumen" — commodity back-reference in accounts
        # Location/geographic terms appearing in ki...ta source lines
        "a-gar3",   # irrigation district / agricultural plot — location noun
        # Debit/accounting formulae
        "bi2-gu7-bi",  # "was consumed by it" — debit formula, not a person
        # Animal subtypes extracted as false recipients
        "szeg9-bar",  # type of pack animal / donkey — livestock subtype, not a person
        # Administrative accounting terms
        "igi-gal2",   # "what is present/receipts" — accounting category, not a person
        # Commodity possessive back-references (WORD + "-bi" = "its WORD") appearing as false recipients.
        # In Ur III accounts, each commodity sub-entry lists the by-product with the possessive suffix.
        "i3-nun-bi",      # "its ghee/clarified butter"
        "esir2 e2-a-bi",  # "its house bitumen" — bitumen by-product reference
        "igi-gal2-bi",    # "its receipts/counted items"
        "igi-sag-bi",     # "its first/head portion"
        "ga-ar3-bi",      # "its ga-ar3 flour allocation"
        "sag-bi",         # "its principal" (accounting: principal vs. interest)
        "sza3-bi",        # "its interior/midst" — spatial back-reference in accounts
        "duh-bi",         # "its bran" — cereal processing by-product
        "naga-bi",        # "its naga (alkali-plant)" — lye/soap by-product reference
        "ga-bi",          # "its milk" — dairy sub-entry back-reference
        "szu-bi",         # "its hand-allotment" — administrative sub-entry
        # Divine ownership/attribution formulas (temple accounting designations)
        "nanna-kam",      # "it is of Nanna" — attribution to the Nanna moon-god temple
        "nansze-kam",     # "it is of Nanše" — attribution to the Nanše fishing-god temple
        # Bitumen commodity types and sub-entries
        "esir2 e2-a",     # "house bitumen" — commodity (base form, without -bi)
        "esir2 e2-a lugal",  # "royal house bitumen" — royal-grade bitumen commodity
        "esir2 had2",     # "dried bitumen" — dried/solid bitumen variety
        # Processed fat/dairy commodities
        "ga-ar3",         # ghee/clarified butter — processed dairy commodity
        # Iteration counter formula (not a name)
        "a-ra2 -kam",     # "it is the Nth time" — iteration-counting formula in accounts
        # Livestock grades and combinations (commodity descriptions, not names)
        "szah2 niga",     # "first-quality pig" — livestock quality grade
        "szah2 ze2-eh-tur",  # "small pig" — livestock size grade
        "dara3-masz",     # mountain goat / ibex — wild livestock type
        "ansze-edin-na",  # steppe donkey — livestock subtype
        "udu-nita2 sila4 gub",  # "male sheep / standing lamb" — livestock combination
        "masz2-gal masz2",  # "adult goat + young goat" — livestock combination
        "masz2-gal sila4",  # "adult goat + lamb" — livestock combination
        # Malt/grain processing commodity
        "ba-ba munu4",    # "baba-malt" — processed grain product
        # Accounting sub-category
        "igi-gal2 ku3",   # "silver receipts" — accounting sub-category (not a name)
        # Vine/fruit commodities
        "gesztin had2",   # "dried grapes/raisins" — dried fruit commodity
        "a-gesztin-na",   # "grape juice / vine-water" — liquid from grapes
        # Plant/herbal commodity
        "u2-kur",         # "distant plant / herb" — plant commodity (not a personal name)
        # Administrative titles that appear standalone (not attached to a personal name)
        "sukkal-mah",     # "Grand Vizier" — senior administrative role, not a personal name
        "nam-sza3-tam",   # "administrator/manager" — institutional role title
        # Accounting formula for scheduled/regular deliveries
        "sa2-du11",       # "regular delivery/scheduled offering" — accounting category noun
        # Institution nouns extracted as issuers via ki...ta patterns
        "i3-dub",         # "granary" — storage facility, not a person (also in SECTION_LABEL)
        # English translations from TITLE_MAP / INSTITUTION_MAP that leak as entities
        "overseer (ugula)",   # English for ugula — job description, not a named person
        "mill-house",         # English for e2-kikken — institutional building, not a person
        "child/son-of",       # English for dumu — kinship term, not a personal name
        # Administrative source tokens that fire the ki...ta pattern as verbal phrases
        "lugal-sze3 ba-gen-na-a",    # "went to the king's place" — directional verb phrase
        "lugal-sze3 ba-e-re-sza-a",  # "they went to the king's place" — directional verb phrase
        # Agricultural/livestock commodity types (all appear measured by sila3, ban2, or gur)
        "bu-rum",          # agricultural product measured in gur — commodity, not a person
        "zi-bi2-tum",      # grain variety "sze zi-bi2-tum" — commodity
        "kusz gu4 mu",     # "ox hide of year X" — commodity + year-reference phrase
        "masz2-nita2 masz2 gub",  # "male goat + young goat standing" — livestock combination
        "ur-e2-dar-a",     # commodity measured in sila3
        "al-la-ha-ru",     # commodity measured in sila3 (e.g. "fresh al-la-ha-ru")
        "szi-ip-ku",       # commodity measured in sila3/ban2
        # English translations produced by INSTITUTION_MAP normalization
        "granary",         # English for guru7 — storage facility
        "granary-gate",    # English for ka-guru7 — gate/portal
        "royal granary",   # English for gur lugal — royal storage
        "scribe (dub-sar)",    # English for dub-sar — job title
        "village-household",   # English for e2-duru5 — rural settlement building
        # Sumerian institution/building nouns extracted as entities
        "e2-gal",          # "palace/great-house" — institutional building, not a person
        "guru7",           # "granary" — storage facility (source of "granary" false entity)
        "ka-guru7",        # "granary-gate" — gate/portal
        # Administrative title not caught by TITLE_SUFFIX regex
        "sza13-dub-ba",    # "tablet-house official/archivist" — job title, not a name
        # Oil commodity: cedar/juniper oil
        "i3-erin",         # "cedar/juniper oil" — commodity (appears with other oil types)
        # Military/administrative category noun
        "erin2 lugal",     # "royal troops/soldiers" — administrative category, not a person
        # Accounting sub-formulas
        "sza3-ba udu ugu2-bi",  # "in it: sheep, their above-count" — accounting sub-formula
        "szu-nigin2 udu hi-a",  # "total: mixed sheep" — accounting grand-total formula
        # Loading/transport verbal phrases
        "ma2-a si-ga",     # "loaded onto a boat" — verbal phrase for cargo shipment
        # Silver commodity reference
        "ku3-babbar2",     # silver type/standard — commodity not a personal name
        # Geographic/landscape nouns
        "ambar",           # reed-marsh/swampland — geographic/landscape noun
        "sza3-iri",        # "city interior" — spatial/geographic term
        # Livestock type
        "uz-tur",          # "young female donkey" — livestock subtype
        # Grain milling commodity
        "nig2-ar3",        # "ground/milled grain" — commodity (cf. nig2-ar3-ra)
        # Agricultural tools / harvesting context nouns
        "gur10",           # sickle / "gur10{ku6}" (carp fish) — neither is a personal name
        # Boat type used as institutional shorthand
        "ma2-gur8",        # type of ceremonial/cargo boat — not a personal name
        # Verbal/formulaic phrase
        "erin2-me",        # "they are troops" — verbal form of erin2, not a personal name
        # Area measurement formula
        "sahar-bi sar",    # "its soil/dirt: X sar" — area measurement sub-entry
        # Plant seed commodity (za3-hi-li appears with numun "seeds" and {sar} determinative)
        "za3-hi-li",       # aromatic plant — commodity/seed, not a personal name
        # Jar/vessel type used in commodity distribution records
        "udul2",           # type of vessel/jar ("dug udul2") — container, not a person
        # Grain quality grades (premium categories)
        "sag-gal2",        # premium/first-quality grain grade — commodity descriptor
        # Liquid commodity measured in sila3
        "bur-zi",          # liquid commodity in sila3 jars — not a personal name
        # City of Akkad/Agade (geographic proper noun, not a person)
        "a-ga-de3",        # Akkad/Agade — major Mesopotamian city, not a personal name
        # Commodity measured in ban2/gur
        "a-la-pa-nu",      # commodity grade measured in ban2/gur — not a personal name
        # Oil-processing sub-product
        "nig2-i3-de2-a",   # "thing of oil-pouring" — oil processing by-product
        # Spice/incense commodity
        "gu4-ku-ru",       # aromatic/spice commodity (appears with SZIM incense)
        # Commodity measured in sila3
        "pa-li",           # commodity measured in sila3/ban2 — not a personal name
        # Accounting summary/total formulas
        "szu-nigin2",       # "grand total" — accounting summation formula, not a name
        "nigin2-ba gu4",    # "total oxen" — livestock accounting grand total
        # Livestock types (all measured by count, not appearing as named persons)
        "szah2",            # pig — livestock animal
        "gu4-hu-nu",        # "juvenile bull" — young ox, livestock type
        "udu-nita2 sila4",  # "male sheep + lamb" — livestock combination
        "udu-nita2 sila4 ba-ur4",  # "male sheep + shorn lamb" — livestock processing formula
        "kir11 udu",        # "young sheep" — small livestock animal
        "szah2 u2",         # "grass-fed pig" — livestock quality grade
        "asz2-gar3 niga sila4",  # "premium donkey + lamb" — livestock combination
        "asz2-gar3 masz2",  # "donkey + young goat" — livestock combination
        "masz2-nita2 masz2 du",  # "walking male goat + young goat" — livestock combination
        "masz2-gal niga sila4",  # "premium adult goat + lamb" — livestock combination
        # Organ/tissue commodities (animal by-products)
        "mur-gu4",          # "ox lung" — animal organ commodity
        "mur-gu4-bi",       # "its ox lung" — organ back-reference
        # Bitumen types / sub-entries
        "esir2",            # bitumen (base form — commodity, not a person)
        "esir2 su-ba",      # "caulked bitumen" — bitumen processed for caulking
        "esir2 e2",         # "house bitumen" — bitumen for building (cf. esir2 e2-a)
        # Condiment/spice
        "bar-szum",         # "garlic rind/peel" — condiment commodity
        "nu-ur2-ma",        # pomegranate ({gesz} tree-determinative in corpus)
        # Area measurement sub-entry formulas
        "kin-bi sar",       # "its work-area: X sar" — area measurement formula
        "a-sza3-bi sar",    # "its field: X sar" — field area sub-entry formula
        # Administrative role description (not a personal name)
        "sipa ur-gi7",      # "shepherd of the dog-pen" — role description
        "lu2-nin-gir2-su e2-udu",  # "man of Ningirsu, sheep-pen" — role description
        # Material/geographic nouns
        "sahar",            # "soil/dirt/earth" — raw material, not a personal name
        "kar-ra",           # "quay/harbor/merchant district" — geographic noun
        # Quality grade
        "sig15",            # "fine/premium" quality grade — commodity descriptor
        # Variant spelling of already-blocked alkali plant
        "nagga",            # alkali plant (variant spelling of "naga" which is blocked)
        # Commodities measured in sila3
        "da-ri2-sza",       # commodity measured in sila3/ban2
        "ka3-ma-am3-tum",   # commodity measured in sila3
        "nig2-ku5",         # "cut thing" — processed commodity sub-entry
        # Compound accounting formula with historical king name
        "sa2-du11 szul-gi", # "regular delivery (for/of) Shulgi" — accounting category
        # Ox hide commodity variant
        "kusz gu4 u2-hab2", # "ox hide (dyed/treated)" — hide processing commodity
        # Fresh fruit commodity
        "gesztin duru5",    # "fresh grapes" — agricultural commodity
        # Oil allocation formula
        "i3-ba",            # "oil ration/allocation" — commodity distribution term
        # English translations from TITLE_MAP not yet blocked (administrative labor category)
        "male-laborer",     # English for gurusz — workforce category, not a named person
        # English translations from INSTITUTION_MAP not yet blocked
        "sealed-goods-office",  # English for e2-kiszib-ba — administrative building
        "daughter-of",      # English for dumu-munus — kinship term, not a personal name
        "kitchen",          # English for e2-muhaldim — kitchen building
        "cattle-inspector", # English for nu-banda3-gu4 — administrative title
        "household-overseer",  # English for ugula-e2 — supervisory role
        # City/geographic proper nouns leaking as entities
        "nippur",           # City of Nippur — geographic noun
        "umma",             # City of Umma — major Ur III administrative center
        "isin",             # City of Isin — geographic noun
        # Premium fat/butter commodities
        "i3-nun",           # "fine/clarified butter" — fat commodity (measured in gur/sila3)
        "i3-du10-nun-na",   # "sweet noble oil" — premium oil commodity
        # Leather commodity
        "kusz udu",         # "sheep hide/leather" — leather commodity
        # Accounting terms / back-references
        "nig2-gal2-la",     # "what is received/present" — accounting receipt term
        "ma2-bi",           # "its boat" — boat capacity back-reference
        "sza3-ba udu ugu2", # "in it: sheep, above-count" — accounting sub-formula (base form)
        "sza3-ba",          # "in it/within" — accounting inside-reference formula
        "nig2-sa10-bi",     # "its price/value" — silver-equivalent accounting back-reference
        "nig2-ar3-ra-bi",   # "its ground grain" — cereal processing back-reference
        "ba-ba munu4-bi",   # "its ba-ba malt" — malt commodity back-reference
        "kusz gu4 u2-hab2-bi",  # "its dyed ox hide" — hide processing back-reference
        # Building/pen names extracted as issuers via ki...ta
        "e2-masz",          # "goat-house/goat-pen" — livestock facility, not a person
        "e2-kikken-gibil",  # "new mill-house" — building name, not a person
        # Collective noun extracted as issuer
        "sipa-de3-ne",      # "the shepherds" — collective plural, not a named individual
        # Grain type / agricultural estate name extracted as entity
        "ar-za-na",         # "ar-za-na grain" — a specific grain variety measured in gur
        # Akkadian preposition leaked as issuer/recipient
        "a-na",             # Akkadian "to/for" — preposition, not a personal name
        # Collective noun for herdsmen (plural form)
        "unu3-e-ne",        # "the herdsmen" — plural collective noun, not an individual
        # Akkadian fragment mis-extracted as entity
        "im-ma",            # Akkadian "anything/something" — not a Sumerian personal name
        # Grain variety measured in asz volume units
        "dumu-da-ba",       # grain variety measured in asz — commodity, not a person
        # Collective group designation
        "un-sa6-ga",        # "the good/beautiful people" — collective group, not an individual
        # Building / livestock facility names extracted via ki...ta
        "e2-udu",           # "sheep-house/sheep-pen" — livestock facility
        "e2-szu-tum",       # "enclosure/storage facility" — building
        "e2-sag-il2-la",    # "exalted house" — temple/building name
        # Additional building/facility names confirmed as non-persons
        "e2-mah",           # "great house" — appears as building in "from e2-mah" patterns
        "e2-gu4",           # "ox-house/ox-pen" — livestock facility for oxen
        "e2-da-na",         # "his father's house" — building/estate reference
        # False-positive entities confirmed in corpus
        "pi2-hu",           # jar/vessel type ("1(disz) pi2-hu sag10")
        "szukur",           # wooden spear ("{gesz}ma-nu" = manu-wood spear)
        "bappir saga",      # first-quality beer bread commodity
        "en nanna",         # priestly title in year-name formulas
        "en inanna",        # priestly title in year-name formulas
        "tul2-ta",          # cistern/well place name (from ki tul2-ta-ta)
        "bala",             # rotation/turn-of-duty administrative term
        "gesztin",          # wine/grape commodity and place name
        # Batch 19: English translation leakage, commodities, fragments
        "general (šagina)", # English form of šagina military title
        "cook (muhaldim)",  # English form of muhaldim kitchen title
        "lahmah (field)",   # English translation of field name
        "gara2",            # cream/butter dairy commodity
        "sa udu",           # sheep sinew/wool commodity
        "kunga2",           # hybrid equid (donkey-horse)
        "asznan",           # grain goddess {d}asznan — deity, not person
        "banda3",           # "junior" administrative/deity term
        "siskur2",          # ritual offering term
        "kal",              # Akkadian adjective fragment
        "er3",              # name-prefix fragment (er3-zu-dan, er3-re-eb)
        # Batch 20: livestock combos, place names, parsing fragments
        "uru11",            # city name (uru11{ki})
        "gukkal masz2",     # fat-tailed sheep + goat livestock combo
        "gukkal sila4",     # fat-tailed sheep + lamb livestock combo
        "kir11 sila4",      # ewe + lamb livestock combo
        "kir11 masz2",      # ewe + goat livestock combo
        "kid dagal ma2",    # wide reed mat for boat ({gi} determinative)
        "geszimmar tur",    # small date palm ({gesz} determinative)
        "had2",             # "dried" — adjective fragment (siki had2, esir2 had2)
        "esz3",             # sanctuary/shrine — location, not person
        "eme5",             # herding station/geographic unit
        "kad4",             # bundle/tied package (proto-cuneiform KAD4)
        "n gesz",           # damaged-text fragment (n = unknown count + wood)
        "n udu",            # damaged-text fragment (n + sheep)
        "n lugal",          # damaged-text fragment (n + royal)
        "lugal ur5",        # "this/that king" — royal designation phrase
        "szen sza",         # parsing artifact
        "erin2 im nu",      # "troops clay not" — administrative phrase fragment
        "sa2",              # Akkadian adjective "equal/matching"
        # Batch 21: administrative phrases, date formula fragments, Elamite commodity
        "bar-ta gal2-la",   # "outside, available" — administrative status phrase
        "bala-bi",          # "its rotation amount" — accounting term
        "szi-ba-la elam",   # Elamite commodity measured in sila3
        "sa-bi",            # suffix of date formula "mu us2-sa-bi" (year after)
        "sa-a",             # accounting comparison term (al-sa-a = matching)
        "a-ra2",            # name-element fragment (standalone; safe in compounds)
        # Batch 22
        "rib-ba",           # herb/plant ({u2}rib-ba plant determinative); ki rib-ba = location
        "di-ku5-a-ni",      # "his judge" — title phrase in royal inscriptions
        # Batch 23
        "lugal ki-en-gi",   # "King of Sumer" — royal designation
        "lugal ur5-ra",     # "that king" — royal phrase
        "sipa ur",          # herdsman + ur fragment
        "mun-gazi tur-tur", # small aromatic plant
        "kunga2-nita2 mu",  # male equid + year
        "udu-nita2 sila4 du", # livestock description
        "apin-la2-da ba-a", # plow not-available phrase
        "ud-disz-ma ana",   # Akkadian per-day date phrase
        "nigin2-ba masz2",  # accounting total phrase
        "lugal -numun",     # damaged fragment
        "lugal-numun",      # alternate form
        # Batch 24: standalone title plural forms
        "sza3-tam-e-ne",   # "the treasurers" — Sumerian plural of sza3-tam
        "sagi-ne",          # "the cupbearers" — Sumerian plural of sagi
        "ab-ba-iri",        # "city elder" — standalone civic title
        # Batch 25: accounting back-references and -bi possessive forms
        "su3-he2-bi",       # "its fine quality [silver weight]" — accounting notation
        "gu4-apin-na",      # plow oxen (agricultural term, counted in head)
        "gu4-ku-ru-bi",     # aromatic commodity + possessive back-reference
        "igi-bi",           # "its face/equivalent" — accounting reference phrase
        "masz-bi",          # goat/interest + possessive
        "gazi-bi",          # aromatic herb commodity + possessive
        "za3-hi-li-bi",     # za3-hi-li commodity + possessive
        "e2-ur2-bi",        # "its main building" — building back-reference
        "e2-a-lu2-bi",      # house + people + possessive
        "e2-a-lu-bi",       # alternate form
        "lu2-bi",           # "his man/person" — pronoun reference
        "nig2-sa10-am3-bi", # "its purchase price" — accounting
        "a-sza3-bi",        # "its field area" — agricultural accounting
        "szul-gi-kalam-ma-me-te-bi",  # royal epithet phrase
        # Batch 26: all TITLE_MAP English values
        "courier (kas4)", "governor (ensi2)", "secretary (sukkal)",
        "steward (agrig)", "lord/high-priest", "livestock-official (šuš3)",
        "cattle-inspector", "overseer (ugula)", "household-overseer",
        "scribe (dub-sar)", "messenger", "barber",
        "farmer/field-manager (engar)", "leather-worker", "musician",
        "fuller", "smith", "carpenter", "metalworker", "gem-cutter",
        "potter", "cloth-fuller", "miller", "soldier/guard",
        "female-worker", "male-worker", "woman", "man", "male-laborer",
        "sealed-storehouse", "é (household)",
        "menkara (field)", "lahtur (field)",
        # Additional phrase fragments
        "igi-lugal",        # "before the king" — destinatory phrase
        "lugal-kam",        # "it belongs to the king" — royal attribution
        "gesz-i3 lugal",    # "royal sesame oil" — commodity + royal qualifier
        # Batch 27
        "hi-sar",           # plant seed commodity (N sila3 HI-sar)
        "babbar2 hi-sar",   # white hi-sar seed commodity
        "ma-na igi-gal2",   # "1 mina visible" — accounting notation
        "nig2-sar",         # "measured item" — administrative term
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
    # ku3-bi = "its silver (value)" — a silver equivalent note, e.g.
    # "ku3-bi N gin2 M sze" where sze is the barleycorn weight sub-unit.
    _RE_SILVER = re.compile(r"\bku3-babbar\b|\bku3-bi\b|\bsilver\b", re.I)
    # Structural section-divider labels that break commodity carry-forward.
    # When one of these appears without its own commodity keyword, the pending
    # commodity from the previous entry should NOT carry forward to the next
    # quantity line (which belongs to a new sub-section or field category).
    # Examples: GAN2-gu4 (plow-land), e2-duru5 NAME (named settlement),
    # i3-dub (granary), ki-su7 (threshing floor), a-sza3 NAME (named field).
    _RE_SECTION_LABEL = re.compile(
        r"\bGAN2(?:-gu4(?:-suhub2?)?)?\b"   # plow-land categories
        r"|\be2-duru5\b"                     # rural settlements
        r"|\bi3-dub\b"                       # granary
        r"|\bki-su7\b"                       # threshing floor
        r"|\ba-sza3\b"                       # named field
        r"|\bgu2-edin\b"                     # embankment/canal edge
        r"|\bapin-la2\b",                    # plow-fallow land category
        re.I,
    )

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
    _RE_KISZIB        = re.compile(r"^kiszib3#?\s+(.+?)(?:\s+#.*)?$")
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
    _RE_SA2_DU11  = re.compile(r"^sa2-du11\s+(.+?)(?:\s+#.*)?$", re.I)

    # --------------- Field allocation patterns ---------------
    _RE_SZABRA = re.compile(r"^(.+?)\s+s[zž]abra\b")
    _RE_ENGAR  = re.compile(r"^(.*?)\s+engar\b")

    # --------------- Agent ---------------
    _RE_GIRI3  = re.compile(r"^giri3#?\s+(.+?)(?:\s+#.*)?$")
    _RE_UGULA  = re.compile(r"^ugula#?\s+(.+?)(?:\s+#.*)?$")

    # --------------- Parentage (patronymic) ---------------
    # "NAME dumu FATHER" / "NAME dumu-munus FATHER" — child-of formula. Both are
    # single whitespace tokens (Sumerian names are hyphen-joined internally), so
    # capture the token on each side of a standalone "dumu".
    _RE_PATRONYM = re.compile(
        r"(?<![\w-])([a-z0-9{}\[\]_-]{2,})\s+dumu(?:-munus)?\s+([a-z0-9{}\[\]_-]{2,})",
        re.I,
    )
    # Words that follow "dumu" as a status/origin descriptor, not a father's
    # name: dumu lugal = prince, dumu eridu = citizen of Eridu, dumu sza3 e2 =
    # household child, dumu gu4 = plough-team junior, etc.
    _PATRONYM_STOP = frozenset({
        "lugal", "sza3", "e2", "gu4", "munus", "nita", "ki", "eridu",
        "dingir", "uri5", "gir2-su", "umma", "nibru",
    })

    # --------------- Date ---------------
    # Month name group: each word token uses a negative lookahead to stop before
    # a second "iti" keyword (date-range lines like "iti 1-a-kam iti 12-sze3"
    # would otherwise swallow the trailing "iti ..." into the month name).
    _RE_ITI = re.compile(
        r"^(?:\d+[a-z]?[!?*'ʼ]?\.\s*)?iti\s+((?:(?!iti\b)\S)+(?:\s+(?:(?!iti\b)\S)+)*?)"
        r"(?:\s+u4[-\s](\d+)(?:-kam)?)?\s*(?:#.*)?$",
        re.I,
    )
    _RE_MU  = re.compile(
        r"^(?:\d+[a-z]?[!?*'ʼ]?\.\s*)?mu\s+(.+?)(?:\s*#.*)?$", re.I
    )
    _RE_U4  = re.compile(r"\bu4[-\s](\d+)(?:-kam)?\b")

    # --------------- Section boundaries ---------------
    _RE_SZUNIGIN = re.compile(
        r"^\d+[a-z]?[!?*'ʼ]?\.\s*\[?(?:szunigin2?|šunigin2?|szu-nigin2?|šu-nigin2?)\b",
        re.I,
    )

    # Lines that are not personal names
    _RE_NOT_NAME = re.compile(
        r"^\d|^[@$#&]"
        r"|^(?:iti|mu|giri3|ki|ugula|kiszib3|szunigin|šunigin"
        r"|sze-ba|sza3-bi-ta|zi-ga|la2-ia3|nig2-ka9|sag-nig2"
        r"|engar|szabra|šabra|szu-a|sza3-gal"
        r"|nu-banda3|kuruszda|muhaldim|szusz3|dub-sar"
        r"|szuku|kasz)\b"                   # "ration-of" genitive; beer commodity
        r"|^dingir-re-ne\b"                 # "the gods" — deity collective, not a name
        r"|^u4\s"           # date day token (u4 N-kam) — "day N"
        r"|^sze\s"          # commodity formula (sze ur5-ra, sze-ba etc.) — not a name
        r"|^asz\s"          # asz (unit/number) followed by space — not a name start
        r"|^dumu\s+\S",     # "son of NAME" parentage formula (not a standalone name)
        re.I,
    )
    # Receipt/debit/transfer formulae that appear anywhere in a line and prove
    # the whole line is an action clause, not a personal name.
    # Note: bare "ba-zi" is intentionally excluded — it doubles as a personal
    # name (Ba-zi); the debit formula is ba-zi *at end of line* which is already
    # handled by _RE_SHU_ALONE / the prev_name reset logic in extract_structure.
    _RE_ACTION_FORMULA = re.compile(
        r"\bs[zž]u\s+ba-(?:an-)?ti\b"   # szu ba-ti / szu ba-an-ti (received)
        r"|\bi3-dab5\b|\bin-dab5\b"      # i3-dab5 / in-dab5 (received)
        r"|\bba-an-s[zž]um2?\b",         # ba-an-szum2 (given)
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
        r"|aga3-us2|aga-us2|lu2-kin-gi4-a"
        r"|ka-guru7|guru7|i3-dub"
        r"|sanga(?:\s+\S+)?"        # "temple administrator [of DEITY]" — with optional deity
        r"|kuruszda(?:\s+\S+)?"     # "livestock inspector [of DEITY/ESTATE]" — with optional deity
        r"|lukur(?:\s+\S+)?"    # lukur [DEITY] — temple-woman title with optional deity
        r"|gu-za-la2"           # "throne-bearer" — court/administrative title
        r"|zabar-dab5"          # "copper-caster" — craft title
        r"|sza13-dub(?:-ba(?:-ka)?)?" # "tablet-house official" (+ optional -ba[-ka]) — archival title
        r"|ra2?-gaba"           # "horse-attendant/rider" — ra2-gaba or ra-gaba variant
        r"|sagi(?:-\w+)?"       # "cupbearer" (+ optional suffix like -ne plural)
        r"|sza3-tam"            # "treasurer/administrator" — storage official
        r"|gala"                # "lamentation singer" — temple musician title
        r"|ab-ba-iri"           # "city elder" — civic title
        r"|igi-du8"             # "doorkeeper/inspector" — gatekeeper title
        r"|gudu4"               # "purification priest" — cultic title
        r"|dam-gar3"            # "merchant" — trade/commercial title
        r"|unu(?:2|3)?"         # "herdsman" — unu/unu2/unu3 alternate sign readings
        r"|ku3-dim2"            # "goldsmith/silversmith" — metalworking craft title
        r"|sa12-du5"            # "judge" — judicial title
        r"|di-ku5"              # "judge/decision-maker" — alternative judicial title
        r"|szandana"            # "šandana" — administrative official type
        r"|lunga"               # "brewer" — beverage production title
        r"|mar-tu"              # "Amorite" — ethnic label appended to non-Sumerian names
        r"|szabra-e2"           # "house-administrator" — compound steward title
        r"|lu2\s+lunga"         # "man of the brewery" — compound occupation label
        r"|lu2\s+ur3-ra"        # "street sweeper" — compound menial role label
        r"|gala-mah(?:\s+\S+)?" # "chief lamentation singer" + optional temple affiliation
        r"|masz2?-szu-gid2-gid2"  # "dream interpreter/diviner" — masz/masz2 variants
        r"|nimgir"              # "herald/town crier" — administrative messenger title
        r"|szitim"              # "builder/construction worker" — craft title
        r"|sipa\s+gu4"          # "cowherd" — compound herd title
        r"|sipa\s+ansze?"       # "donkey herdsman" — compound herd title (ansze/anse)
        r"|sipa\s+ur-gi7(?:-ra)?"   # "dog keeper" — compound herd title (+ genitive)
        r"|sipa\s+szah2"            # "swine herdsman" — compound herd title
        r"|sipa\s+udu(?:\s+\S+)?"  # "sheep herdsman" (+ optional qualifier)
        r"|i3-du8"              # "gatekeeper/porter" — alternate form of igi-du8
        r"|sipa"                # "shepherd/herdsman" — livestock management title
        r"|szu-ku6"             # "fisherman" — aquatic resource management title
        r"|enku"                # "canal inspector" — water management official
        r"|nu-esz3"             # "temple administrator" — Ur III religious official
        r"|na-gada"             # "herdsman/flock-guard" — livestock guard title
        r"|iszib"               # "libation/anointing priest" — cultic title
        r"|szu-i"               # "barber" — court/craft service title
        r"|a-igi-du8"           # "lookout/inspector" — inspection official title
        r"|tir"                 # "forest [warden]" — occupation label for grove keepers
        r"|agar4-nigin2"        # "storage enclosure/round field" — location suffix after name
        r"|lu2\s+tukul(?:-\S+)?"    # "weapons man/soldier" — occupational suffix
        r"|lu2\s+kin-gi4-a(?:\s+lugal)?"  # "[royal] messenger" — occupational suffix
        r"|ad-kup4"                 # "reed-mat weaver" — craft title
        r"|a-zu"                    # "physician/doctor" — medical title
        r"|giri17-dab5"             # "touching-nose official" — cultic/administrative title
        r"|tur"                     # "junior/young" — age qualifier after name
        r"|min(?:3)?"               # "ditto/same" — accounting notation, not a name component
        r")\s*$",
        re.I,
    )

    _RE_TITLE_PREFIX = re.compile(
        r"^(?:nu-banda3(?:-gu4)?|kuruszda|muhaldim|szusz3|dub-sar"
        r"|lu2-kin-gi4-a|lu2-kinda)\s+",
        re.I,
    )
