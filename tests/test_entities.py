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
