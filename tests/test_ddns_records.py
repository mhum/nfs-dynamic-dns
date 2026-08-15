"""Record-level behaviour: which record type is touched, and add vs. replace."""

import pytest

IPV4 = "203.0.113.7"
IPV6 = "2001:db8::7"


@pytest.fixture
def dns(ddns, monkeypatch):
    """A fake NFSN zone that records the writes made against it."""

    class FakeZone:
        def __init__(self):
            self.records = {}
            self.added = []
            self.replaced = []

        def set_existing(self, record_type, data):
            self.records[record_type] = data

        def fetch(self, name, domain, record_type, username, apikey):
            return self.records.get(record_type)

        def add(self, domain, name, record_type, data, ttl, username, apikey):
            self.added.append((record_type, data, ttl))
            self.records[record_type] = data

        def replace(self, domain, name, record_type, data, ttl, username, apikey):
            self.replaced.append((record_type, data, ttl))
            self.records[record_type] = data

    zone = FakeZone()
    monkeypatch.setattr(ddns, "fetchDNSRecordData", zone.fetch)
    monkeypatch.setattr(ddns, "addDNSRecord", zone.add)
    monkeypatch.setattr(ddns, "replaceDNSRecord", zone.replace)
    monkeypatch.setattr(ddns, "fetchCurrentIP", lambda v6=False: IPV6 if v6 else IPV4)
    return zone


class TestRecordTypeSelection:

    def test_ipv4_run_reads_the_a_record(self, ddns, dns):
        requested = []
        ddns.fetchDNSRecordData = lambda name, domain, rtype, u, k: requested.append(rtype)
        ddns.fetchDomainIP("example.com", "home", "user", "key", v6=False)
        assert requested == ["A"]

    def test_ipv6_run_reads_the_aaaa_record(self, ddns, dns):
        requested = []
        ddns.fetchDNSRecordData = lambda name, domain, rtype, u, k: requested.append(rtype)
        ddns.fetchDomainIP("example.com", "home", "user", "key", v6=True)
        assert requested == ["AAAA"]

    def test_ipv4_run_writes_the_a_record(self, ddns, dns):
        ddns.replaceDomain("example.com", "home", IPV4, "user", "key", v6=False)
        assert dns.replaced == [("A", IPV4, 3600)]

    def test_ipv6_run_writes_the_aaaa_record(self, ddns, dns):
        ddns.replaceDomain("example.com", "home", IPV6, "user", "key", v6=True)
        assert dns.replaced == [("AAAA", IPV6, 3600)]


class TestAddVersusReplace:

    def test_existing_record_is_replaced(self, ddns, dns):
        ddns.replaceDomain("example.com", "home", IPV4, "user", "key", create=False)
        assert dns.replaced and not dns.added

    def test_missing_record_is_added(self, ddns, dns):
        ddns.replaceDomain("example.com", "home", IPV4, "user", "key", create=True)
        assert dns.added and not dns.replaced

    def test_check_ips_creates_a_record_that_does_not_exist_yet(self, ddns, dns):
        ddns.check_ips("example.com", "home", "user", "key", v6=True,
                       create_if_not_exists=True)
        assert dns.added == [("AAAA", IPV6, 3600)]

    def test_check_ips_does_not_create_when_creation_is_disabled(self, ddns, dns):
        ddns.check_ips("example.com", "home", "user", "key", v6=True,
                       create_if_not_exists=False)
        assert dns.added == []
        assert dns.replaced == [("AAAA", IPV6, 3600)]

    def test_check_ips_replaces_an_existing_record_rather_than_adding(self, ddns, dns):
        dns.set_existing("A", "198.51.100.1")
        ddns.check_ips("example.com", "home", "user", "key",
                       create_if_not_exists=True)
        assert dns.added == []
        assert dns.replaced == [("A", IPV4, 3600)]


class TestUpdateDecision:

    def test_matching_ip_is_left_alone(self, ddns, dns):
        dns.set_existing("A", IPV4)
        ddns.check_ips("example.com", "home", "user", "key")
        assert dns.replaced == [] and dns.added == []

    def test_stale_ip_is_updated(self, ddns, dns):
        dns.set_existing("A", "198.51.100.1")
        ddns.check_ips("example.com", "home", "user", "key")
        assert dns.replaced == [("A", IPV4, 3600)]

    def test_equivalent_ipv6_spellings_count_as_matching(self, ddns, dns):
        dns.set_existing("AAAA", "2001:0db8:0000:0000:0000:0000:0000:0007")
        ddns.check_ips("example.com", "home", "user", "key", v6=True)
        assert dns.replaced == [], "expanded and compressed IPv6 are the same address"

    def test_name_server_placeholder_is_reported_as_unset(self, ddns, dns, capsys):
        dns.set_existing("A", "nearlyfreespeech.net.")
        ddns.check_ips("example.com", "home", "user", "key")
        assert "doesn't appear to be set yet" in capsys.readouterr().out

    def test_name_server_placeholder_is_created_rather_than_replaced(self, ddns, dns):
        dns.set_existing("AAAA", "nearlyfreespeech.net.")
        ddns.check_ips("example.com", "home", "user", "key", v6=True,
                       create_if_not_exists=True)
        assert dns.added == [("AAAA", IPV6, 3600)]
        assert dns.replaced == []


class TestIPComparison:

    def test_identical_addresses_match(self, ddns):
        assert ddns.doIPsMatch("203.0.113.7", "203.0.113.7") is True

    def test_different_addresses_do_not_match(self, ddns):
        assert ddns.doIPsMatch("203.0.113.7", "198.51.100.1") is False

    def test_equivalent_ipv6_spellings_match(self, ddns):
        assert ddns.doIPsMatch("2001:db8::7", "2001:0db8:0000:0000:0000:0000:0000:0007") is True

    def test_addresses_from_different_families_do_not_match(self, ddns):
        assert ddns.doIPsMatch("203.0.113.7", "2001:db8::7") is False

    def test_a_non_address_never_matches(self, ddns):
        assert ddns.doIPsMatch("nearlyfreespeech.net.", "203.0.113.7") is False

    def test_a_missing_record_never_matches(self, ddns):
        assert ddns.doIPsMatch(None, "203.0.113.7") is False


class TestBothFamiliesEnabled:
    """Enabling IPv6 adds an AAAA update; it does not swap the A update out."""

    def test_both_records_are_written_in_one_run(self, ddns, dns, creds):
        dns.set_existing("A", "198.51.100.1")
        dns.set_existing("AAAA", "2001:db8::dead")

        assert ddns.main(["--ipv6"]) == 0

        assert dns.replaced == [("A", IPV4, 3600), ("AAAA", IPV6, 3600)]

    def test_an_ipv6_only_run_leaves_the_a_record_untouched(self, ddns, dns, creds):
        dns.set_existing("A", "198.51.100.1")
        dns.set_existing("AAAA", "2001:db8::dead")

        assert ddns.main(["--ipv6", "--no-ipv4"]) == 0

        assert dns.replaced == [("AAAA", IPV6, 3600)]
        assert dns.records["A"] == "198.51.100.1"


class TestCurrentIPLookup:

    def test_dig_asks_for_the_matching_address_family(self, ddns, monkeypatch):
        commands = []
        monkeypatch.setattr(ddns.os, "popen",
                            lambda cmd: commands.append(cmd) or _FakeStream('"203.0.113.7"'))

        ddns.digCurrentIP(v6=False)
        ddns.digCurrentIP(v6=True)

        assert "dig -4 " in commands[0]
        assert "dig -6 " in commands[1]

    def test_dig_strips_the_quotes_around_the_answer(self, ddns, monkeypatch):
        monkeypatch.setattr(ddns.os, "popen", lambda cmd: _FakeStream('"203.0.113.7"'))
        assert ddns.digCurrentIP() == "203.0.113.7"

    def test_http_lookup_uses_the_configured_providers(self, ddns, monkeypatch):
        requested = []

        class FakeResponse:
            text = " 203.0.113.7\n"

            def raise_for_status(self):
                pass

        monkeypatch.setattr(ddns.requests, "get",
                            lambda url: requested.append(url) or FakeResponse())

        ddns.fetchCurrentIP(v6=False)
        ddns.fetchCurrentIP(v6=True)

        assert requested == [ddns.IPV4_PROVIDER_URL, ddns.IPV6_PROVIDER_URL]

    def test_http_lookup_trims_the_response_body(self, ddns, monkeypatch):
        class FakeResponse:
            text = " 203.0.113.7\n"

            def raise_for_status(self):
                pass

        monkeypatch.setattr(ddns.requests, "get", lambda url: FakeResponse())
        assert ddns.fetchCurrentIP() == "203.0.113.7"


class _FakeStream:
    def __init__(self, text):
        self._text = text

    def read(self):
        return self._text
