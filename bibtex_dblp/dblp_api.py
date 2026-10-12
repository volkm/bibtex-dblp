import json
import logging
import os
import re
from enum import Enum
from pathlib import Path
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import HTTPError
from requests_ratelimiter import LimiterSession
from urllib3.util import Retry

import bibtex_dblp.anubis_solver
import bibtex_dblp.dblp_data
from bibtex_dblp import __version__

#: Environment variables used to pass a browser-obtained Anubis cookie / User-Agent,
#: and to control the in-process proof-of-work solver.
ENV_AUTH_COOKIE = "BIBTEX_DBLP_ANUBIS_COOKIE"
ENV_USER_AGENT = "BIBTEX_DBLP_USER_AGENT"
ENV_SOLVE_CHALLENGE = "BIBTEX_DBLP_SOLVE_CHALLENGE"

DEFAULT_USER_AGENT = "bibtex-dblp/{} (+https://github.com/volkm/bibtex-dblp)".format(__version__)
#: DBLP's Anubis deployment issues a low-difficulty *decoy* challenge to User-Agents that don't
#: look like a browser, which it then rejects at submission regardless of whether the solver got
#: the proof-of-work right (confirmed with a clean A/B: DEFAULT_USER_AGENT -> HTTP 403 on
#: pass-challenge every time; this string -> a real, solvable challenge). So this, not
#: DEFAULT_USER_AGENT, is the fallback whenever auto-solving is enabled and no --user-agent / env
#: / cached UA was given - without it the solver cannot work out of the box. Do not "fix" this
#: back to the honest identifying string; see the DBLP bot protection section of the README.
BROWSER_LIKE_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
#: Time budget for the Anubis proof-of-work grind before falling back to the manual-cookie error.
CHALLENGE_SOLVE_TIMEOUT = 30

#: DBLP's three officially supported, kept-in-sync hosts (see
#: https://dblp.org/faq/Which+mirror+sites+exist+for+dblp.html). Older, externally maintained
#: mirrors are explicitly *not* kept in sync by the dblp team and are intentionally not included.
DBLP_MIRRORS = {
    "dblp.org": "https://dblp.org",
    "trier": "https://dblp.uni-trier.de",
    "dagstuhl": "https://dblp.dagstuhl.de",
}
#: Fixed priority order used when failing over from an unreachable mirror.
MIRROR_FAILOVER_ORDER = ["dblp.org", "trier", "dagstuhl"]


class InvalidDblpIdException(Exception):
    pass


class DblpApiError(Exception):
    """Raised when DBLP returns a response that cannot be processed as a search result."""


class DblpBotChallengeError(DblpApiError):
    """Raised when DBLP serves an Anubis bot-protection challenge instead of the requested data."""


def _looks_like_anubis(resp):
    """
    Heuristically detect an Anubis bot-protection challenge page.

    DBLP serves the Anubis (https://github.com/TecharoHQ/anubis) proof-of-work
    interstitial with HTTP 200 and an HTML body, which a scripted client cannot solve.
    Detection is by the interstitial's HTML markers and Anubis' ``X-Clacks-Overhead``
    header. The auth ``Set-Cookie`` is deliberately *not* used as a signal: DBLP names
    its cookies ``dblp_org-auth-<hash>`` / ``dblp_org-cookie-verification-<hash>`` and
    sends the ``-auth-`` one on *successful* responses too.
    :param resp: Response object.
    :return: True if the response looks like an Anubis challenge.
    """
    if "X-Clacks-Overhead" in resp.headers:
        return True
    body = resp.text[:4000].lower()
    markers = ['id="anubis"', "making sure you're not a bot", "/.within.website/", "anubis_version"]
    return any(marker in body for marker in markers)


def _challenge_message(session):
    """Return a helpful message for a hit Anubis wall, tailored to whether a cookie was supplied."""
    if getattr(session, "auth_cookie_provided", False):
        return f"DBLP's Anubis cookie is missing or expired. Solve the check again in your browser and refresh {ENV_AUTH_COOKIE} / --auth-cookie (see README)."
    return (
        f"DBLP is behind the Anubis bot-protection wall. Solve it once in a browser, copy the whole Cookie request header"
        f" and your User-Agent, and pass them via --auth-cookie / --user-agent or {ENV_AUTH_COOKIE} / {ENV_USER_AGENT} (see README)."
    )


def _anubis_cache_path(base_url):
    """Location of the cached Anubis cookie / User-Agent, scoped per DBLP host (a cookie minted
    for one host is not valid for another, so mirrors must not share a cache file)."""
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    host = urlparse(base_url).hostname or "unknown"
    return Path(base) / "bibtex-dblp" / "anubis-{}.json".format(host)


def _load_anubis_cache(base_url):
    """Read the cached ``{"cookie": ..., "user_agent": ...}`` for ``base_url``; ``{}`` if absent/unreadable."""
    try:
        with open(_anubis_cache_path(base_url), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_anubis_cache(base_url, cookie, user_agent):
    """Persist the cookie / User-Agent for ``base_url`` so the next invocation stays authenticated. Best-effort."""
    try:
        path = _anubis_cache_path(base_url)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"cookie": cookie, "user_agent": user_agent}, f)
        os.chmod(path, 0o600)
    except OSError:
        logging.debug("Could not write DBLP auth cache to %s", _anubis_cache_path(base_url), exc_info=True)


def _apply_auth_cookie(session, cookie_str, base_url):
    """
    Apply a browser ``Cookie:`` header (or ``name=value; name=value`` string) to the session.

    Every pair is set verbatim for the DBLP host; no assumptions about cookie names.
    """
    host = urlparse(base_url).hostname
    for part in cookie_str.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        name, _, value = part.partition("=")
        name, value = name.strip(), value.strip()
        if name:
            session.cookies.set(name, value, domain=host, path="/")


class BibFormat(Enum):
    """
    Format of DBLP bibtex.
    """

    condensed = "condensed"
    standard = "standard"
    crossref = "crossref"
    condensed_doi = "condensed_doi"

    def bib_url(self):
        """
        Get identifier of format for DBLP urls.
        :return:
        """
        if self is BibFormat.condensed:
            return "0"
        elif self is BibFormat.standard:
            return "1"
        elif self is BibFormat.crossref:
            return "2"
        elif self is BibFormat.condensed_doi:
            return "0"
        else:
            assert False

    def __str__(self):
        return self.value


class DblpSession:
    """
    Keeps track of session for DBLP.
    Needed for rate limiting.
    """

    def __init__(self, wait_time, dblp_base_url="https://dblp.org", auth_cookie=None, user_agent=None, solve_challenge=None, mirror_failover=True):
        """
        Create a session for DBLP.
        :param wait_time: Time in seconds to sleep before retrying.
        :param dblp_base_url: Base URL for DBLP, typically one of ``DBLP_MIRRORS``'s values.
        :param auth_cookie: Browser ``Cookie:`` header used to pass DBLP's Anubis bot wall.
            ``None`` falls back to the ``BIBTEX_DBLP_ANUBIS_COOKIE`` env var and then the cache
            file; an empty string forces "no cookie" (ignore env / cache). Applies per-host: if
            a mirror fail-over switches hosts, this is re-resolved (env/cache) for the new host.
        :param user_agent: User-Agent to send. Must match the browser the cookie was obtained
            with. ``None`` falls back to ``BIBTEX_DBLP_USER_AGENT``, then the cache file, then
            ``BROWSER_LIKE_USER_AGENT`` if auto-solving is enabled (required for the solver to get
            a real, passable challenge - see ``BROWSER_LIKE_USER_AGENT``) or the honest
            ``DEFAULT_USER_AGENT`` otherwise.
        :param solve_challenge: Whether to automatically solve an Anubis proof-of-work challenge
            in-process when one is hit. ``None`` falls back to the ``BIBTEX_DBLP_SOLVE_CHALLENGE``
            env var (any of ``0``/``false``/``no`` disables it), defaulting to enabled.
        :param mirror_failover: If a request fails with a connection-level error (not an HTTP
            error, not an Anubis challenge), automatically switch to the next official mirror in
            ``MIRROR_FAILOVER_ORDER`` and retry, for the rest of this session's lifetime.
        """
        self.wait_time = wait_time
        self.mirror_failover = mirror_failover
        self._auth_cookie_arg = auth_cookie
        self._user_agent_arg = user_agent

        self.session = LimiterSession(per_second=1.0 / wait_time, per_minute=60.0 / wait_time, burst=3)

        # DBLP's search API throws intermittent 5xx/429 responses (independent of Anubis);
        # retry a few times with back-off. raise_on_status=False keeps the familiar HTTPError
        # path (via raise_for_status) once retries are exhausted.
        retry = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset(["GET"]),
            backoff_factor=max(1.0, wait_time / 2),
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        if solve_challenge is None:
            env_val = os.environ.get(ENV_SOLVE_CHALLENGE)
            solve_challenge = env_val is None or env_val.strip().lower() not in ("0", "false", "no", "")
        self.solve_challenge_enabled = solve_challenge

        self._apply_host_auth(dblp_base_url)

    def _apply_host_auth(self, base_url):
        """(Re-)point the session at ``base_url`` and resolve/apply that host's cookie + User-Agent."""
        self.base_url = base_url
        self.publication_search_url = base_url + "/search/publ/api"
        self.publication_bibtex = base_url + "/rec/{key}.bib?param={bib_format}"

        cache = _load_anubis_cache(base_url)
        cookie = self._auth_cookie_arg
        if cookie is None:
            cookie = os.environ.get(ENV_AUTH_COOKIE)
        if cookie is None:
            cookie = cache.get("cookie")
        user_agent = self._user_agent_arg or os.environ.get(ENV_USER_AGENT) or cache.get("user_agent")
        if not user_agent:
            user_agent = BROWSER_LIKE_USER_AGENT if self.solve_challenge_enabled else DEFAULT_USER_AGENT

        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "application/json",
            }
        )

        self.auth_cookie_provided = bool(cookie)
        if cookie:
            _apply_auth_cookie(self.session, cookie, base_url)
        self._persisted_cookie = None  # force a fresh persist for this (possibly new) host

    def _persist_auth(self, response):
        """After a successful non-challenge response, cache the (possibly refreshed) cookies + UA."""
        try:
            pairs = ["{}={}".format(c.name, c.value) for c in self.session.cookies]
            if not pairs:
                return
            cookie_str = "; ".join(pairs)
            if cookie_str == getattr(self, "_persisted_cookie", None):
                return  # unchanged since last write
            _save_anubis_cache(self.base_url, cookie_str, self.session.headers.get("User-Agent"))
            self._persisted_cookie = cookie_str
        except Exception:  # never let cache bookkeeping break a request
            logging.debug("Could not persist DBLP auth cookies", exc_info=True)

    def _failover(self, url, params, kwargs, last_err):
        """Switch to the next reachable official mirror and retry; re-raise if none work (or disabled)."""
        if not self.mirror_failover:
            raise last_err
        original_base = self.base_url
        tried = {original_base}
        for name in MIRROR_FAILOVER_ORDER:
            candidate = DBLP_MIRRORS[name]
            if candidate in tried:
                continue
            tried.add(candidate)
            new_url = url.replace(original_base, candidate, 1)
            self._apply_host_auth(candidate)
            logging.warning("DBLP mirror %s unreachable (%s); switching to %s.", original_base, last_err, candidate)
            try:
                return new_url, self.session.get(new_url, params=params, **kwargs)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as err:
                last_err = err
                continue
        raise last_err

    def perform_request(self, url, params=None, **kwargs):
        """
        Perform a GET request to DBLP.
        :param url: URL to access.
        :param params: Optional parameters.
        :param kwargs: Optional arguments.
        :return: Response.
        :raises: HTTPError if request was unsuccessful.
        """
        try:
            response = self.session.get(url, params=params, **kwargs)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as err:
            url, response = self._failover(url, params, kwargs, err)

        if _looks_like_anubis(response) and self.solve_challenge_enabled:
            if bibtex_dblp.anubis_solver.solve_challenge(self.session, response, response.url, max_seconds=CHALLENGE_SOLVE_TIMEOUT):
                self._persist_auth(response)  # response arg is unused by _persist_auth; it reads the live cookie jar
                response = self.session.get(url, params=params, **kwargs)
        if response.ok and "Set-Cookie" in response.headers and not _looks_like_anubis(response):
            self._persist_auth(response)
        response.raise_for_status()
        return response


def add_auth_arguments(parser):
    """Add the shared --mirror / --no-mirror-failover / --auth-cookie / --no-auth-cookie /
    --user-agent / --no-solve-challenge options."""
    parser.add_argument(
        "--mirror",
        choices=sorted(DBLP_MIRRORS),
        default="dblp.org",
        help="Which official dblp mirror to start with (see "
        "https://dblp.org/faq/Which+mirror+sites+exist+for+dblp.html). All mirrors sit behind the same Anubis bot wall.",
    )
    parser.add_argument(
        "--no-mirror-failover",
        dest="mirror_failover",
        action="store_false",
        default=True,
        help="Don't automatically switch to another mirror if the selected one is unreachable.",
    )
    parser.add_argument(
        "--auth-cookie",
        dest="auth_cookie",
        default=None,
        help="Browser 'Cookie:' header used to pass DBLP's Anubis bot wall (or set the {} "
        "environment variable). See the README section 'DBLP bot protection (Anubis)'.".format(ENV_AUTH_COOKIE),
    )
    parser.add_argument(
        "--no-auth-cookie",
        dest="auth_cookie",
        action="store_const",
        const="",
        help="Ignore any Anubis cookie from {} or the cache file.".format(ENV_AUTH_COOKIE),
    )
    parser.add_argument(
        "--user-agent",
        dest="user_agent",
        default=None,
        help="User-Agent to send; must match the browser the --auth-cookie was copied from " "(or set the {} environment variable).".format(ENV_USER_AGENT),
    )
    parser.add_argument(
        "--no-solve-challenge",
        dest="solve_challenge",
        action="store_false",
        default=None,
        help="Don't try to solve DBLP's Anubis proof-of-work challenge automatically; just report "
        "it (or set {} to disable by default).".format(ENV_SOLVE_CHALLENGE),
    )


def session_from_args(args):
    """Build a :class:`DblpSession` from parsed CLI args (``sleep_time``, ``mirror``,
    ``mirror_failover``, ``auth_cookie``, ``user_agent``, ``solve_challenge``)."""
    return DblpSession(
        wait_time=args.sleep_time,
        dblp_base_url=DBLP_MIRRORS[getattr(args, "mirror", "dblp.org")],
        mirror_failover=getattr(args, "mirror_failover", True),
        auth_cookie=getattr(args, "auth_cookie", None),
        user_agent=getattr(args, "user_agent", None),
        solve_challenge=getattr(args, "solve_challenge", None),
    )


def extract_dblp_id(entry):
    """
    Extract DBLP id by either using the biburl if given or trying to use the entry name.
    :param entry: Bibliography entry.
    :return: DBLP id or None if no could be extracted.
    """
    if "biburl" in entry.fields:
        # Try to get id from biburl
        match = re.search(r"http(s?)://dblp.org/rec/(.*).bib", entry.fields["biburl"])
        if match:
            return match.group(2)

    # Try to get id from entry name
    key = entry.key
    if key.startswith("DBLP:"):
        return key[5:]
    return None


def get_bibtex(session, dblp_id, bib_format=BibFormat.condensed):
    """
    Get bibtex entry in specified format.
    :param session: DBLP session.
    :param dblp_id: DBLP id for entry.
    :param bib_format: Format of bibtex export (see BibFormat).
    :return: Bibtex as binary string.
    """
    try:
        resp = session.perform_request(session.publication_bibtex.format(key=dblp_id, bib_format=bib_format.bib_url()))
    except HTTPError as err:
        if err.response.status_code == 404:
            raise InvalidDblpIdException("Invalid DBLP id '{}'".format(dblp_id))
        else:
            raise err

    if _looks_like_anubis(resp):
        raise DblpBotChallengeError(_challenge_message(session))

    bibtex = resp.content.decode("utf-8")

    if bib_format == BibFormat.condensed_doi:
        # Also get DOI and insert it into bibtex
        resp = session.perform_request(session.publication_bibtex.format(key=dblp_id, bib_format=BibFormat.standard.bib_url()))
        lines = resp.content.decode("utf-8").split("\n")
        keep_lines = [line for line in lines if line.startswith("  doi")]
        assert len(keep_lines) <= 1
        if keep_lines:
            doi = keep_lines[0][:-1]  # Remove comma
            # Insert into bibtex
            bibtex = bibtex[:-4] + ",\n" + doi + bibtex[-4:]

    if bib_format == BibFormat.condensed or bib_format == BibFormat.condensed_doi:
        # Also insert biburl into bibtex
        assert "biburl" not in bibtex
        biburl = "  biburl = {{https://dblp.org/rec/{}.bib}}".format(dblp_id)
        bibtex = bibtex[:-4] + ",\n" + biburl + bibtex[-4:]

    return bibtex


def search_publication(session, pub_query, max_search_results):
    """
    Search for publication according to given query.
    :param session: DBLP session.
    :param pub_query: Query for publication.
    :param max_search_results: Maximal number of search results to return.
    :return: Search results.
    """
    parameters = dict(q=pub_query, format="json", h=max_search_results)

    resp = session.perform_request(session.publication_search_url, params=parameters)
    try:
        payload = resp.json()
    except ValueError as err:
        if _looks_like_anubis(resp):
            raise DblpBotChallengeError(_challenge_message(session)) from None
        raise DblpApiError(
            "DBLP returned a non-JSON response (HTTP {}, content-type {}).".format(resp.status_code, resp.headers.get("Content-Type", "?"))
        ) from err
    logging.debug("DBLP response body (first 300 chars): %s", resp.text[:300])
    results = bibtex_dblp.dblp_data.DblpSearchResults(payload)
    assert results.status_code == 200
    return results
