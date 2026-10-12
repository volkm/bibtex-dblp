"""
Solve DBLP's Anubis (https://github.com/TecharoHQ/anubis) proof-of-work bot-wall
challenge in-process, as a fallback for when no browser-obtained cookie
(see ``DblpSession(auth_cookie=...)``) is available or it has expired.

The algorithm here is not guessed: it was read out of Anubis' own served
JavaScript (``main.mjs`` plus ``worker/sha256-{webcrypto,purejs}.mjs``) and
verified end-to-end against a live DBLP challenge.

- The challenge interstitial embeds
  ``<script id="anubis_challenge" type="application/json">{"rules":
  {"algorithm": "fast", "difficulty": N}, "challenge": {"id": "...",
  "randomData": "..."}}</script>``.
- The proof is the smallest ``nonce`` (starting at 0) such that
  ``sha256(randomData + str(nonce)).hexdigest()`` has ``difficulty`` leading
  hex-zero characters (Anubis checks this at the byte level; it is exactly
  equivalent to the hex-prefix check used here).
- Submitting ``id``, ``response`` (the digest), ``nonce``, ``redir`` and
  ``elapsedTime`` to ``/.within.website/x/cmd/anubis/api/pass-challenge`` makes
  Anubis set the real auth cookie on the session.

Live testing against DBLP also showed Anubis rejects a solve submitted "too
fast" (``"insufficient time."``) — observed on low-difficulty challenges solved
in under a millisecond. The exact threshold isn't published and wasn't fully
pinned down (repeated probing risks looking like abuse to the very system this
is meant to get past), so ``_MIN_SOLVE_SECONDS`` below is a conservative safety
margin, not a verified minimum. If DBLP still rejects a submission for any
reason, ``solve_challenge`` simply returns ``False`` and the caller falls back
to the existing manual-cookie error.
"""

import hashlib
import json
import logging
import re
import time
from urllib.parse import urljoin

_CHALLENGE_SCRIPT_RE = re.compile(r'<script id="anubis_challenge" type="application/json">(.*?)</script>', re.S)
_PASS_CHALLENGE_PATH = "/.within.website/x/cmd/anubis/api/pass-challenge"
_GRIND_CHECK_INTERVAL = 50000
#: Conservative floor on real elapsed time (challenge fetch -> submit) before
#: submitting a solution, to avoid DBLP's "insufficient time." rejection on
#: trivially-fast (low-difficulty) solves. See module docstring.
_MIN_SOLVE_SECONDS = 2.0


def _parse_challenge(html):
    """Extract ``(random_data, challenge_id, difficulty)`` from a challenge page, or ``None``."""
    match = _CHALLENGE_SCRIPT_RE.search(html)
    if not match:
        return None
    try:
        payload = json.loads(match.group(1))
        challenge = payload["challenge"]
        return challenge["randomData"], challenge["id"], int(payload["rules"]["difficulty"])
    except (KeyError, TypeError, ValueError):
        return None


def _grind(random_data, difficulty, max_seconds):
    """Find ``(nonce, hex digest)`` satisfying the proof-of-work, or ``None`` on timeout."""
    prefix = "0" * difficulty
    start = time.monotonic()
    nonce = 0
    while True:
        digest = hashlib.sha256((random_data + str(nonce)).encode()).hexdigest()
        if digest.startswith(prefix):
            return nonce, digest
        nonce += 1
        if nonce % _GRIND_CHECK_INTERVAL == 0 and time.monotonic() - start > max_seconds:
            return None


def solve_challenge(session, challenge_response, original_url, max_seconds=30):
    """
    Attempt to solve an Anubis proof-of-work challenge and leave the session authenticated.
    :param session: requests.Session that received the challenge; its cookie jar already
        holds the verification cookie and is updated in place with the real auth cookie.
    :param challenge_response: the Response carrying the challenge HTML.
    :param original_url: the URL that triggered the challenge (used as the ``redir`` target).
    :param max_seconds: time budget for the SHA-256 grind before giving up.
    :return: True if solving succeeded and the session now holds a valid auth cookie.
    """
    start = time.monotonic()
    parsed = _parse_challenge(challenge_response.text)
    if parsed is None:
        logging.debug("Anubis challenge page did not match the expected shape; cannot auto-solve.")
        return False
    random_data, challenge_id, difficulty = parsed

    solved = _grind(random_data, difficulty, max_seconds)
    if solved is None:
        logging.debug("Anubis proof-of-work not solved within %ss (difficulty %s); giving up.", max_seconds, difficulty)
        return False
    nonce, digest = solved

    # Pad out trivially-fast (low-difficulty) solves so the reported elapsed time
    # doesn't look suspiciously instant to DBLP's Anubis deployment (see module docstring).
    remaining = _MIN_SOLVE_SECONDS - (time.monotonic() - start)
    if remaining > 0:
        time.sleep(remaining)
    elapsed_ms = int((time.monotonic() - start) * 1000)

    pass_url = urljoin(challenge_response.url, _PASS_CHALLENGE_PATH)
    params = {
        "id": challenge_id,
        "response": digest,
        "nonce": str(nonce),
        "redir": original_url,
        "elapsedTime": str(elapsed_ms),
    }
    try:
        resp = session.get(pass_url, params=params, timeout=30)
    except Exception:
        logging.debug("Submitting the solved Anubis challenge failed.", exc_info=True)
        return False

    from bibtex_dblp.dblp_api import _looks_like_anubis  # local import avoids an import cycle

    if not resp.ok or _looks_like_anubis(resp):
        logging.debug("DBLP rejected the solved Anubis challenge (HTTP %s).", resp.status_code)
        return False
    logging.info("Solved DBLP's Anubis challenge (difficulty %s, %s ms).", difficulty, elapsed_ms)
    return True
