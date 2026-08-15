import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _load_script(module_name, filename):
    """Import an entry point whose hyphenated filename is not a valid module name."""
    spec = importlib.util.spec_from_file_location(module_name, REPO_ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


nfsn_ddns = _load_script("nfsn_ddns", "nfsn-ddns.py")
nfsn_acme = _load_script("nfsn_acme", "nfsn-acme.py")

import nfsn_api as _nfsn_api  # noqa: E402  (must follow the sys.path insert above)

# nfsn_api calls load_dotenv() at import time, so a developer's real .env would
# otherwise leak into every test that reads configuration from the environment.
MANAGED_ENV_VARS = (
    "USERNAME",
    "API_KEY",
    "DOMAIN",
    "SUBDOMAIN",
    "ENABLE_IPV4",
    "ENABLE_IPV6",
    "IP_USE_DIG",
    "IP_PROVIDER",
    "IPV6_PROVIDER",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in MANAGED_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def ddns():
    return nfsn_ddns


@pytest.fixture
def acme():
    return nfsn_acme


@pytest.fixture
def api():
    return _nfsn_api


@pytest.fixture
def creds(monkeypatch):
    """Minimal valid configuration for the DDNS entry point."""
    monkeypatch.setenv("USERNAME", "testuser")
    monkeypatch.setenv("API_KEY", "testkey")
    monkeypatch.setenv("DOMAIN", "example.com")
    return {"username": "testuser", "apikey": "testkey", "domain": "example.com"}
