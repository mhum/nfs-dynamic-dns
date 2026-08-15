"""Zone file rendering for `--export-to`."""

import pytest


def record(name="", record_type="A", data="203.0.113.7", ttl=3600, aux=None):
    return {"name": name, "type": record_type, "data": data, "ttl": ttl, "aux": aux}


def lines(ddns, records):
    return ddns.NFSNDnsToZoneFile(records)


def test_a_record_renders_as_tab_separated_fields(ddns):
    assert lines(ddns, [record(name="home")])[0] == "home\t3600\tIN\tA\t203.0.113.7"


def test_the_bare_domain_renders_as_an_at_sign(ddns):
    assert lines(ddns, [record(name="")])[0].startswith("@\t")


def test_txt_data_is_quoted(ddns):
    rendered = lines(ddns, [record(name="_acme", record_type="TXT", data="token")])[0]
    assert rendered.endswith('TXT\t"token"')


def test_mx_data_is_prefixed_with_its_priority(ddns):
    rendered = lines(ddns, [record(name="", record_type="MX", data="mail.example.com", aux=10)])[0]
    assert rendered.endswith("MX\t10 mail.example.com")


def test_aaaa_records_are_exported(ddns):
    rendered = lines(ddns, [record(name="home", record_type="AAAA", data="2001:db8::7")])[0]
    assert rendered == "home\t3600\tIN\tAAAA\t2001:db8::7"


def test_records_are_sorted_by_host_then_data(ddns):
    output = lines(ddns, [
        record(name="www", data="203.0.113.9"),
        record(name="home", data="203.0.113.8"),
        record(name="home", data="203.0.113.7"),
    ])
    assert [line.split("\t")[0] for line in output[:3]] == ["home", "home", "www"]
    assert output[0].endswith("203.0.113.7")


def test_output_ends_with_a_blank_line_so_the_file_gets_a_trailing_newline(ddns):
    assert lines(ddns, [record()])[-1] == ""


def test_an_empty_zone_renders_a_single_blank_line(ddns):
    assert lines(ddns, []) == [""]
