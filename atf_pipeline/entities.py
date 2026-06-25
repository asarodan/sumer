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
