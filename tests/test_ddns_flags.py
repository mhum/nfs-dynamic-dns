import pytest


def test_env_flag_falls_back_to_default_when_unset(ddns):
    assert ddns.env_flag("ENABLE_IPV6", default=False) is False
    assert ddns.env_flag("ENABLE_IPV6", default=True) is True


@pytest.mark.parametrize("value", ["true", "TRUE", "1", "yes", "on", "anything"])
def test_env_flag_treats_affirmative_values_as_enabled(ddns, monkeypatch, value):
    monkeypatch.setenv("ENABLE_IPV6", value)
    assert ddns.env_flag("ENABLE_IPV6", default=False) is True


@pytest.mark.parametrize("value", ["false", "FALSE", "0", "no", "off", "", "  "])
def test_env_flag_treats_negative_values_as_disabled(ddns, monkeypatch, value):
    monkeypatch.setenv("ENABLE_IPV6", value)
    assert ddns.env_flag("ENABLE_IPV6", default=True) is False


def test_env_flag_ignores_surrounding_whitespace(ddns, monkeypatch):
    monkeypatch.setenv("ENABLE_IPV6", "  false  ")
    assert ddns.env_flag("ENABLE_IPV6", default=True) is False
