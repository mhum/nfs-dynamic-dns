"""Which address families a run updates, and how failures are reported."""

import pytest


@pytest.fixture
def calls(ddns, monkeypatch):
    """Record every check_ips invocation instead of touching the network."""
    recorded = []

    def fake_check_ips(domain, subdomain, username, apikey, v6=False, dig=False,
                       create_if_not_exists=False):
        recorded.append({
            "domain": domain,
            "subdomain": subdomain,
            "v6": v6,
            "dig": dig,
            "create_if_not_exists": create_if_not_exists,
        })

    monkeypatch.setattr(ddns, "check_ips", fake_check_ips)
    return recorded


def families(calls):
    return [call["v6"] for call in calls]


def test_updates_only_ipv4_by_default(ddns, creds, calls):
    assert ddns.main([]) == 0
    assert families(calls) == [False]


def test_ipv6_flag_updates_both_families(ddns, creds, calls):
    assert ddns.main(["--ipv6"]) == 0
    assert families(calls) == [False, True]


def test_ipv6_short_flag_updates_both_families(ddns, creds, calls):
    assert ddns.main(["-6"]) == 0
    assert families(calls) == [False, True]


def test_enable_ipv6_env_var_updates_both_families(ddns, creds, calls, monkeypatch):
    monkeypatch.setenv("ENABLE_IPV6", "true")
    assert ddns.main([]) == 0
    assert families(calls) == [False, True]


def test_ipv4_is_updated_before_ipv6(ddns, creds, calls):
    ddns.main(["--ipv6"])
    assert families(calls) == [False, True], "IPv4 must not wait on IPv6 connectivity"


def test_enable_ipv6_false_leaves_ipv6_disabled(ddns, creds, calls, monkeypatch):
    monkeypatch.setenv("ENABLE_IPV6", "false")
    assert ddns.main([]) == 0
    assert families(calls) == [False]


def test_disabling_ipv4_gives_an_ipv6_only_run(ddns, creds, calls, monkeypatch):
    monkeypatch.setenv("ENABLE_IPV4", "false")
    assert ddns.main(["--ipv6"]) == 0
    assert families(calls) == [True]


def test_no_ipv4_cli_flag_gives_an_ipv6_only_run(ddns, creds, calls):
    assert ddns.main(["--ipv6", "--no-ipv4"]) == 0
    assert families(calls) == [True]


def test_env_var_can_re_enable_ipv4_over_the_cli_flag(ddns, creds, calls, monkeypatch):
    monkeypatch.setenv("ENABLE_IPV4", "true")
    assert ddns.main(["--ipv6", "--no-ipv4"]) == 0
    assert families(calls) == [False, True]


def test_disabling_both_families_is_rejected(ddns, creds, calls):
    assert ddns.main(["--no-ipv4"]) == 1
    assert calls == []


def test_disabling_both_families_explains_why(ddns, creds, calls, capsys):
    ddns.main(["--no-ipv4"])
    printed = capsys.readouterr().out
    assert "ENABLE_IPV4" in printed
    assert "Traceback" not in printed


def test_dig_preference_reaches_every_family(ddns, creds, calls, monkeypatch):
    monkeypatch.setenv("IP_USE_DIG", "true")
    ddns.main(["--ipv6"])
    assert [call["dig"] for call in calls] == [True, True]


def test_ip_use_dig_false_is_not_treated_as_enabled(ddns, creds, calls, monkeypatch):
    monkeypatch.setenv("IP_USE_DIG", "false")
    ddns.main([])
    assert [call["dig"] for call in calls] == [False]


def test_missing_records_are_created(ddns, creds, calls):
    ddns.main(["--ipv6"])
    assert [call["create_if_not_exists"] for call in calls] == [True, True]


def test_subdomain_is_passed_through(ddns, creds, calls, monkeypatch):
    monkeypatch.setenv("SUBDOMAIN", "home")
    ddns.main([])
    assert calls[0]["subdomain"] == "home"


@pytest.mark.parametrize("missing", ["USERNAME", "API_KEY", "DOMAIN"])
def test_missing_credentials_are_rejected(ddns, creds, calls, monkeypatch, missing):
    monkeypatch.delenv(missing)
    assert ddns.main([]) == 1
    assert calls == []


@pytest.mark.parametrize("missing", ["USERNAME", "API_KEY", "DOMAIN"])
def test_missing_credentials_name_the_missing_variable(ddns, creds, monkeypatch,
                                                       calls, capsys, missing):
    monkeypatch.delenv(missing)
    ddns.main([])
    printed = capsys.readouterr().out
    assert missing in printed
    assert "Traceback" not in printed


class TestFailureIsolation:
    """One address family failing must not silence the other, or the exit code."""

    @pytest.fixture
    def failing(self, ddns, monkeypatch):
        attempted = []

        def make(fails_on_v6):
            def fake_check_ips(domain, subdomain, username, apikey, v6=False,
                               dig=False, create_if_not_exists=False):
                attempted.append(v6)
                if v6 is fails_on_v6:
                    raise ConnectionError("network is unreachable")

            monkeypatch.setattr(ddns, "check_ips", fake_check_ips)
            return attempted

        return make

    def test_ipv6_failure_still_updates_ipv4(self, ddns, creds, failing):
        attempted = failing(fails_on_v6=True)
        assert ddns.main(["--ipv6"]) == 1
        assert attempted == [False, True]

    def test_ipv4_failure_still_updates_ipv6(self, ddns, creds, failing):
        attempted = failing(fails_on_v6=False)
        assert ddns.main(["--ipv6"]) == 1
        assert attempted == [False, True]

    def test_failure_is_reported_on_stdout(self, ddns, creds, failing, capsys):
        failing(fails_on_v6=True)
        ddns.main(["--ipv6"])
        output = capsys.readouterr().out
        assert "AAAA" in output
        assert "network is unreachable" in output

    def test_sole_family_failing_exits_non_zero(self, ddns, creds, failing):
        failing(fails_on_v6=False)
        assert ddns.main([]) == 1


def test_export_to_writes_a_zone_file_without_updating_records(ddns, creds, calls,
                                                               monkeypatch, tmp_path):
    monkeypatch.setattr(ddns, "getAllDNSRecords", lambda *args: [
        {"name": "", "type": "A", "data": "203.0.113.1", "ttl": 3600},
    ])
    destination = tmp_path / "zone.txt"

    assert ddns.main(["--export-to", str(destination)]) == 0

    assert "203.0.113.1" in destination.read_text(encoding="utf-8")
    assert calls == []
