import hashlib
import json
from unittest import mock

import bibtex_dblp.anubis_solver as solver


class _FakeChallengeResponse:
    """Minimal stand-in for the Response carrying the Anubis challenge HTML."""

    def __init__(self, text, url="https://dblp.org/search/publ/api?q=x"):
        self.text = text
        self.url = url


class _FakeSubmitResponse:
    """Minimal stand-in for the Response to the pass-challenge submission."""

    def __init__(self, ok=True, status_code=200, text="ok", headers=None):
        self.ok = ok
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}


def _challenge_html(difficulty=1, random_data="deadbeef", challenge_id="test-id-123"):
    payload = {"rules": {"algorithm": "fast", "difficulty": difficulty}, "challenge": {"id": challenge_id, "randomData": random_data}}
    return '<html><body><script id="anubis_challenge" type="application/json">{}</script></body></html>'.format(json.dumps(payload))


def test_solve_challenge_success(monkeypatch):
    monkeypatch.setattr(solver, "_MIN_SOLVE_SECONDS", 0)
    challenge_response = _FakeChallengeResponse(_challenge_html(difficulty=1, random_data="deadbeef"))
    session = mock.Mock()
    session.get.return_value = _FakeSubmitResponse(ok=True, status_code=200, text="ok", headers={})

    result = solver.solve_challenge(session, challenge_response, "https://dblp.org/search/publ/api?q=x", max_seconds=5)

    assert result is True
    session.get.assert_called_once()
    args, kwargs = session.get.call_args
    assert args[0] == "https://dblp.org/.within.website/x/cmd/anubis/api/pass-challenge"
    params = kwargs["params"]
    assert params["id"] == "test-id-123"
    assert params["redir"] == "https://dblp.org/search/publ/api?q=x"
    digest = hashlib.sha256(("deadbeef" + params["nonce"]).encode()).hexdigest()
    assert digest == params["response"]
    assert digest.startswith("0")


def test_solve_challenge_malformed_html_returns_false():
    challenge_response = _FakeChallengeResponse("<html><body>no challenge script here</body></html>")
    session = mock.Mock()

    assert solver.solve_challenge(session, challenge_response, "https://dblp.org/x") is False
    session.get.assert_not_called()


def test_solve_challenge_gives_up_on_timeout():
    # Difficulty high enough that it won't be found within one grind-check interval.
    challenge_response = _FakeChallengeResponse(_challenge_html(difficulty=10))
    session = mock.Mock()

    assert solver.solve_challenge(session, challenge_response, "https://dblp.org/x", max_seconds=0.001) is False
    session.get.assert_not_called()


def test_solve_challenge_rejected_submission_returns_false(monkeypatch):
    monkeypatch.setattr(solver, "_MIN_SOLVE_SECONDS", 0)
    challenge_response = _FakeChallengeResponse(_challenge_html(difficulty=1))
    session = mock.Mock()
    session.get.return_value = _FakeSubmitResponse(ok=False, status_code=403, text="insufficient time.", headers={})

    assert solver.solve_challenge(session, challenge_response, "https://dblp.org/x") is False
