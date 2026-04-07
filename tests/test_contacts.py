"""Tests for buddy-comms/contacts_lookup.py."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SKILL_PATH = Path(__file__).parent.parent / "skills" / "buddy-comms"
sys.path.insert(0, str(SKILL_PATH))

import contacts_lookup


@pytest.fixture(autouse=True)
def tmp_contacts(sample_contacts):
    with patch.object(contacts_lookup, "CONTACTS_PATH", sample_contacts):
        yield


class TestSearch:
    def test_exact_name(self):
        assert len(contacts_lookup.search("Ірина Дорош")) == 1

    def test_nickname(self):
        assert len(contacts_lookup.search("Іра")) == 1

    def test_role(self):
        assert len(contacts_lookup.search("дружина")) == 1

    def test_not_found(self):
        assert len(contacts_lookup.search("Невідомий")) == 0

    def test_case_insensitive(self):
        assert len(contacts_lookup.search("ірина")) == 1


class TestAddContact:
    def test_add_new(self):
        assert contacts_lookup.add_contact("Олег", "o@test.com")["status"] == "added"

    def test_duplicate(self):
        assert contacts_lookup.add_contact("Ірина Дорош", "x@test.com")["status"] == "exists"
