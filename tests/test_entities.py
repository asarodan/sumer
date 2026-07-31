"""Issuer / recipient / agent extraction from administrative formulae,
including the debit-verb (ba-zi) bleed fix."""
import pytest


class TestIssuer:
    def test_ablative_with_debit_verb(self, ext):
        # "ki na-sa6-ta ba-zi" ("expended from Nasa") → issuer Nasa, NOT
        # "na-sa6-ta ba-zi".
        assert ext._extract_issuer("ki na-sa6-ta ba-zi") == "na-sa6"

    def test_internal_ta_name_kept_whole(self, ext):
        assert ext._extract_issuer("ki in-ta-e3-a-ta ba-zi") == "in-ta-e3-a"

    def test_genuine_person_bazi_preserved(self, ext):
        # "ki ba-zi-ta" is the person Bazi — the name must survive intact.
        assert ext._extract_issuer("ki ba-zi-ta") == "ba-zi"

    def test_abbreviated_ablative_strips_verb(self, ext):
        # No -ta to bound the name; the trailing debit verb is stripped.
        got = ext._extract_issuer("ki {d}iszkur-illat ba-zi")
        assert "ba-zi" not in got and "iszkur-illat" in got

    def test_title_stripped(self, ext):
        assert ext._extract_issuer("ki lu2-dingir-ra szabra-ta ba-zi") == "lu2-dingir-ra"

    def test_plain_ablative(self, ext):
        assert ext._extract_issuer("ki ur-{d}szara2-ta") in ("ur-szara2", "ur-{d}szara2")


class TestRecipientAndAgent:
    def test_inline_shu_ba_ti(self, ext):
        assert ext._extract_recipient_inline("ku3-ga-ni szu ba-ti") == "ku3-ga-ni"

    def test_idab5_recipient(self, ext):
        # {d} divine determinative is normalised away by _clean_atf_name.
        assert ext._extract_recipient_idab5("lu2-{d}nanna i3-dab5") == "lu2-nanna"

    def test_giri3_agent(self, ext):
        assert ext._extract_agent("giri3 ur-{d}szul-pa-e3") == "ur-szul-pa-e3"

    def test_ugula_agent(self, ext):
        assert ext._extract_agent("ugula da-da") == "da-da"

    def test_mukux_idab5_recipient(self, ext):
        # Drehem delivery formula: "mu-kux(DU) NAME i3-dab5" — NAME is the
        # receiving official (P212153 and thousands of Drehem tablets).
        assert ext._extract_recipient_idab5(
            "mu-kux(DU) ab-ba-sa6-ga i3-dab5") == "ab-ba-sa6-ga"

    def test_bare_mukux_is_not_a_recipient(self, ext):
        # Without i3-dab5, "mu-kux(DU) NAME" names the deliverer, not the
        # receiver; the recipient extractor must not fire.
        assert ext._extract_recipient_idab5(
            "mu-kux(DU) szesz-da-da sanga") is None


class TestSealedReceipt:
    """kiszib3 PN on a ki X-ta receipt = PN received (envelope-proven)."""

    def test_kiszib_is_recipient_on_receipt(self, ext):
        # P133455 body: ki lu2-gi-na-ta / kiszib3 ur-szusz3-ba-ba6; its own
        # envelope restates the same transaction as "ur-szusz3-ba-ba6 szu ba-ti".
        txs = ext.extract_transactions([
            "@tablet", "@obverse",
            "1. 3(u) 1(asz) 4(barig) 1(ban2) sze gur lugal",
            "2. ki lu2-gi-na-ta",
            "@reverse",
            "1. kiszib3 ur-{d}szusz3-{d}ba-ba6",
            "2. iti sze-sag11-ku5",
        ], "TEST-KISZIB")
        assert txs
        assert txs[0].issuer == "lu2-gi-na"
        assert txs[0].recipient == "ur-szusz3-ba-ba6"

    def test_kiszib_only_tablet_passes_admin_gate(self, ext):
        # A sealed receipt whose only admin markers are "ki NAME" (no -ta)
        # and kiszib3 must not be rejected as non-administrative (P129198).
        txs = ext.extract_transactions([
            "@tablet", "@obverse",
            "1. 3(disz) ad3 udu",
            "2. ki lugal-ku3-zu",
            "@reverse",
            "1. kiszib3 nam-zi-tar-ra",
            "2. iti nesag",
        ], "TEST-GATE")
        assert txs, "kiszib3-only receipt must pass the admin-keyword gate"
        assert txs[0].issuer == "lugal-ku3-zu"

    def test_kiszib_stays_issuer_without_other_frames(self, ext):
        # With no ki X-ta issuer at all, kiszib3 remains the fallback issuer
        # (accountability), not a recipient.
        txs = ext.extract_transactions([
            "@tablet", "@obverse",
            "1. 5(asz) sze gur",
            "2. kiszib3 ur-lugal",
            "3. iti nesag",
        ], "TEST-KISZIB-ISS")
        assert txs
        assert txs[0].issuer == "ur-lugal"
        assert txs[0].recipient is None


class TestAuditRecipientPriority:
    """Audit finding (P202259): explicit receipt verbs outrank sa2-du11
    destination labels, and document-count notes yield no quantities."""

    def test_szu_bati_overrides_sa2_du11_destination(self, ext):
        txs = ext.extract_transactions([
            "@tablet", "@obverse",
            "1. 4(gesz2) 1(u) 1(asz) 2(barig) sze gur lugal",
            "2. sa2-du11 {d}nin-gir2-su-ka-sze3",
            "3. ki ur-{d}ba-ba6 szabra-ta",
            "@reverse",
            "1. ki-tusz-lu2",
            "2. szu ba-ti",
        ], "TEST-SA2DU11")
        assert txs
        assert txs[0].recipient == "ki-tusz-lu2"

    def test_sa2_du11_kept_when_no_receipt_verb(self, ext):
        # Without a szu ba-ti, the offering destination is still the best
        # available recipient (P129198 behaviour preserved).
        txs = ext.extract_transactions([
            "@tablet", "@obverse",
            "1. 3(asz) sze gur",
            "2. sa2-du11 {d}szara2",
            "3. ki lugal-ku3-zu-ta",
        ], "TEST-SA2DU11-ONLY")
        assert txs
        assert txs[0].recipient == "szara2"

    def test_kiszib_bi_count_is_not_a_quantity(self, ext):
        # "kiszib3-bi N-am3" = "its sealed tablets: N" (P201081, P208651).
        assert ext.extract_quantity("kiszib3-bi 2(disz)-am3", context_gur=True) == (None, None)
        assert ext.extract_quantity("kiszib3-bi 1(u) 3(disz)-am3", context_gur=True) == (None, None)


class TestNameVerbClauseStripping:
    def test_su_su_dam_stripped(self, ext):
        # P116018: "kiszib3 ur-sa6-ga nu-banda3 su-su-dam" — name + title +
        # "to be repaid" must reduce to the bare name.
        assert ext._clean_atf_name("ur-sa6-ga nu-banda3 su-su-dam") == "ur-sa6-ga"

    def test_i3_gal2_stripped(self, ext):
        assert ext._clean_atf_name("ur-nigar i3-gal2") == "ur-nigar"


class TestLogogramNamesNotUncertainReadings:
    """Trailing-digit ALL-CAPS logograms (ARAD2, GAN2, SIG7 ...) are determinate
    sign readings and common personal names — not CDLI's uncertain-reading
    notation (KA, SZIM, LAM ...), which never carries a digit. Found via
    corpus-scale cross-validation against tablets with embedded translations
    (P109320: "ki ARAD2-ta" translated as "from ARAD," extracted no issuer
    at all before this fix)."""

    def test_arad2_is_a_name(self, ext):
        assert ext._looks_like_name("ARAD2") is True
        assert ext._extract_issuer("ki ARAD2-ta") == "ARAD2"

    def test_uncertain_reading_without_digit_still_rejected(self, ext):
        assert ext._looks_like_name("KA") is False
        assert ext._looks_like_name("SZIM") is False
        assert ext._looks_like_name("LAM") is False

    def test_catalog_code_still_stripped_from_names(self, ext):
        # Genuine sign-catalog references (3+ digit index) must still be
        # stripped when standalone; only the digit-count threshold changed.
        # Hyphen-prefixed occurrences (nin-LAK384) are deliberately preserved
        # as compound-name components — a separate, pre-existing rule.
        assert "KWU147" not in ext._clean_atf_name("ur-{KWU147}")
        assert ext._clean_atf_name("LAK384") == ""

    def test_ordinary_logogram_survives_cleaning(self, ext):
        assert ext._clean_atf_name("ARAD2") == "ARAD2"
        assert ext._clean_atf_name("GAN2") == "GAN2"


class TestKiszibRollDamagedSealBoundary:
    """A multi-sealer disbursement roll where one seal-line's name is too
    damaged to read must still register as a seal BOUNDARY -- the entry
    it seals stays unattributed, and it must not let a later, unrelated
    sealer's name bleed backward onto it (P102286, ASJ 09 237 10: "8 gur,
    under seal of ..." followed by "34 gur ..., under seal of Ur-Enunna"
    -- only the second entry belongs to Ur-Enunna)."""

    def test_illegible_inline_seal_leaves_entry_unattributed(self, ext):
        summ = ext.extract_records([
            "@tablet", "@obverse",
            "1. 8(asz) gur kiszib3 x-x-[...]",
            "2. 3(u) 4(asz) 4(barig) 8(disz) sila3 gur",
            "3. kiszib3 ur-e2-nun-na",
        ], "TEST-DAMAGED-SEAL")
        ents = [e for r in summ.records for e in r.entries]
        assert len(ents) == 2
        assert ents[0].recipient is None
        assert ents[1].recipient == "ur-e2-nun-na"

    def test_inline_kiszib_regex_detects_ellipsis_damage(self, ext):
        # Character class must admit "." so damage-ellipsis fragments are
        # recognised as a seal clause at all, not just rejected as an
        # unreadable name.
        assert ext._RE_KISZIB_INLINE.search("8(asz) gur kiszib3 x-x-[...]")


class TestMultiIssuerSectionSplitting:
    """A section can carry more than one distinct "ki X-ta" clause, each
    retroactively closing the quantities that precede it -- the common ATF
    convention of quantities first, then the issuer clause (P109320: barley
    /emmer/wheat closed by "ki ARAD2-ta", then a separately-issued deficit
    entry closed by "ki bi2-da-ta"; P102435 has the identical shape). A
    single scalar issuer per record silently discarded the second clause
    and its entries; this must now split into separate records."""

    def test_two_issuer_clauses_split_into_two_groups(self, ext):
        summ = ext.extract_records([
            "@tablet", "@obverse",
            "1. 1(gesz2) sze gur",
            "2. ki ARAD2-ta",
            "3. 3(asz) sze gur",
            "4. ki bi2-da-ta",
        ], "TEST-MULTI-ISSUER")
        groups = {(r.issuer): [e.quantity for e in r.entries] for r in summ.records}
        assert groups.get("ARAD2") == [18000.0]
        assert groups.get("bi2-da") == [900.0]

    def test_single_issuer_section_still_produces_one_record(self, ext):
        # Regression guard: the common, simple case (one issuer, no split
        # needed) must not be fragmented by this change.
        summ = ext.extract_records([
            "@tablet", "@obverse",
            "1. 1(gesz2) sze gur",
            "2. 3(asz) sze gur",
            "3. ki ARAD2-ta",
        ], "TEST-SINGLE-ISSUER")
        assert len(summ.records) == 1
        assert summ.records[0].issuer == "ARAD2"
        assert [e.quantity for e in summ.records[0].entries] == [18000.0, 900.0]


class TestInstitutionalIssuerInKiTaFrame:
    """ka-guru7 ("granary-gate") is correctly excluded from personal-name
    matching as a place, but inside the "ki X-ta" source frame it is a
    legitimate institutional issuer (251 tablets; P102435's own translation:
    "from the grain depot manager")."""

    def test_ka_guru7_recognized_as_issuer(self, ext):
        assert ext._extract_issuer("ki ka-guru7-ta") == "ka-guru7"

    def test_ka_guru7_still_rejected_as_a_bare_name(self, ext):
        # The general name filter is unchanged outside the ki-ta frame.
        assert ext._looks_like_name("ka-guru7") is False


class TestKiTaTrailingDamageMarker:
    """A damage marker directly abutting "-ta" with no separating space
    ("ki ka-guru7-ta#") must not silently fail the whole issuer match
    (912 tablets corpus-wide)."""

    def test_trailing_hash_after_ta(self, ext):
        assert ext._extract_issuer("ki ka-guru7-ta#") == "ka-guru7"

    def test_trailing_question_mark_after_ta(self, ext):
        assert ext._extract_issuer("ki lugal-ku3-zu-ta?") == "lugal-ku3-zu"
