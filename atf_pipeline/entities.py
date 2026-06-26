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
        # Block very long strings (> 45 chars): all confirmed personal names and
        # institutional names in the Ur III corpus are under 35 characters; strings
        # above 45 are invariably Akkadian sentence fragments or Old Babylonian
        # legal clause extractions.
        if len(cn) > 45:
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
