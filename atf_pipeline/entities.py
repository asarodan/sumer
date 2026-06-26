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
        # canonical_name → {canonical_father: {"count": int, "tablets": set}}
        self._fathers: Dict[str, Dict[str, Dict]] = {}

    def add_patronymics(self, triples) -> None:
        """Record (name, father, tablet_id) parentage statements, normalising
        both name and father so they match the canonical roster keys. tablet_id
        may be None when source provenance is not tracked."""
        for item in triples:
            name, father = item[0], item[1]
            tablet_id = item[2] if len(item) > 2 else None
            nm = (self._norm.normalize_name(name) if self._norm else name) or name
            fa = (self._norm.normalize_name(father) if self._norm else father) or father
            slot = self._fathers.setdefault(nm, {}).setdefault(
                fa, {"count": 0, "tablets": set()}
            )
            slot["count"] += 1
            if tablet_id is not None:
                slot["tablets"].add(tablet_id)

    @property
    def homonym_count(self) -> int:
        """Number of names attested with two or more distinct fathers."""
        return sum(1 for fa in self._fathers.values() if len(fa) >= 2)

    def export_patronymics_csv(self, filepath: str) -> None:
        """One row per (name, father) parentage edge — the raw material for
        family trees and for disambiguating individuals who share a name.
        is_homonym marks names attested with more than one father."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=[
                "name", "father", "attestations", "tablet_count",
                "is_homonym", "tablets",
            ])
            w.writeheader()
            for name in sorted(self._fathers):
                fathers = self._fathers[name]
                is_homonym = len(fathers) >= 2
                for father, data in sorted(
                    fathers.items(), key=lambda x: -x[1]["count"]
                ):
                    tablets = sorted(data["tablets"])
                    w.writerow({
                        "name":         name,
                        "father":       father,
                        "attestations": data["count"],
                        "tablet_count": len(tablets),
                        "is_homonym":   int(is_homonym),
                        "tablets":      "|".join(tablets),
                    })
        n_edges = sum(len(f) for f in self._fathers.values())
        logger.info("Patronymics: %s (%d name→father edges)", filepath, n_edges)

    # Bare commodity/function words that should never appear as entity names,
    # even after normalization collapses a suffixed form (e.g. "ur-sze3" → "ur").
    _BLOCKLIST = frozenset({
        "gur", "barig", "ban2", "sila3", "sila", "asz", "gesz2", "szar2",
        "udu", "gu4", "masz2", "sila4", "ansze", "ab2", "amar",
        "i3", "uruda", "zabar", "siki", "na4", "gi", "mun", "naga", "ga",
        "gazi", "lal3", "zu2", "u2", "gesz", "ku3", "tug2", "u8", "du8",
        "sze", "ma2", "la2", "duh", "ug3", "sar", "ur", "saga", "sza3",
        "lu2", "dumu", "szu", "nig2", "u3", "u4", "geme2", "dam", "e2",
        "ur5", "a2", "ga-a",
        "tul2", "nu", "ba", "ib2", "sa10", "ar3", "igi", "sag",
        "munu4", "numun", "sumun", "szim", "i3-bi",
        "du", "har", "gal", "masz", "kur", "sza",
        "iri", "kar", "nam", "usz", "us2", "bi2", "bal", "dab", "za3",
        "ud5", "nin", "gu2", "bur", "sur",
        "ga-ud", "ga-ud-bi",
        "nig2-ba", "ga2-nun",
        # Administrative titles (role references, not personal names)
        "ensi2", "sanga",
        # Temporal/geographic/purpose terms from ki...ta or giri3 lines
        "za3-mu", "kaskal",
        # Function words and verbal elements
        "inim", "tuku", "gibil",
        # Accounting formula for credit/loan
        "ur5-ra",
        # English translations produced by normalization
        "woman", "man", "field",
        # Common Sumerian nouns used as location references in ki...ta lines
        "a-sza3",   # "field/agricultural land" — location noun, not a personal name
        # English role-title translations from TITLE_MAP (job descriptions, not named individuals)
        "musician", "carpenter", "fuller", "cloth-fuller", "potter",
        "smith", "barber", "metalworker", "female-worker", "male-worker",
        "leather-worker", "gem-cutter", "miller", "soldier/guard",
        "farmer/field-manager (engar)",
        # Commodity terms extracted as false recipients
        "imgaga3",    # salt commodity
        "nig2-ar3-ra",  # ground flour — commodity description
        "i3-sag",     # fine oil — commodity qualifier
        "masz2-bi",   # "its goat count" accounting reference
        # Administrative title genitive forms
        "ensi2-ka",   # "of the governor" — genitive, not a personal name
        # Livestock commodity subtypes
        "udu-nita",   # "male sheep" — livestock subtype
        # Commodity back-references with possessive suffix
        "esir2-bi",   # "its bitumen" — commodity sub-entry reference
        # Location/geographic terms
        "a-gar3",     # irrigation district / agricultural plot
        # Debit formulae
        "bi2-gu7-bi", # "was consumed by it" — debit/expenditure formula
        # Animal subtypes
        "szeg9-bar",  # type of pack animal — livestock subtype
        # Accounting category terms
        "igi-gal2",   # "receipts/what is present" — accounting category
        # Commodity possessive back-references (WORD + "-bi" = "its WORD")
        "i3-nun-bi", "esir2 e2-a-bi", "igi-gal2-bi", "igi-sag-bi",
        "ga-ar3-bi", "sag-bi", "sza3-bi", "duh-bi", "naga-bi", "ga-bi", "szu-bi",
        # Divine ownership/attribution formulas
        "nanna-kam", "nansze-kam",
        # Bitumen commodity types
        "esir2 e2-a", "esir2 e2-a lugal", "esir2 had2",
        # Processed fat/dairy commodities
        "ga-ar3",
        # Iteration counter formula
        "a-ra2 -kam",
        # Livestock grades and combinations
        "szah2 niga", "szah2 ze2-eh-tur", "dara3-masz", "ansze-edin-na",
        "udu-nita2 sila4 gub", "masz2-gal masz2", "masz2-gal sila4",
        # Malt/grain processing commodity
        "ba-ba munu4",
        # Accounting sub-category
        "igi-gal2 ku3",
        # Vine/fruit commodities
        "gesztin had2", "a-gesztin-na",
        # Plant/herbal commodity
        "u2-kur",
        # Administrative titles appearing standalone
        "sukkal-mah",    # "Grand Vizier" role
        "nam-sza3-tam",  # "administrator/manager" role
        # Accounting formula for regular deliveries
        "sa2-du11",      # "regular delivery/scheduled offering"
        # Institution nouns
        "i3-dub",        # "granary"
        # English translations from TITLE_MAP / INSTITUTION_MAP
        "overseer (ugula)", "mill-house", "child/son-of",
        # Verbal directional phrases mis-extracted via ki...ta pattern
        "lugal-sze3 ba-gen-na-a", "lugal-sze3 ba-e-re-sza-a",
        # Agricultural/livestock commodity types (all appear measured by volume units)
        "bu-rum", "zi-bi2-tum", "kusz gu4 mu",
        "masz2-nita2 masz2 gub", "ur-e2-dar-a", "al-la-ha-ru", "szi-ip-ku",
        # English translations from INSTITUTION_MAP
        "granary", "granary-gate", "royal granary",
        "scribe (dub-sar)", "village-household",
        # Sumerian institution/building nouns
        "e2-gal",        # palace/great-house
        "guru7",         # granary (source of "granary" English entity)
        "ka-guru7",      # granary-gate
        # Administrative title (archivist role)
        "sza13-dub-ba",
        # Oil commodity
        "i3-erin",         # cedar/juniper oil
        # Military/administrative category noun
        "erin2 lugal",     # royal troops
        # Accounting sub-formulas
        "sza3-ba udu ugu2-bi", "szu-nigin2 udu hi-a",
        # Transport verbal phrase
        "ma2-a si-ga",     # "loaded onto a boat"
        # Silver commodity
        "ku3-babbar2",
        # Geographic/landscape nouns
        "ambar", "sza3-iri",
        # Livestock
        "uz-tur",          # young female donkey
        # Grain commodity
        "nig2-ar3",
        # Agricultural/fishing nouns (not personal names)
        "gur10", "ma2-gur8",
        # Verbal form
        "erin2-me",
        # Area measurement formula
        "sahar-bi sar",
        # Plant seed / aromatic commodity
        "za3-hi-li",       # aromatic plant (with {sar} determinative in corpus)
        # Vessel/jar type
        "udul2",
        # Grain quality grade
        "sag-gal2",
        # Liquid commodity
        "bur-zi",
        # City of Akkad (geographic proper noun)
        "a-ga-de3",
        # Commodity grades / aromatics
        "a-la-pa-nu", "nig2-i3-de2-a", "gu4-ku-ru", "pa-li",
        # Accounting summary formulas
        "szu-nigin2", "nigin2-ba gu4",
        # Livestock types
        "szah2", "gu4-hu-nu", "udu-nita2 sila4", "udu-nita2 sila4 ba-ur4",
        "kir11 udu", "szah2 u2",
        "asz2-gar3 niga sila4", "asz2-gar3 masz2",
        "masz2-nita2 masz2 du", "masz2-gal niga sila4",
        # Animal organ commodities
        "mur-gu4", "mur-gu4-bi",
        # Bitumen types
        "esir2", "esir2 su-ba", "esir2 e2",
        # Condiments / plant commodities
        "bar-szum", "nu-ur2-ma",
        # Area measurement formulas
        "kin-bi sar", "a-sza3-bi sar",
        # Administrative role descriptions
        "sipa ur-gi7", "lu2-nin-gir2-su e2-udu",
        # Material / geographic nouns
        "sahar", "kar-ra",
        # Quality grade
        "sig15",
        # Alkali plant variant
        "nagga",
        # Commodities measured in sila3
        "da-ri2-sza", "ka3-ma-am3-tum", "nig2-ku5",
        # Accounting formula with king name
        "sa2-du11 szul-gi",
        # Hide and fruit commodities
        "kusz gu4 u2-hab2", "gesztin duru5",
        # Oil allocation term
        "i3-ba",
        # English TITLE_MAP translations not yet blocked
        "male-laborer",     # gurusz
        # English INSTITUTION_MAP translations not yet blocked
        "sealed-goods-office", "daughter-of", "kitchen",
        "cattle-inspector", "household-overseer",
        # City/geographic proper nouns (normalized to lowercase)
        "nippur", "umma", "isin",
        # Premium fat/butter and oil commodities
        "i3-nun", "i3-du10-nun-na",
        # Leather commodity
        "kusz udu",
        # Accounting terms and back-references
        "nig2-gal2-la", "ma2-bi", "sza3-ba udu ugu2", "sza3-ba",
        "nig2-sa10-bi", "nig2-ar3-ra-bi", "ba-ba munu4-bi",
        "kusz gu4 u2-hab2-bi",
        # Building names extracted as issuers
        "e2-masz",           # goat-house/pen
        "e2-kikken-gibil",   # new mill-house
        # Collective noun
        "sipa-de3-ne",       # "the shepherds" (plural)
        # Grain type / agricultural estate
        "ar-za-na",          # ar-za-na grain variety
        # Akkadian preposition
        "a-na",              # Akkadian "to/for" — preposition
        # Collective herdsmen noun
        "unu3-e-ne",         # "the herdsmen" (plural)
        # Akkadian fragment
        "im-ma",
        # Grain variety measured in asz
        "dumu-da-ba",
        # Collective group designation
        "un-sa6-ga",
        # Building / livestock facility names
        "e2-udu", "e2-szu-tum", "e2-sag-il2-la",
        "e2-mah",        # "great house" — building
        "e2-gu4",        # "ox-house" — livestock facility
        "e2-da-na",      # "his father's house" — estate
        # Confirmed false positives
        "pi2-hu",        # jar/vessel type
        "szukur",        # wooden spear commodity
        "bappir saga",   # first-quality beer bread
        "en nanna",      # priestly title in year-name formulas
        "en inanna",     # priestly title in year-name formulas
        "tul2-ta",       # cistern/well place name
        "bala",          # rotation/turn-of-duty term
        "gesztin",       # wine/grape commodity and place name
        # Batch 19
        "general (šagina)", "cook (muhaldim)", "lahmah (field)",
        "gara2",         # cream/butter
        "sa udu",        # sheep sinew
        "kunga2",        # hybrid equid
        "asznan",        # grain goddess, not person
        "banda3",        # administrative/deity term
        "siskur2",       # ritual offering
        "kal",           # Akkadian adjective fragment
        "er3",           # name-prefix fragment
        # Batch 20
        "uru11",         # city name
        "gukkal masz2", "gukkal sila4",   # livestock combos
        "kir11 sila4",  "kir11 masz2",   # ewe + lamb/goat
        "kid dagal ma2",  # reed mat for boat
        "geszimmar tur",  # small date palm
        "had2",           # "dried" adjective fragment
        "esz3",           # sanctuary/shrine
        "eme5",           # herding station
        "kad4",           # bundle
        "n gesz", "n udu", "n lugal",  # damaged-text fragments
        "lugal ur5",      # royal designation phrase
        "szen sza",       # parsing artifact
        "erin2 im nu",    # administrative phrase fragment
        "sa2",            # Akkadian adjective
        # Batch 21
        "bar-ta gal2-la", # administrative status phrase
        "bala-bi",        # accounting rotation term
        "szi-ba-la elam", # Elamite commodity
        "sa-bi",          # date formula fragment
        "sa-a",           # accounting comparison term
        "a-ra2",          # name-element extracted as standalone fragment
        # Batch 22
        "rib-ba",         # herb ({u2}rib-ba plant determinative)
        "di-ku5-a-ni",    # "his judge" title phrase in royal inscriptions
        # Batch 23: English-translated title forms and multi-word false positives
        "estate-administrator (šabra)",  # normalized form of szabra title compound
        "inspector (nu-banda3)",         # normalized form of nu-banda3 compound
        "lugal ki-en-gi",  # "King of Sumer" — royal designation, not person
        "lugal ur5-ra",    # "that king" — royal designation phrase
        "sipa ur",         # "herdsman ur" — title + fragment
        "mun-gazi tur-tur",  # small aromatic plant
        "kunga2-nita2 mu",   # male equid + year notation
        "udu-nita2 sila4 du",  # livestock description phrase
        "apin-la2-da ba-a",    # "plow not-available" status phrase
        "ud-disz-ma ana",      # Akkadian date/per-day phrase
        "nigin2-ba masz2",     # "their total goats" accounting phrase
        "lugal -numun",        # damaged fragment
        "lugal-numun",         # alternate form
        # Batch 24
        "sza3-tam-e-ne",   # "the treasurers" plural
        "sagi-ne",         # "the cupbearers" plural
        "ab-ba-iri",       # city elder civic title
        # Batch 25
        "su3-he2-bi",      # fine silver accounting notation
        "gu4-apin-na",     # plow oxen
        "gu4-ku-ru-bi",    # aromatic commodity back-reference
        "igi-bi",          # "its equivalent" accounting phrase
        "masz-bi", "gazi-bi", "za3-hi-li-bi",  # commodity + possessive
        "e2-ur2-bi", "e2-a-lu2-bi", "e2-a-lu-bi",  # building back-references
        "lu2-bi",          # pronoun reference
        "nig2-sa10-am3-bi", "a-sza3-bi",  # accounting back-references
        "szul-gi-kalam-ma-me-te-bi",  # royal epithet phrase
        # Batch 26: all TITLE_MAP English values — block every normalized title form
        "courier (kas4)", "governor (ensi2)", "secretary (sukkal)",
        "steward (agrig)", "lord/high-priest", "livestock-official (šuš3)",
        "cattle-inspector", "overseer (ugula)", "household-overseer",
        "scribe (dub-sar)", "messenger", "barber",
        "farmer/field-manager (engar)", "leather-worker", "musician",
        "fuller", "smith", "carpenter", "metalworker", "gem-cutter",
        "potter", "cloth-fuller", "miller", "soldier/guard",
        "female-worker", "male-worker", "woman", "man", "male-laborer",
        # INSTITUTION_MAP English values that are not legitimate institutional actors
        "sealed-storehouse", "é (household)",
        "menkara (field)", "lahtur (field)",
        "igi-lugal",        # "before the king" phrase
        "lugal-kam",        # "it belongs to the king" phrase
        "gesz-i3 lugal",    # "royal sesame oil" commodity phrase
        # Batch 27
        "hi-sar",          # plant seed commodity
        "babbar2 hi-sar",  # white hi-sar seed
        "ma-na igi-gal2",  # accounting notation
        "nig2-sar",        # measured item term
        # Batch 29: possessive back-references (WORD + "-bi" = "its WORD")
        # All of these have 0 fathers and appear only in recipient/accounting roles
        "udu-bi",          # "its sheep"
        "a2-bi",           # "its wages/labor value"
        "gesz-i3-bi",      # "its sesame oil"
        "nagga-bi",        # "its nagga alkali"
        "lugal-bi",        # "its king" — attribution phrase
        "u4-bi",           # "its day"
        "ensi2-ka-bi",     # "of its governor" — genitive back-reference
        "geme2-bi",        # "its female worker"
        "mur-bi",          # "its interior/lung"
        "zu2-bi",          # "its ivory/tooth"
        "mun-bi",          # "its salt"
        "a-ab-ba-bi",      # "its sea/ocean"
        "gesz-bi",         # "its tree/wood"
        "kar-bi",          # "its quay/harbor"
        "u2-kur-bi",       # "its u2-kur plant"
        "a-ra2-ni-bi",     # "its N-th installment"
        "du-bi",           # "its du (ordinary/regular)" — grade back-reference
        "ba-ba munu3-bi",  # malt-porridge back-reference (variant of ba-ba munu4-bi)
        # Batch 30: collective plural role terms (not individual names)
        # -mesz = Akkadian plural marker; -ne/-e-ne = Sumerian ergative plural
        "mar-tu-mesz",     # "Amorites" — collective ethnic plural
        "aga-us2-mesz",    # "soldiers" — collective military plural
        "dam-gar3-ne",     # "the merchants" — collective occupational plural
        "sipa-e-ne",       # "the shepherds" — collective occupational plural
        "sipa-ne",         # "the shepherds" — alternate plural form
        "masz-masz-e-ne",  # "the diviners/exorcists" — collective plural
        "simug-ne",        # "the smiths" — collective craft plural
        "aga3-us2-ne",     # "the soldiers" — alternate collective plural
        "szandana-ne",     # "the szandana officials" — collective administrative plural
        "unu3-de3-ne",     # "the herdsmen" — collective occupational plural
        "mar-tu-ne",       # "the Amorites" — alternate collective ethnic plural
        # Accounting formula fragments extracted as false entities
        "i3-dab5",         # "it was received" — verbal receipt formula
        "giri3 szesz-kal-la",  # "via Szesz-kalla" — transport agent notation
        "ki lugal-e2-mah-e",   # "from Lugal-e2-mah-e" — source location notation
        "szu-nigin2-nigin2",   # "total total" — accounting summary formula
        "nig2-gur11-ra-kam",   # "it is the property" — accounting formula
        "nig2-gur11-ra-ni",    # "his property" — accounting phrase
        # Administrative phrase fragments
        "a2-na erin2 e2-sukkal",  # "wages of workers of the sukkal-house"
        "erin2 he2-dab5",         # "workers to be seized" — administrative directive
        "lu2-dab5-ba ga2-nun gesz-ka gub-ba",  # "arrested man stationed at timber storehouse"
        "sa10-am3 ansze",         # "purchased donkeys" — transaction phrase
        "kusz gu4",               # "ox hide" — commodity compound
        "u6-di kalam-ma-ka",      # "inspection of the land" — administrative phrase
        "gesz-gid2 szu",          # "under authority of the long staff" — administrative
        "i-di lu2 hun-ga2",       # "wages of the hired man" — labor phrase
        "ge6-par4 had2",          # "dried cloister goods" — commodity phrase
        "asz2-gar3 sila4",        # "lamb of the asz2-gar3 type" — livestock phrase
        "nigin2-ba udu",          # "total sheep" — livestock accounting total
        "nig2-sa10 uruda",        # "copper purchase price" — commercial phrase
        "sa2-sag hu-ul-hu-ul",    # "joy inspection" or Akkadian phrase — administrative
        "ur3-re-ba-du7 szu-gi4",  # "szu-gi4 returned" — transaction formula + name
        "du-szu -a",              # name fragment with trailing grammatical suffix
        "dusu2-nita2 mu",         # "male basket-carrier, year..." — phrase fragment
        "ba-ba saga",             # "first-quality porridge" — commodity
        "gukkal udu a-lum",       # "fat-tailed sheep, ordinary sheep, a-lum type" — livestock
        "dumu-mesz e2",           # "sons of the house" — institutional/collective phrase
        "zi dub-dub",             # accounting disbursement formula
        "geme2-bi u4",            # "its female worker, day..." — back-reference phrase
        "me udu hi-a",            # "various sheep entries" — livestock accounting
        "haszhur duru5",          # "fresh apple" — fruit commodity compound
        "sa imgaga3",             # "bundle of salt" — commodity compound
        "lugal-sze3 ba-de6",      # "was taken to the king" — transfer phrase
        "lugal zabar gar-ra",     # "king wearing bronze" — royal epithet phrase
        "lugal sumun",            # "old king" or "old barley" phrase — not a personal name
        "sanga ba-gara2",         # "temple administrator of Ba-gara2" — institutional role
        "sanga nin-szubur",       # "temple administrator of Nin-szubur" — institutional role
        "li2-iq-tum al-la-ha-ru", # two Akkadian names merged without conjunction
        "ni2 dub2-bu-da-ni",      # "his own trembling" — psychological/literary phrase
        # Batch 31: livestock/animal age phrases
        "sipa ansze",             # "donkey shepherd" — standalone role phrase
        "sipa ur-ra",             # "shepherd of the dog/team" — role phrase
        "gukkal niga sila4",      # fat-tailed sheep + prime + lamb
        "masz2-gal u2 sila4",     # large goat + plant + lamb
        "udu-gal udu lugud2-da",  # large sheep + small sheep
        "niga sila4",             # prime lamb — livestock grade phrase
        "udu-nita2 masz2",        # ewe + goat — livestock combination
        "udu-nita2 sila4 ga",     # suckling lamb phrase
        "masz2-nita2 masz2 sza3-du10",  # male goat types
        "nigin2-ba gu4 ab2 hi-a", # total cattle count
        "udu-gal sila4 udu-gal",  # sheep size pair
        "n udu niga",             # [n] prime sheep (damaged count placeholder)
        "n ab2 mu",               # [n] mature cows (damaged count placeholder)
        "dusu2-munus mu",         # female basket-carrier + year (age notation)
        "lulim-munus mu",         # female deer + year (age notation)
        "kunga2-munus mu",        # female mule + year (age notation)
        # Batch 31: administrative formula phrases
        "dab-ba a2 erin2-na-ka",  # "hired workers' wages" (genitive) — labor formula
        "dab-ba a2 erin2-na",     # "hired workers' wages" — labor formula
        "nag lugal",              # "drink of the king" — offering formula
        "nig2-sa10 gi",           # "price of reeds" — commodity phrase
        "e2-a si-ga",             # "placed in the house" — administrative formula
        "i7 pa-e3",               # "canal clearance" — water management phrase
        "sa10-am3 esir2 e2-a",    # "purchase of bitumen (for house)" — commercial phrase
        "kusz ab2 mu",            # "hide of cow, year" — commodity + year phrase
        "al-la erin2",            # "labor clearance/levying of workers"
        "lugal erin2-na",         # "king's troops" — military phrase
        "al-la erin2 esz3 didli", # "labor clearing from various depots"
        "gun an-na",              # "tribute of the sky/Anu" — offering formula
        "lu2-dab5-ba en-nu",      # "arrested man, night watch" — security phrase
        "mun-gazi hi-a",          # "mixed mun-gazi spices" — condiment phrase
        "bappir2 du",             # "ordinary beer bread" — commodity phrase
        "bappir2 lugal",          # "royal beer bread" — commodity phrase
        "sig5 du",                # "good + ordinary" — quality phrase
        "ma2-lah5 lugal",         # "royal boatman" — role phrase (no personal name)
        "lugal zabar",            # "bronze king" — royal epithet/formula
        "an inanna",              # two deities listed together (not a person)
        "an-na a-na",             # Anu + Akkadian preposition fragment
        "su-ga ur-lamma",         # "returned [goods] to ur-lamma" — accounting verb + name
        "usz2 lu2-bala-sa6-ga",   # "died, the-turncoat" — death record formula
        "usz2 ur-ba-ba6",         # "died, ur-ba-ba6" — death record formula
        "muszen-na-sze3 du-ni",   # "it went to the birds" — dispersal phrase
        "ugu2 lu2-du10-ga",       # "above/for the good man" — allocation phrase
        "mur gu4-re nu",          # "ox lung not [accepted]" — quality rejection phrase
        "muszen-du3 sa2-du11",    # "bird catcher's regular delivery" — supply formula
        "kusz3 sukud",            # "height/length measure" — measurement phrase
        "in mu",                  # damaged/uncertain fragment
        "gir2 an",                # "dagger of Anu" — votive phrase
        "in u4",                  # "chaff/straw, day" — commodity fragment
        "sa gu",                  # "sinew/bundle of neck" — commodity phrase
        "za-gin3 1-a",            # "first-quality lapis lazuli" — gem grade phrase
        "zi-ge duh-hu-um",        # grain + Akkadian term fragment
        "me a-gar3",              # "divine powers of the field" — ritual phrase
        "asz-a ki",               # location/field fragment
        "u2-nu-ut ansze",         # "donkey equipment" — equipment phrase
        "ab mah2",                # "large/old cow" — livestock description
        "gesz-gar um-mi",         # "beam of the craftsman" — craft material phrase
        "mi-ri2-za ma2",          # "boat of mi-ri2-za" — commodity + location
        "u3-hu-in lugal",         # Elamite name + royal title (title not a name)
        "ru-ba-ti er2-du8",       # Elamite compound designation
        "a-bi2-si2-im-ti nin",    # Elamite queen Abisimti + title nin — not personal name
        "sanga nin-gir2-su",      # "temple administrator of Ningirsu" — institutional role
        # Batch 31: Elamite/ethnic designations
        "elam za-ul-me",          # Elamite ethnic designation
        "elam du8-du8-li2-me",    # Elamite ethnic designation
        "ad-da elam",             # "father [from] Elam" — ethnic reference
        # Batch 31: Akkadian formula fragments
        "as,-bat ansze kur-ba-ni sza a-ba-ri",  # Akkadian property clause
        "ta-ri-bu-um sza lugal",  # Akkadian name + royal possessive
        "kar3-szum szu-szi an-dah-szum",  # Akkadian name sequence
        # Batch 31: additional commodity/accounting fragments
        "lu2-nin-szubur munu4-mu2",  # name + sprouted malt commodity — false extraction
        "szesz-szesz iszib",         # "many brothers, libation priest" — role phrase
        "gudu4 nun-gal",             # "great purification priest" — title compound
        "gudu4 gu-la",               # "great purification priest" — title compound
        # Batch 32: livestock, commodity, and accounting phrase false extractions
        "ba-ba munu4 saga",          # "first-quality malt porridge" — commodity quality phrase
        "haszhur had2",              # "dried apple" — fruit commodity
        "ur5-sze3 masz2",            # "goats for that [purpose]" — accounting phrase
        "inim-szara2 ga",            # "decree of Szara + milk" — administrative phrase
        "usz-bar-sze3 gen-na",       # "went for weaving" — verbal administrative phrase
        "ba-ri2-ga gesz e3-a",       # "ba-ri2-ga wood that came out" — material phrase
        "nigin2-ba udu hi-a",        # "total various sheep" — livestock accounting total
        "sza3-ga-du3 gada kug-bi masz",  # complex commodity phrase
        "ku-ta-ni ansze",            # "donkey [of/named] ku-ta-ni" — commodity phrase
        "al ak",                     # "hoe work" — agricultural labor phrase
        "ma-szum e2-a",              # Akkadian name + location phrase
        # Batch 32: geographic/institutional phrases
        "a-ga2-la2 kesz2-ra2",       # "of the canal, of Kish" — geographic reference
        "nin-hur-sag gu-la",         # "the great Ninhursag" — deity epithet
        "gu-za ur-namma",            # "throne of Ur-Namma" — royal attribute phrase
        "lu2-eb-gal ad-kup4",        # "Ebgal building, reed-mat-weaver" — institutional phrase
        # Batch 32: verbal/accounting phrase false extractions
        "su-ga lu2-nin-gir2-su",     # "returned [goods], man of Ningirsu" — accounting verb + person
        "lu2-igi-ma-sze3 u2-du-lu",  # complex administrative phrase
        "sa6-a-ga lu2 kin-gi4-a lugal",  # "good, royal messenger" — role phrase
        # Batch 32: uncertain compounds (all have 0 confirmed fathers)
        "puzur4 esz18-dar",          # uncertain compound — no patronymics
        "ku-ul-ti sipa ur",          # "ku-ul-ti, shepherd, ur" — role phrase fragments
        "lu2-ba-li2-it, sipa ur",    # name + shepherd + ur fragment
        "ur-mes tur",                # "the young ur-mes" — age adjective phrase
        # Batch 32: later Babylonian/Akkadian formula fragments (OB/post-Ur-III)
        "qa-bal-ti kur-ia ansze-gam-mal ina ina kas-pi",  # OB Akkadian property clause
        "suen lugal dingir-mesz sza2 an-e",  # Suen royal title from later period
        "ta-ab-li-it-ti gu4 gesz",   # OB Akkadian compound phrase
        "marduk-mu-sza-lim a-bi erin2",  # OB Akkadian name + military title
        "kar3-szum bu-ra-szum",      # two Akkadian names merged (no conjunction)
        # Batch 33: sanga/kuruszda deity-affiliation phrases as standalone entities
        "sanga nansze",              # "temple administrator of Nanshe" — institutional role
        "sanga szul-gi",             # "temple administrator of Shulgi" — institutional role
        # Batch 33: livestock and commodity phrases
        "kunga2-nita2-gesz mu",      # male equid + year (age notation)
        "lulim udu",                 # "deer + sheep" — livestock combination
        "sipa udu kur-ra",           # "shepherd of mountain sheep" — role phrase
        "gukkal gesz-du3 udu a-lum", # "fat-tailed + ordinary + a-lum sheep" — livestock
        "masz2-gal niga udu",        # "large prime goat + sheep" — livestock combo
        "udu-gal u8 udu lugud2-da",  # "large sheep + ewe + small sheep"
        "udu-nita2 sza3-ba udu ugu2-bi",  # sheep accounting back-reference
        "nigin2-ba la2 udu",         # "total deficit sheep" — accounting phrase
        "ar3-ra udu",                # sheep phrase
        "bir3 kunga2 lugal",         # "royal equid" — livestock phrase
        "gu4-numun hun-ga2",         # "hired plow-oxen" — labor phrase
        "asz2-gar3 udu hur-sag",     # "mountain sheep of asz2-gar3 type" — livestock
        "gukkal gesz-du3 sila4",     # "fat-tailed sheep + lamb" — livestock combo
        "sipa udu gukkal",           # "shepherd of fat-tailed sheep" — role phrase
        # Batch 33: administrative/accounting formula false extractions
        "gi-zi ha",                  # fresh reed + ha — commodity phrase
        "lugal sza3-gal",            # "king's choice grain" — commodity phrase
        "ur-sila-luh ga",            # milk phrase
        "sila-a gal2-la",            # "available in the sila" — inventory phrase
        "mur diri gu4-e gu7-a",      # "excess lung eaten by the ox" — waste phrase
        "gi-a sa10-a",               # "sold for it" — transaction phrase
        "nig2-gu7 lu2 mar-za",       # "food of the mar-za festival man" — ritual phrase
        "nig2-szum2-a szu-a",        # "taken for distribution" — accounting phrase
        "nig2-szum2 e2-u4",          # "distribution of the day-house" — administrative
        "diri de6-a",                # "brought [as] surplus" — accounting phrase
        "a ur4",                     # "labor of shearing" — task phrase
        "lugal esir2 e2-a",          # "king's bitumen for house" — commodity phrase
        "igi-szara2-sze3 giri17-dab5",  # "before Szara, giri17-dab5" — ritual phrase
        "ugu2 ku5-da-mu ba-a-gar",   # "above, ku5-da-mu was placed" — administrative
        "amar-du3 gub-ba",           # "amar-du3 stationed" — personnel status phrase
        "lugal ur-lamma",            # "the king, ur-lamma" — disambiguation phrase
        "nu-kiri6 gesz gal",         # "gardener of the great tree" — role phrase
        "ensi2-sze3 gen-na",         # "gone to the governor" — movement phrase
        "gesz-i3-sze3 gen-na",       # "gone for sesame oil" — movement phrase
        "murgu2 ki-mun",             # "back of ki-mun" — body part + location
        "a-da-lal3 aga3-us2-gal",    # place/institution + soldier
        "uru4-a a-sza3 egir-a-suhur",  # "sown field behind the ditch" — agricultural phrase
        "nig2-diri ezem-ma",         # "festival surplus" — accounting phrase
        "sa10-bi ku3",               # "its silver price" — accounting back-reference
        "an-na gal-gal",             # "very great [sky god]" — divine epithet
        "ma-na ku3",                 # "mana of silver" — weight + metal commodity
        "u2-da ni",                  # plant fragment
        "bappir2 saga lugal",        # "royal first-quality beer bread" — commodity phrase
        "ad-da sa12-du5 nansze",     # "father, judge of Nanshe" — compound title phrase
        "ab-su13 sar-da",            # uncertain compound — 0 confirmed fathers
        "kusz u2-hab2",              # "u2-hab2 leather" — leather commodity type
        "hu-wa-wa tum3-da",          # "Huwawa, bring [it]" — mythological reference
        "szah2-gesz-gi-nita2 gal",   # "large male reed-thicket boar" — livestock phrase
        "gu4-numun lu2-nin-szubur",  # "plow-oxen of lu2-nin-szubur" — animal + name
        "dabx-ba sze ur5-ra-ka",     # grain accounting phrase
        "lugal ur5-ra masz2 ga2-ga2",  # "king's goats deposited" — accounting phrase
        "elam an-sza-an-na-me",      # "they are Elamite from Anshan" — ethnic phrase
        "elam ki-masz-me",           # "they are Elamite from Ki-mash" — ethnic phrase
        "a-kal-la min",              # "a-kal-la, ditto" — accounting ditto notation
        "szara2-mu-tum2 kikken2 e2-mah",  # "Szara2-mu-tum2's mill of the e2-mah"
        "a-ha-ma-ti lu2 lu2-mah",    # compound role phrase
        "lugal-inim-gi-na-ka gesz",  # name + wood/timber commodity
        "ur-zu u3-um-de6",           # "ur-zu, bring-it" — accounting directive
        "lugal sza3-gal",            # "king's choice grain" already added above
        "ur5-sze3 masz2",            # already added in batch 32 — duplicate safe
        "du-du gu-la",               # uncertain compound — 0 confirmed fathers
        # Batch 34: livestock combinations and commodity phrases
        "masz2-gal niga asz2-gar3 niga sila4",  # complex livestock grade phrase
        "udu-ni udu niga",           # "his sheep + prime sheep" — livestock phrase
        "asz2-gar3 niga masz2 niga", # livestock grade combination
        "niga udu niga gu4-e-us2-sa",  # prime sheep + ox combination
        "gukkal niga udu a-lum niga",  # fat-tailed sheep + prime combo
        "masz2-gal niga udu u2",     # large prime goat + sheep + plant
        "masz2-gal niga szimaszgi sila4",  # prime goat + lamb from Shimashki
        "niga masz2",                # "prime goat" — livestock grade
        "sagi lugal",                # "royal cupbearer" — institutional role phrase
        # Batch 34: administrative formula and accounting phrases
        "a bala-e",                  # "water of the bala-rotation" — accounting
        "ba-an esir2 su-ba",         # "it was given as bitumen" — allocation phrase
        "szesz-a-ni lu2 lugal-ku3-zu",  # "his brother, the man of Lugal-kuzu"
        "asz-a lu2-he2-gal2",        # "field of lu2-he2-gal2" — location phrase
        "lugal sza3-gal kunga2",     # "king's choice grain + equid" — commodity phrase
        "nig2-dab5 en",              # "en-priest's rations" — allocation phrase
        "dab-ba didli",              # "various detained/held items" — accounting
        "dabx-ba a2 erin2-na-ka",    # labor wage phrase variant
        "gi-a sa10",                 # "exchanged/sold" — transaction phrase
        "nig2-sa10-am3 gi",          # "purchased reed" — commodity phrase
        "nig2-sa10-ma-ni ku3",       # "his silver price" — accounting back-reference
        "lugal sza3-gal",            # "king's choice grain" — commodity phrase
        "nu-ur2 dub",                # "tablet/account of nu-ur2" — document phrase
        "ka i7 ta",                  # "from the mouth of the river" — location phrase
        "nanna dub",                 # "tablet of Nanna" — temple document
        "ma-an-szum2 ga",            # milk allocation phrase
        "dusu gesztin",              # "basket of wine" — commodity
        "lugal a-ra2",               # "king's installment" — accounting phrase
        "par4 had2",                 # "dried par4 [vessel/container]" — commodity
        "ur5-ta e3-a",               # "came out of debt" — accounting phrase
        "asz-a a-lu5-lu5",           # "irrigation field" — agricultural phrase
        "dub tur-tur",               # "small tablets" — document phrase
        "si-i3-tum-e ba-ab",         # accounting clause fragment
        "ugu2 ba-a-gar",             # "was placed above/in charge" — administrative
        "nig2-dab5 li9-si4",         # "rations of li9-si4 grass" — commodity phrase
        "kin u2 sahar-ba",           # "work, plant, in its soil" — agricultural phrase
        "su7 szukur sza3 sahar-ra",  # "granary spear in the soil" — inventory phrase
        "sag3-ga gu4",               # "beaten ox" — livestock phrase
        "igi-sag nig2-sur-bi",       # "first quality, its pressed product" — quality
        "lu2-szara2 lu2 szum2",      # "man of Szara + the giving man" — phrase
        "hal-la sag-gal2",           # "excellent choice ration" — accounting
        "kusz3 sukud bad3",          # "wall height measure" — measurement phrase
        "dub-szen-e sag du8-hu-ba",  # accounting phrase
        "nir2 babbar",               # "white necklace" — luxury commodity
        "eme3 mu",                   # "language/tongue + year" — phrase
        "bara2 gir13-gesz",          # "dais + gir13-gesz [wood]" — ritual phrase
        "gada sza3-gu gu-za e3",     # "linen + inner + throne + came out" — complex
        "ma-na uruda",               # "mana of copper" — weight + metal commodity
        "kusz nu-ur2-ma",            # "pomegranate leather" — hide commodity
        "lugal-nig2-lagar-e esz3 didli",  # accounting phrase
        "nin-dingir en-ki",          # "en-priestess of Enki" — religious title
        "lu2-mah sag-ub3",           # "lu2-mah priest, side-shrine" — institutional
        "a-du-du mu6-sub3",          # name + garment type — false extraction
        "e gil",                     # "sealed/closed house" — status phrase
        "gudu4 da-lagasz",           # "gudu4 priest from Lagash" — role + place
        "nu-kiri6 gir2-su",          # "gardener of Girsu" — role + place phrase
        "en-nu-ga2 uri5-ma",         # "night watch of Ur" — role + place phrase
        "ma-na ku3",                 # already in batch 33? check — add anyway (safe)
        "ur5-ta e3-a",               # already added above — frozenset deduplicates
        "gir-sze6 lugal",            # "king's feet" — royal title/attribute phrase
        "gu-za szul-gi",             # "throne of Shulgi" — royal attribute
        "szara2-mu-tum2 kikken2 e2-mah",  # already in batch 33 — safe duplicate
        "nin-ur4-ra a-pi4-sal4",     # "nin-ur4-ra of Apisal" — person + city (will be caught by a-pi4-sal4 filter)
        "nin-zabala3 a-pi4-sal4",    # "Nin-zabala3 of Apisal" — deity + city
        "lugal uri5-e",              # "king of Ur" — royal designation phrase
        "ugu2 lu2-dingir-ra",        # "above lu2-dingir-ra" — allocation phrase
        "lugal-nir-gal2 ma2",        # "boat of lugal-nir-gal2" — boat reference
        "ur5-ta e3-a",               # debt clearance phrase (duplicate - fine)
        # Batch 35: livestock and commodity phrases
        "masz2-gal niga masz2 niga", # double prime goat grade phrase
        "udu-nita2-mesz masz2",      # ewes collective + goat combo
        "niga udu u2 masz2",         # prime sheep + plant + goat combo
        "ad3 udu",                   # "old sheep" — livestock age phrase
        "ad3 gu4 niga hi-a",         # "old prime cattle, various" — livestock
        "am gu4 mu",                 # "wild bull + ox + year" — livestock age
        "a am mu",                   # "water/milk + wild bull + year" — livestock
        "sila4-ga masz2 ga",         # "suckling lamb + goat + milk" — livestock
        "el-li-tum masz",            # Akkadian name + goat — false extraction
        "lim me ansze munu4",        # "1000 divine-powers + donkeys + malt" — phrase
        "udu-nita2-mesz masz2",      # already added — duplicate fine
        "szi2-im ansze hi-a",        # "various donkeys with load" — livestock phrase
        "u2-ku-ul-ti2 ansze hi-a",   # "various donkeys for fodder" — livestock phrase
        # Batch 35: administrative/accounting phrases
        "gu4-numun ur-lamma",        # "plow-oxen of ur-lamma" — livestock + person
        "nir2 babbar2",              # "white necklace" — luxury commodity variant
        "ukusz2 dusu",               # "heavy-load basket" — container commodity
        "gu-nigin2 a2 u4-da",        # "daily wages total" — accounting formula
        "kusz gu4-bi",               # "its ox hide" — commodity back-reference
        "szitim gub-ba-am3",         # "builder, it is stationed" — occupational status
        "en mah-di an",              # "en-priest, great one of the sky" — title phrase
        "sza-lim lugal",             # "shalom/well-being of the king" — Akkadian phrase
        "gun an-na i-id-dan",        # "tribute, Anu will give" — ritual phrase
        "szu-szi ansze",             # "60 donkeys" — numeric commodity phrase
        "szu-igi-sze3 du",           # "went toward the front" — directional phrase
        "ur-gigir sza3-gu4",         # "ur-gigir's ox heart" — anatomical phrase
        "u2-bi sar",                 # "its plant, garden" — agricultural phrase
        "a-di2-in an-na",            # "given to Anu" — offering phrase
        "gurusz-bi u4",              # "its workers, day" — labor accounting
        "be-li2-i3-li2 e2",          # "house of Beli-ili" — building reference
        "a-di2-in la2",              # "given, lacking" — accounting phrase
        "ni-isz-qu2-ul an-na",       # Akkadian name + "heavenly" — phrase
        "ku3-babbar uk",             # "silver + uk" — silver commodity phrase
        "bara2 iri-sa12-rig7",       # "dais of Irisagrig" — institutional phrase
        "asz2-qul2 a-na sza-hi-ri-in",  # Akkadian name + preposition + city
        "utu lugal-ga2-sze3 mi-ni-gam",  # "went to the king's Utu" — verbal phrase
        "ad-di gu4 am-mesz ti-la-mesz",  # "added live wild bulls" — livestock phrase
        "sza2 ki-mah szu-a-tu2 bad-u2",  # Akkadian phrase fragment
        "lim me ansze munu4",        # already added — duplicate fine
        "li gur2-gur2",              # "li fruit trees twisting" — agricultural
        "sah-le2-e naga si",         # "naga-si of sah-le2-e" — commodity phrase
        "a gazi",                    # "water/milk of gazi plant" — commodity
        "da-na esz2-gid2",           # "rope of a danna" — measurement phrase
        "gamun2 bala-bi",            # "its cumin rotation" — commodity
        "bappir saga gaz",           # "crushed first-quality beer bread" — commodity
        "bappir a-ga-de3",           # "beer bread from Akkad" — commodity phrase
        "ka5-a-mu naga",             # "naga plant of the fox" — commodity phrase
        "dusu2 nita2 mu",            # "male basket-carrier, year" — phrase variant
        "ba-ba munu3",               # "malt porridge" — variant spelling
        "ba-an ku-ku-szu",           # Akkadian phrase
        "gam-ma man-du",             # Akkadian name pair without conjunction
        "a gazi2",                   # "water/milk of gazi2 plant" — variant
        "ka5-a sud2 hi-hi igi-mesz-szu2",  # Akkadian phrase
        "lu2-inim-ma-bi-mesz ib2-ra",  # "their witnesses, he went" — legal phrase
        "sa10-am3 gi",               # "purchased reed" — commodity phrase
        "gi-szid sa10-a",            # "dry reed sold" — commodity phrase
        "szi-ba-la nim",             # Elamite commodity phrase
        "kusz gu4 mu babbar-bi",     # "ox hide, year, its white" — commodity phrase
        "sa2-sag a-bu-la-um",        # "payment at Abulaum" — commercial phrase
        "u2-tul2-esz18-tar2 a-bi erin2",  # OB Akkadian name + military title
        "pa-bil-sag giri3",          # "via Pabilsag" — deity transport phrase
        "kislah da e2 im-suen",      # "threshing floor beside Im-Suen temple" — location
        "nu-kiri6 gir2-su",          # "gardener of Girsu" — role + place phrase
        "gudu4 e11-e",               # "gudu4 priest who ascends" — priestly epithet
        "nig2-dab5 en",              # "en-priest's rations" — allocation phrase
        "ze2-ba-zu nu-usz-mu-e-a-ak-a",  # Sumerian religious phrase
        "a-zi-ga masz kusz3 im-ma-zi",   # "rising goat measured" — agricultural phrase
        "utu lugal-mu-ur2 di-ku5 mah an",  # "Utu, my king, great judge of the sky"
        "zu-zu lugal gal sza a-la-ah-zi-na",  # Akkadian royal inscription phrase
        "ma2-i3-dub ne-me-et-ti",    # OB Akkadian phrase
        "kusz3 mu-s,u2-um a-na sila",  # Akkadian measurement phrase
        # Batch 36: remaining false entities
        "bappir du",                 # "ordinary beer bread" — variant spelling (no subscript)
        "bappir2 sig5",              # "fine beer bread" — quality commodity
        "dug dida",                  # "vessel of dida beer" — beverage commodity
        "nu-kiri6 gesz gal-gal",     # "gardener of many great trees" — role phrase
        "ur-ba-ba6 munu4-mu2",       # name + sprouted malt — false extraction
        "sa10-am3 zi",               # "purchased flour/grain" — commodity phrase
        "me udu hi-a la2-u-su2",     # "various sheep deductions" — accounting phrase
        "suen-i-din-nam a-bi-szu",   # "Suen-iddinam, his father" — possessive phrase
        "gar3-szum bu-ra-szum szi-pi2-ir-tum",  # three Akkadian names merged
        "u2-tul2-isz8-tar2 a-bi erin2",  # OB Akkadian name variant + military title
        "u2-tul2-isz8-tar2 a-bi",    # OB Akkadian name + father reference
        "mar-tu-mesz lu2 ki-sur-ra", # "Amorites, man of the boundary" — ethnic phrase
        "marduk-ni-szu szu-i lugal", # Babylonian name + barber + king
        "ka3-ri-im ka3-ni-isz",      # two Akkadian place names / proper nouns
        "ba-zi na-szi",              # "was drawn out, she carries" — verbal phrase
        "illu buluh",                # "flood, fright" — administrative phrase
        "i3-mesz gun sig2-mesz",     # "oils, tribute, wools" — commodity list
        "du10-ga ih-ti ban ni",      # Akkadian phrase fragment
        "an-e u",                    # "sky + reed" — cosmic + commodity fragment
        "be silim masz2 masz2",      # unclear Akkadian/Sumerian phrase
        "ma-ha-ar marduk lugal an",  # "before Marduk, king of the sky" — OB royal phrase
        "lugal si-sa2",              # "righteous king" — royal epithet
        "la szi-ka-tum",             # Akkadian phrase
        "esir e3",                   # "bitumen came out" — commodity phrase
        "szen uruda sza",            # "copper tablet of" — artifact phrase
        "su i3-ba lu2 lu2 su-am3",   # accounting phrase
        "esir2 e3",                  # "bitumen came out" — variant spelling
        # Batch 37: final multi-word false extractions
        "i-di lu2 sza i-ki isz-pu-ku",  # Akkadian wages/hire phrase fragment
        "gar3-szum szu-szi an-dah-szum",  # three Akkadian names merged (variant)
        # Batch 37: single-word possessive back-references not yet blocked
        "gu-nigin2-bi",              # "its total" — accounting back-reference
        "e2-mah-ki-bi",              # "its great-house place" — building back-reference
        "za3-bar-bi",                # "its za3-bar metal" — commodity back-reference
        "nimgir-di-ne",              # "heralds of the legal case" — collective noun
        "a-bi",                      # Akkadian "father" possessive — not a personal name
    })

    def _add(self, raw_name: str, role: str, tablet_id: str) -> None:
        name = raw_name.strip()
        if not name or len(name) < 2:
            return
        canonical = (
            self._norm.normalize_name(name) if self._norm else None
        ) or name
        # Block commodity/function words that survived normalization
        # (e.g. the normalizer may collapse "ur-sze3" → "ur" when "ur" is
        # in the known-roots set, producing a false entity).
        if canonical.lower() in self._BLOCKLIST:
            return
        # Block two-person list extractions: "NAME u3 NAME2" where u3 = "and".
        # The parser occasionally extracts a line listing two people joined by the
        # Sumerian conjunction u3 as a single entity.
        if " u3 " in canonical.lower():
            return
        # Block trailing grammatical particle: "NAME lu2" where lu2 = "the person/man".
        # Ur III scribes sometimes append lu2 as a classifier after a name; it is
        # never part of the canonical personal name.
        if canonical.lower().endswith(" lu2"):
            return
        # Block Akkadian fraction / line-break artifacts: "/" never appears in
        # genuine Sumerian or Akkadian personal names in the CDLI ATF corpus.
        if "/" in canonical:
            return
        # Block ATF editorial/bilingual notation artifacts:
        # "%" = language-switch marker (%a = Akkadian, %s = Sumerian)
        # "~" = approximate/uncertain reading marker
        # '"' = ATF quotation/repeat marker in literary or lexical texts
        # "=" = Sumerian–Akkadian equivalence marker in bilingual lexical lists
        # None of these characters can appear in genuine personal names.
        if any(c in canonical for c in ('%', '~', '"', '=')):
            return
        cn = canonical.lower()
        # Block CDLI compound-sign readings used as standalone entities: names
        # that BEGIN with "|" are sign-reading notations (|diszx2u|, |ninda2x|),
        # not personal names.  Personal names that contain "|" embedded in them
        # (e.g. "lugal-uszurx(|.|)") are legitimate and are NOT blocked here.
        if cn.startswith("|"):
            return
        # Block digit-starting entities: numeric fragments from damaged or
        # mis-parsed lines (e.g. "1 nu gu4 su-su im-ma").
        if cn[0].isdigit():
            return
        # Block very long strings (> 30 chars): the longest confirmed-father entity
        # in the full corpus is 22 characters.  Strings above 30 are invariably
        # Akkadian sentence fragments, OB legal clauses, or multi-token phrases —
        # never Ur III personal names.  (Threshold was previously 45; tightened
        # after verifying that 0 entities with confirmed fathers exceed 22 chars.)
        if len(cn) > 30:
            return
        # Block sibling-reference compounds: "NAME szesz NAME2" or "szesz NAME"
        # where szesz (space-separated) means "brother of". Legitimate names that
        # include szesz are always hyphenated (szesz-kal-la, szesz-a-ni, etc.).
        if " szesz" in cn or cn.startswith("szesz "):
            return
        # Block two-name extractions ending in " szar2-ra-ab-du": a common Akkadian
        # personal name that appears after another name when the parser merges adjacent
        # lines.  The bare "szar2-ra-ab-du" entity is legitimate and is NOT blocked.
        if cn.endswith(" szar2-ra-ab-du"):
            return
        # Block Akkadian preposition-phrase fragments: "i-na" and "ina" are the
        # Akkadian preposition "in/at" — never the start of a personal name.
        # "a-na-ku" = Akkadian "I (myself)" — first-person clause fragment.
        if cn.startswith("i-na ") or cn.startswith("ina ") or cn.startswith("a-na-ku "):
            return
        # Block ordinal formula fragments: " -kam" (space + hyphen + kam) is a
        # scribal ordinal suffix ("N-th") used in date formulas.  The space before
        # the hyphen means the number token was separated; always a formula, never
        # a personal name.
        if " -kam" in cn:
            return
        # Block broken-line continuation fragments: any token that begins with a
        # hyphen (space + hyphen) indicates an ATF line-break suffix appended on
        # the following line.  These are NEVER personal names — they are ordinal,
        # case, or verbal suffixes detached from their stem by a clay tablet edge.
        # Verified: 0 entities with " -" in this corpus have confirmed fathers.
        if " -" in cn:
            return
        # Block CDLI transcription artifacts starting with "=" (editorial notes).
        if cn.startswith("="):
            return
        # Block "NAME u3" where the conjunction u3 is the LAST token (the u3 being
        # at string end rather than mid-string, so the " u3 " check above missed it).
        if cn.endswith(" u3"):
            return
        # Block "NAME a-na" where Akkadian "a-na" (to/for) is the trailing token.
        # The extractor picks up the line "NAME a-na [next-line]" as one entity.
        if cn.endswith(" a-na"):
            return
        # Block accounting verb "su-ga [PERSON]": "su-ga" = "was returned [to]".
        # These extract the recipient of a returned-goods formula as an entity.
        if cn.startswith("su-ga "):
            return
        # Block death-record formulas "usz2 [PERSON]": usz2 = "died".
        # These extract the deceased person as a two-word entity with the verb prefix.
        if cn.startswith("usz2 "):
            return
        # Block CDLI damage-notation commodities "n [ITEM]": lowercase "n " as the
        # first token is the CDLI placeholder for an uncertain numeral, followed by
        # a commodity word.  No personal name starts with a single "n" and a space.
        if cn.startswith("n "):
            return
        # Block fugitive-status phrases "zah3 [PERSON/PLACE]": zah3 = "fugitive/escaped".
        if cn.startswith("zah3 "):
            return
        # Block illness-record formulas "tu-ra [PERSON]": tu-ra = "sick/ill".
        # The parser extracts "tu-ra NAME" (illness record) as a two-word entity.
        if cn.startswith("tu-ra "):
            return
        # Block movement-verb phrases ending in " gen-na": gen-na = "went/has gone".
        # These appear as "[DESTINATION/PURPOSE]-sze3 gen-na" — verbal clauses.
        if cn.endswith(" gen-na"):
            return
        # Block Elamite ethnic suffix " elam": "NAME elam" = "NAME [from] Elam".
        if cn.endswith(" elam"):
            return
        # Block city-of-Apisal geographic suffix " a-pi4-sal4".
        if cn.endswith(" a-pi4-sal4"):
            return
        # Block "of Ur" geographic suffix " uri5-ma": "ROLE uri5-ma" = "ROLE in Ur".
        if cn.endswith(" uri5-ma"):
            return
        # Block age/size adjective suffix " tur": "NAME tur" = "junior/young NAME".
        # Legitimate name compounds with tur are always hyphenated (szul-gi-tur, etc.)
        if cn.endswith(" tur") and " " in cn:
            return
        # Block "lugal-sze3 [VERB]" phrases: "lugal-sze3" = "to the king [was brought]".
        # These are transfer-of-goods formulae, never personal names.
        if cn.startswith("lugal-sze3 "):
            return
        # Block "NAME min-kam": "min-kam" = "second time" accounting ordinal.
        if cn.endswith(" min-kam"):
            return
        # Block "NAME tusz-a": "tusz-a" = "is seated/residing" — status clause.
        if cn.endswith(" tusz-a"):
            return
        # Block "NAME sipa ur": trailing "ur" after the herdsman title is a fragment.
        if cn.endswith(" sipa ur"):
            return
        # Block "NAME sipa szah2": swine-herdsman compound; no personal name ends this way.
        if cn.endswith(" sipa szah2"):
            return
        # Block strings containing the Akkadian preposition "ina" as a space-separated token.
        # Personal names never contain a free-standing "ina" mid-string.
        if " ina " in cn:
            return
        # Block "sikil-la [VERB]" ritual purification verb phrases.
        if cn.startswith("sikil-la "):
            return
        # Block CDLI mathematical/addendum operator "+" as first character.
        if cn.startswith("+"):
            return
        # Block Akkadian conditional particle "szum-ma" (if/whether) as first token.
        if cn.startswith("szum-ma "):
            return
        # Block "erin2 nig2-szu [PERSON] [PLACE]": "workers' property of [X in Y]" —
        # an Ur III administrative formula that the extractor misreads as a name.
        if cn.startswith("erin2 nig2-szu "):
            return
        # Block place-determinative suffix " ki" at end of a multi-word string:
        # "NAME ki" = "NAME [place]" — geographic determinative, not a personal name.
        if cn.endswith(" ki") and " " in cn:
            return
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
                ranked = sorted(fathers.items(), key=lambda x: -x[1]["count"])
                w.writerow({
                    "entity":       name,
                    "appearances":  data["appearances"],
                    "tablet_count": len(data["tablets"]),
                    "roles":        "|".join(sorted(data["roles"])),
                    "n_fathers":    len(fathers),
                    "fathers":      "|".join(f"{f}({d['count']})" for f, d in ranked),
                })
        logger.info("Entity roster: %s (%d entities)", filepath, len(self._roster))

    @property
    def entity_count(self) -> int:
        return len(self._roster)

    @property
    def total_appearances(self) -> int:
        return sum(d["appearances"] for d in self._roster.values())
