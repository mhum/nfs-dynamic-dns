"""Coverage for the NFSN API layer: authentication, requests, and DNS calls."""

import hashlib
from urllib.parse import parse_qs

import pytest

USERNAME = "testuser"
APIKEY = "testkey"
PATH = "/dns/example.com/listRRs"


class FakeResponse:
    def __init__(self, text="[]", payload=None):
        self.text = text
        self._payload = payload if payload is not None else []

    def json(self):
        return self._payload


@pytest.fixture
def posts(api, monkeypatch):
    """Capture outgoing requests and control what the API answers with."""

    class Recorder:
        def __init__(self):
            self.requests = []
            self.response = FakeResponse()

        def post(self, url, data=None, headers=None):
            self.requests.append({"url": url, "data": data, "headers": headers})
            return self.response

        @property
        def last(self):
            return self.requests[-1]

        def body(self):
            return parse_qs(self.last["data"] or "")

        def answer_with(self, payload):
            self.response = FakeResponse(text="nonempty", payload=payload)

    recorder = Recorder()
    monkeypatch.setattr(api.requests, "post", recorder.post)
    return recorder


class TestRandomRangeString:

    def test_has_the_requested_length(self, api):
        assert len(api.randomRangeString(16)) == 16

    def test_contains_only_alphanumerics(self, api):
        assert api.randomRangeString(64).isalnum()

    def test_successive_calls_differ(self, api):
        assert api.randomRangeString(16) != api.randomRangeString(16)


class TestAuthHeader:
    """https://members.nearlyfreespeech.net/wiki/API/Introduction"""

    def header(self, api, body=""):
        return api.createNFSNAuthHeader(USERNAME, APIKEY, PATH, body)["X-NFSN-Authentication"]

    def test_header_has_the_four_semicolon_separated_fields(self, api):
        assert len(self.header(api).split(";")) == 4

    def test_header_starts_with_the_username(self, api):
        assert self.header(api).split(";")[0] == USERNAME

    def test_salt_is_sixteen_characters(self, api):
        assert len(self.header(api).split(";")[2]) == 16

    def test_timestamp_is_a_unix_epoch_second(self, api):
        timestamp = int(self.header(api).split(";")[1])
        # Sanity bounds rather than a clock comparison: after 2020, before 2100.
        assert 1577836800 < timestamp < 4102444800

    @pytest.mark.parametrize("body", ["", "name=home&type=A"])
    def test_hash_matches_the_documented_algorithm(self, api, body):
        username, timestamp, salt, digest = self.header(api, body).split(";")

        body_hash = hashlib.sha1(body.encode("utf-8")).hexdigest()
        expected = hashlib.sha1(
            f"{username};{timestamp};{salt};{APIKEY};{PATH};{body_hash}".encode("utf-8")
        ).hexdigest()

        assert digest == expected

    def test_a_missing_body_hashes_as_the_empty_string(self, api):
        empty_sha1 = hashlib.sha1(b"").hexdigest()
        username, timestamp, salt, digest = self.header(api, None).split(";")

        expected = hashlib.sha1(
            f"{username};{timestamp};{salt};{APIKEY};{PATH};{empty_sha1}".encode("utf-8")
        ).hexdigest()

        assert digest == expected

    def test_each_request_gets_a_fresh_salt(self, api):
        assert self.header(api).split(";")[2] != self.header(api).split(";")[2]


class TestHTTPRequest:

    def test_posts_to_the_nfsn_api_domain(self, api, posts):
        api.makeNFSNHTTPRequest(PATH, None, USERNAME, APIKEY)
        assert posts.last["url"] == "https://api.nearlyfreespeech.net" + PATH

    def test_sends_the_form_encoded_content_type(self, api, posts):
        api.makeNFSNHTTPRequest(PATH, None, USERNAME, APIKEY)
        assert posts.last["headers"]["Content-Type"] == "application/x-www-form-urlencoded"

    def test_sends_the_authentication_header(self, api, posts):
        api.makeNFSNHTTPRequest(PATH, None, USERNAME, APIKEY)
        assert posts.last["headers"]["X-NFSN-Authentication"].startswith(USERNAME + ";")

    def test_returns_the_parsed_response(self, api, posts):
        posts.answer_with([{"data": "203.0.113.7"}])
        assert api.makeNFSNHTTPRequest(PATH, None, USERNAME, APIKEY) == [{"data": "203.0.113.7"}]

    def test_returns_an_empty_string_when_the_response_has_no_body(self, api, posts):
        posts.response = FakeResponse(text="")
        assert api.makeNFSNHTTPRequest(PATH, None, USERNAME, APIKEY) == ""


class TestFetchDNSRecordData:

    def test_queries_the_requested_name_and_type(self, api, posts):
        posts.answer_with([{"data": "203.0.113.7"}])
        api.fetchDNSRecordData("home", "example.com", "A", USERNAME, APIKEY)
        assert posts.body() == {"name": ["home"], "type": ["A"]}

    def test_uses_the_listrrs_endpoint(self, api, posts):
        posts.answer_with([{"data": "203.0.113.7"}])
        api.fetchDNSRecordData("home", "example.com", "A", USERNAME, APIKEY)
        assert posts.last["url"].endswith("/dns/example.com/listRRs")

    def test_returns_the_first_matching_record(self, api, posts):
        posts.answer_with([{"data": "203.0.113.7"}, {"data": "198.51.100.1"}])
        result = api.fetchDNSRecordData("home", "example.com", "A", USERNAME, APIKEY)
        assert result == "203.0.113.7"

    def test_returns_none_when_no_record_exists(self, api, posts):
        posts.answer_with([])
        assert api.fetchDNSRecordData("home", "example.com", "A", USERNAME, APIKEY) is None

    def test_a_bare_domain_queries_an_empty_name(self, api, posts):
        posts.answer_with([{"data": "203.0.113.7"}])
        api.fetchDNSRecordData(None, "example.com", "A", USERNAME, APIKEY)
        # urlencode drops nothing, so the empty name is sent explicitly.
        assert posts.last["data"] == "name=&type=A"


class TestRecordMutations:

    def test_add_uses_the_addrr_endpoint(self, api, posts):
        api.addDNSRecord("example.com", "home", "AAAA", "2001:db8::7", 3600, USERNAME, APIKEY)
        assert posts.last["url"].endswith("/dns/example.com/addRR")

    def test_add_sends_the_record_details(self, api, posts):
        api.addDNSRecord("example.com", "home", "AAAA", "2001:db8::7", 3600, USERNAME, APIKEY)
        assert posts.body() == {
            "name": ["home"], "type": ["AAAA"], "data": ["2001:db8::7"], "ttl": ["3600"],
        }

    def test_replace_uses_the_replacerr_endpoint(self, api, posts):
        api.replaceDNSRecord("example.com", "home", "A", "203.0.113.7", 300, USERNAME, APIKEY)
        assert posts.last["url"].endswith("/dns/example.com/replaceRR")

    def test_replace_sends_the_record_details(self, api, posts):
        api.replaceDNSRecord("example.com", "home", "A", "203.0.113.7", 300, USERNAME, APIKEY)
        assert posts.body() == {
            "name": ["home"], "type": ["A"], "data": ["203.0.113.7"], "ttl": ["300"],
        }

    def test_remove_uses_the_removerr_endpoint(self, api, posts):
        api.removeDNSRecord("example.com", "home", "A", "203.0.113.7", USERNAME, APIKEY)
        assert posts.last["url"].endswith("/dns/example.com/removeRR")

    def test_remove_does_not_send_a_ttl(self, api, posts):
        api.removeDNSRecord("example.com", "home", "A", "203.0.113.7", USERNAME, APIKEY)
        assert "ttl" not in posts.body()


class TestResponseValidation:

    @pytest.mark.parametrize("response", [None, "", []])
    def test_empty_responses_are_tolerated(self, api, response):
        api.validateNFSNResponse(response)  # must not raise

    def test_an_error_response_is_printed(self, api, capsys):
        api.validateNFSNResponse({"error": "Permission denied", "debug": "no such domain"})
        printed = capsys.readouterr().out
        assert "Permission denied" in printed
        assert "no such domain" in printed

    def test_an_error_inside_a_list_is_printed(self, api, capsys):
        api.validateNFSNResponse([{"error": "Permission denied", "debug": "details"}])
        assert "Permission denied" in capsys.readouterr().out

    def test_a_successful_response_prints_nothing(self, api, capsys):
        api.validateNFSNResponse([{"data": "203.0.113.7"}])
        assert capsys.readouterr().out == ""


class TestOutput:

    def test_message_is_prefixed_with_a_timestamp(self, api, capsys):
        api.output("hello", timestamp="26-01-01 00:00:00")
        assert capsys.readouterr().out == "26-01-01 00:00:00: hello\n"

    def test_message_type_is_included_when_given(self, api, capsys):
        api.output("boom", type_msg="ERROR", timestamp="26-01-01 00:00:00")
        assert capsys.readouterr().out == "26-01-01 00:00:00: ERROR: boom\n"
