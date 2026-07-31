"""Patronymic ('NAME dumu FATHER') extraction and homonym detection."""
import pytest

from atf_pipeline import EntityScanner, Normalizer


class TestPatronymicExtraction:
    def test_basic_child_of(self, ext):
        pairs = ext.extract_patronymics(["1. kiszib3 ur-{d}szara2 dumu ur-mes"])
        assert ("ur-szara2", "ur-mes") in pairs

    def test_name_line_without_leading_number(self, ext):
        # Parentage often sits on a bare name line (no leading quantity); the
        # {d} determinative is stripped, suffixes are left to the normaliser.
        pairs = ext.extract_patronymics(["ur-{d}ba-ba6 dumu ur-sa6-ga"])
        assert ("ur-ba-ba6", "ur-sa6-ga") in pairs

    def test_status_descriptor_rejected(self, ext):
        # "dumu lugal" = prince (a status), not a father's name.
        assert ext.extract_patronymics(["1. lu2-saga dumu lugal"]) == []

    def test_hyphenated_dumu_compound_ignored(self, ext):
        # "dumu-gu4" is a compound word, not "dumu FATHER".
        assert ext.extract_patronymics(["1. 3(asz) dumu-nun-szita"]) == []


class TestHomonymRoster:
    def test_two_fathers_flags_homonym(self):
        scanner = EntityScanner(Normalizer())
        scanner.add_patronymics([
            ("lu2-szara2", "ur-nigar"),
            ("lu2-szara2", "lugal-ezem"),
            ("a-kal-la",   "ur-du6"),
        ])
        assert scanner.homonym_count == 1   # only lu2-szara2 has 2 distinct fathers

    def test_single_father_not_homonym(self):
        scanner = EntityScanner(Normalizer())
        scanner.add_patronymics([("a-kal-la", "ur-du6"), ("a-kal-la", "ur-du6")])
        assert scanner.homonym_count == 0
