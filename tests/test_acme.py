"""ACME DNS-01 challenge record handling."""

import pytest

DOMAIN = "example.com"
USERNAME = "testuser"
APIKEY = "testkey"


@pytest.fixture
def zone(acme, monkeypatch):
    class FakeZone:
        def __init__(self):
            self.existing = None
            self.added = []
            self.removed = []

        def fetch(self, name, domain, record_type, username, apikey):
            self.lookups = (name, domain, record_type)
            return self.existing

        def add(self, domain, name, record_type, data, ttl, username, apikey):
            self.added.append((name, record_type, data, ttl))

        def remove(self, domain, name, record_type, data, username, apikey):
            self.removed.append((name, record_type, data))

    fake = FakeZone()
    monkeypatch.setattr(acme, "fetchDNSRecordData", fake.fetch)
    monkeypatch.setattr(acme, "addDNSRecord", fake.add)
    monkeypatch.setattr(acme, "removeDNSRecord", fake.remove)
    return fake


class TestCreateTxtRecord:

    def test_creates_a_txt_record_with_a_short_ttl(self, acme, zone):
        acme.createTxtRecord("_acme-challenge", "token", DOMAIN, USERNAME, APIKEY)
        assert zone.added == [("_acme-challenge", "TXT", "token", 300)]

    def test_reports_the_created_record(self, acme, zone, capsys):
        acme.createTxtRecord("_acme-challenge", "token", DOMAIN, USERNAME, APIKEY)
        assert "_acme-challenge=token" in capsys.readouterr().out


class TestDeleteTxtRecord:

    def test_removes_the_record_using_its_current_value(self, acme, zone):
        zone.existing = "token"
        acme.deleteTxtRecord("_acme-challenge", DOMAIN, USERNAME, APIKEY)
        assert zone.removed == [("_acme-challenge", "TXT", "token")]

    def test_a_missing_record_is_skipped_rather_than_removed(self, acme, zone):
        zone.existing = None
        acme.deleteTxtRecord("_acme-challenge", DOMAIN, USERNAME, APIKEY)
        assert zone.removed == []

    def test_a_missing_record_is_reported(self, acme, zone, capsys):
        zone.existing = None
        acme.deleteTxtRecord("_acme-challenge", DOMAIN, USERNAME, APIKEY)
        assert "skipping deletion" in capsys.readouterr().out


def test_fetch_looks_up_the_txt_record_type(acme, zone):
    zone.existing = "token"
    assert acme.fetchDomainValue("_acme-challenge", DOMAIN, USERNAME, APIKEY) == "token"
    assert zone.lookups == ("_acme-challenge", DOMAIN, "TXT")
