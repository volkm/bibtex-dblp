import json
from unittest import mock

import pytest
import requests

import bibtex_dblp.dblp_api
from bibtex_dblp.dblp_api import DBLP_MIRRORS, BibFormat, DblpApiError, DblpBotChallengeError


class _FakeResponse:
    """Minimal stand-in for a requests.Response used to test non-JSON handling offline."""

    def __init__(self, text, headers=None, status_code=200):
        self.text = text
        self.content = text.encode("utf-8")
        self.headers = headers or {}
        self.status_code = status_code

    def json(self):
        return json.loads(self.text)


def test_search_publication_anubis_challenge(dblp_session):
    challenge_page = (
        "<html><head><title>Making sure you're not a bot!</title></head>"
        '<body><div id="anubis"></div>'
        '<script src="/.within.website/x/cmd/anubis/static/js/main.mjs"></script></body></html>'
    )
    fake = _FakeResponse(challenge_page, headers={"Content-Type": "text/html; charset=utf-8"})
    with mock.patch.object(dblp_session, "perform_request", return_value=fake):
        with pytest.raises(DblpBotChallengeError):
            bibtex_dblp.dblp_api.search_publication(dblp_session, "Knuth Art", max_search_results=30)


def test_search_publication_non_json(dblp_session):
    fake = _FakeResponse("<html><body>502 Bad Gateway</body></html>", headers={"Content-Type": "text/html"})
    with mock.patch.object(dblp_session, "perform_request", return_value=fake):
        with pytest.raises(DblpApiError) as excinfo:
            bibtex_dblp.dblp_api.search_publication(dblp_session, "Knuth Art", max_search_results=30)
    assert not isinstance(excinfo.value, DblpBotChallengeError)


# --- Anubis cookie / User-Agent handling (offline) ---------------------------------

_CHALLENGE_HTML = "<html><head><title>Making sure you're not a bot!</title></head>" '<body><div id="anubis"></div></body></html>'


def _make_session(**kwargs):
    return bibtex_dblp.dblp_api.DblpSession(wait_time=7, **kwargs)


@pytest.fixture(autouse=True)
def _isolate_anubis_cache(monkeypatch, tmp_path):
    """Keep every test in this module away from the real ~/.cache and env cookie."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    monkeypatch.delenv("BIBTEX_DBLP_ANUBIS_COOKIE", raising=False)
    monkeypatch.delenv("BIBTEX_DBLP_USER_AGENT", raising=False)


def test_auth_cookie_full_header_applied():
    session = _make_session(auth_cookie="dblp_org-auth-ab12=tok.v-x; dblp_org-cookie-verification-ab12=vvv")
    jar = session.session.cookies
    assert jar.get("dblp_org-auth-ab12") == "tok.v-x"
    assert jar.get("dblp_org-cookie-verification-ab12") == "vvv"
    assert session.auth_cookie_provided is True


def test_auth_cookie_from_env(monkeypatch):
    monkeypatch.setenv("BIBTEX_DBLP_ANUBIS_COOKIE", "dblp_org-auth-zz=fromenv")
    session = _make_session()
    assert session.session.cookies.get("dblp_org-auth-zz") == "fromenv"


def test_no_auth_cookie_overrides_env(monkeypatch):
    monkeypatch.setenv("BIBTEX_DBLP_ANUBIS_COOKIE", "dblp_org-auth-zz=fromenv")
    session = _make_session(auth_cookie="")
    assert len(session.session.cookies) == 0
    assert session.auth_cookie_provided is False


def test_user_agent_default_and_override():
    # Default (auto-solving on): a browser-like UA, needed for the solver to get a real,
    # passable challenge rather than DBLP's unsolvable decoy for script-looking UAs.
    assert _make_session().session.headers["User-Agent"] == bibtex_dblp.dblp_api.BROWSER_LIKE_USER_AGENT
    assert _make_session(user_agent="Mozilla/5.0 Custom").session.headers["User-Agent"] == "Mozilla/5.0 Custom"


def test_user_agent_default_is_honest_when_solving_disabled():
    session = _make_session(solve_challenge=False)
    assert session.session.headers["User-Agent"].startswith("bibtex-dblp/")


def test_challenge_error_mentions_refresh_when_cookie_present():
    session = _make_session(auth_cookie="dblp_org-auth-ab=tok")
    challenge = _FakeResponse(_CHALLENGE_HTML, headers={"Content-Type": "text/html"})
    with mock.patch.object(session, "perform_request", return_value=challenge):
        with pytest.raises(DblpBotChallengeError) as excinfo:
            bibtex_dblp.dblp_api.search_publication(session, "Knuth Art", max_search_results=30)
    assert "expired" in str(excinfo.value)


def test_challenge_error_points_to_readme_without_cookie():
    session = _make_session(auth_cookie="")
    challenge = _FakeResponse(_CHALLENGE_HTML, headers={"Content-Type": "text/html"})
    with mock.patch.object(session, "perform_request", return_value=challenge):
        with pytest.raises(DblpBotChallengeError) as excinfo:
            bibtex_dblp.dblp_api.search_publication(session, "Knuth Art", max_search_results=30)
    assert "--auth-cookie" in str(excinfo.value)


def test_refreshed_cookie_is_persisted(tmp_path):
    session = _make_session(auth_cookie="dblp_org-auth-ab=old", user_agent="BrowserUA/9")
    session.session.cookies.set("dblp_org-auth-ab", "new", domain="dblp.org", path="/")

    ok = _FakeResponse('{"result": {}}', headers={"Set-Cookie": "dblp_org-auth-ab=new", "Content-Type": "application/json"})
    ok.ok = True
    ok.raise_for_status = lambda: None
    monkeypatch_get = mock.patch.object(session.session, "get", return_value=ok)
    with monkeypatch_get:
        session.perform_request("https://dblp.org/whatever")

    cached = json.loads((tmp_path / "bibtex-dblp" / "anubis-dblp.org.json").read_text())
    assert cached["cookie"] == "dblp_org-auth-ab=new"
    assert cached["user_agent"] == "BrowserUA/9"


def test_retry_adapter_configured_for_flaky_5xx():
    retry = _make_session().session.get_adapter("https://dblp.org/").max_retries
    assert retry.total == 3
    assert {429, 500, 502, 503, 504} <= set(retry.status_forcelist)
    assert retry.raise_on_status is False


# --- DBLP mirrors (offline) ---------------------------------------------------------


def test_anubis_cache_path_is_per_host():
    p1 = bibtex_dblp.dblp_api._anubis_cache_path("https://dblp.org")
    p2 = bibtex_dblp.dblp_api._anubis_cache_path("https://dblp.uni-trier.de")
    assert p1 != p2
    assert "dblp.org" in p1.name
    assert "dblp.uni-trier.de" in p2.name


def test_cached_cookie_not_shared_across_mirrors():
    session = _make_session(auth_cookie="dblp_org-auth-x=tok", user_agent="BrowserUA/1")
    session.session.cookies.set("dblp_org-auth-x", "fresh", domain="dblp.org", path="/")
    ok = _FakeResponse('{"result": {}}', headers={"Set-Cookie": "dblp_org-auth-x=fresh", "Content-Type": "application/json"})
    ok.ok = True
    ok.raise_for_status = lambda: None
    with mock.patch.object(session.session, "get", return_value=ok):
        session.perform_request("https://dblp.org/whatever")

    # A fresh session for a different mirror, with no explicit cookie, must not see dblp.org's.
    other = _make_session(dblp_base_url=DBLP_MIRRORS["trier"])
    assert other.auth_cookie_provided is False
    assert len(other.session.cookies) == 0


def _fake_ok_response(url):
    resp = _FakeResponse('{"result": {}}', headers={"Content-Type": "application/json"})
    resp.ok = True
    resp.url = url
    resp.raise_for_status = lambda: None
    return resp


def test_perform_request_fails_over_to_next_mirror():
    session = _make_session()
    calls = []

    def fake_get(url, params=None, **kwargs):
        calls.append(url)
        if url.startswith(DBLP_MIRRORS["dblp.org"]):
            raise requests.exceptions.ConnectionError("boom")
        return _fake_ok_response(url)

    with mock.patch.object(session.session, "get", side_effect=fake_get):
        resp = session.perform_request("https://dblp.org/search/publ/api", params={"q": "x"})

    assert resp.status_code == 200
    assert session.base_url == DBLP_MIRRORS["trier"]
    assert calls[0].startswith(DBLP_MIRRORS["dblp.org"])
    assert calls[1].startswith(DBLP_MIRRORS["trier"])


def test_perform_request_failover_exhausted_raises_original_error():
    session = _make_session()

    def always_fail(url, params=None, **kwargs):
        raise requests.exceptions.ConnectionError("still down")

    with mock.patch.object(session.session, "get", side_effect=always_fail):
        with pytest.raises(requests.exceptions.ConnectionError):
            session.perform_request("https://dblp.org/search/publ/api", params={"q": "x"})


def test_perform_request_no_failover_when_disabled():
    session = _make_session(mirror_failover=False)
    mock_get = mock.Mock(side_effect=requests.exceptions.ConnectionError("down"))
    with mock.patch.object(session.session, "get", mock_get):
        with pytest.raises(requests.exceptions.ConnectionError):
            session.perform_request("https://dblp.org/search/publ/api", params={"q": "x"})
    assert mock_get.call_count == 1


def test_search_publication(dblp_session):
    search_string = "Output-sensitive autocompletion search"
    search_results = bibtex_dblp.dblp_api.search_publication(dblp_session, search_string, max_search_results=30)
    assert search_results.total_matches == 2
    for i in range(len(search_results.results)):
        result = search_results.results[i].publication
        if result.doi == "10.1007/S10791-008-9048-X":
            assert result.title == "Output-sensitive autocompletion search."
            assert result.booktitle is None
            assert result.volume == "11"
            assert result.venue == "Inf. Retr."
            assert result.pages == "269-286"
            assert result.year == 2008
            assert result.type == "Journal Articles"
            assert result.key == "journals/ir/BastMW08"
            assert result.doi == "10.1007/S10791-008-9048-X"
            assert result.ee == "https://doi.org/10.1007/s10791-008-9048-x"
            assert result.url == "https://dblp.org/rec/journals/ir/BastMW08"
            authors = [author.name for author in result.authors]
            assert "Hannah Bast" in authors
            assert "Christian Worm Mortensen" in authors
            assert "Ingmar Weber" in authors
        else:
            assert result.doi == "10.1007/11880561_13"


def test_dblp_bibtex(dblp_session):
    search_string = "Output-sensitive autocompletion search"
    search_results = bibtex_dblp.dblp_api.search_publication(dblp_session, search_string, max_search_results=30)
    assert search_results.total_matches == 2
    result = search_results.results[1].publication
    assert result.doi == "10.1007/11880561_13"

    bibtex_standard = bibtex_dblp.dblp_api.get_bibtex(dblp_session, result.key, bib_format=BibFormat.standard)
    assert "booktitle    = {String Processing and Information Retrieval, 13th International Conference," in bibtex_standard
    assert "{SPIRE} 2006, Glasgow, UK, October 11-13, 2006, Proceedings}" in bibtex_standard

    bibtex_crossref = bibtex_dblp.dblp_api.get_bibtex(dblp_session, result.key, bib_format=BibFormat.crossref)
    assert "crossref     = {DBLP:conf/spire/2006}," in bibtex_crossref
    assert "editor " in bibtex_crossref

    bibtex_condensed = bibtex_dblp.dblp_api.get_bibtex(dblp_session, result.key, bib_format=BibFormat.condensed)
    assert "booktitle    = {{SPIRE}}" in bibtex_condensed
    assert "doi" not in bibtex_condensed

    bibtex_condensed_doi = bibtex_dblp.dblp_api.get_bibtex(dblp_session, result.key, bib_format=BibFormat.condensed_doi)
    assert "booktitle    = {{SPIRE}}" in bibtex_condensed_doi
    assert "doi          = {10.1007/11880561\\_13}" in bibtex_condensed_doi
