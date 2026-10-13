import datetime
import hashlib
import types

import bibtex_dblp.anubis as anubis

CHALLENGE_HTML = """<!doctype html><html><head><title>Making sure you're not a bot!</title></head>
<body>
<script id="anubis_version" type="application/json">
    "v1.27.0"
</script>
<script id="anubis_challenge" type="application/json">
    {"rules":{"algorithm":"fast","difficulty":3},"challenge":{"id":"test-id","method":"fast","randomData":"3601e58d314435a2c268f7a7bc01f9be480acb6578bec419053e8e000d4322cd"}}
</script>
<script id="anubis_base_prefix" type="application/json">
    ""
</script>
<script src="/.within.website/x/cmd/anubis/static/js/main.mjs"></script>
</body></html>
"""

CHALLENGE_RESPONSE = types.SimpleNamespace(
    status_code=202,
    headers={"content-type": "text/html; charset=utf-8"},
    text=CHALLENGE_HTML,
    url="https://dblp.org/search/publ/api?q=test&format=json&h=1",
)

METAREFRESH_HTML = """<!doctype html><html><body>
<script id="anubis_challenge" type="application/json">
    {"rules":{"algorithm":"metarefresh","difficulty":1},"challenge":{"id":"mr-id","issuedAt":"2000-01-01T00:00:00+00:00","randomData":"deadbeef"}}
</script>
<script id="anubis_base_prefix" type="application/json">""</script>
<script src="/.within.website/x/cmd/anubis/static/js/main.mjs"></script>
</body></html>
"""

METAREFRESH_RESPONSE = types.SimpleNamespace(
    status_code=202,
    headers={"content-type": "text/html; charset=utf-8"},
    text=METAREFRESH_HTML,
    url="https://dblp.org/search/publ/api?q=test&format=json&h=1",
)

BIBTEX_RESPONSE = types.SimpleNamespace(
    status_code=200,
    headers={"content-type": "text/plain"},
    text="@article{DBLP:journals/tcs/GrooteW05,\n  title = {Parameterised boolean equation systems}\n}\n",
    url="https://dblp.org/rec/journals/tcs/GrooteW05.bib?param=0",
)


def test_is_anubis_challenge():
    assert anubis.is_challenge(CHALLENGE_RESPONSE)
    assert not anubis.is_challenge(BIBTEX_RESPONSE)


def test_extract_json_script():
    challenge = anubis._extract_json_script(CHALLENGE_RESPONSE, "anubis_challenge")
    assert challenge["challenge"]["id"] == "test-id"
    assert challenge["rules"]["difficulty"] == 3
    assert anubis._extract_json_script(CHALLENGE_RESPONSE, "does_not_exist") is None


def test_solve_proof_of_work():
    random_data = "3601e58d314435a2c268f7a7bc01f9be480acb6578bec419053e8e000d4322cd"
    digest, nonce = anubis.solve_proof_of_work(random_data, difficulty=3)
    assert digest.startswith("000")
    assert digest == hashlib.sha256((random_data + str(nonce)).encode("utf-8")).hexdigest()


def test_solve_proof_of_work_parameters():
    random_data = "ab" * 32
    params = anubis._solve_proof_of_work({"id": "test-id", "randomData": random_data}, difficulty=2)
    assert params["id"] == "test-id"
    assert params["response"].startswith("00")
    assert params["response"] == hashlib.sha256((random_data + params["nonce"]).encode("utf-8")).hexdigest()


def test_solve_metarefresh_parameters():
    random_data = "ab" * 32
    issued_at = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)).isoformat()
    data = {"id": "test-id", "randomData": random_data, "issuedAt": issued_at}
    params = anubis._solve_metarefresh(data, difficulty=5)
    assert params == {"id": "test-id", "challenge": random_data}


def test_solve_anubis_challenge_metarefresh():
    call = {}

    class FakeSession:
        def get(self, url, params=None, **kwargs):
            call["url"] = url
            call["params"] = params
            call["allow_redirects"] = kwargs.get("allow_redirects")
            return types.SimpleNamespace(status_code=200, raise_for_status=lambda: None)

    anubis.solve(METAREFRESH_RESPONSE, FakeSession())

    assert call["url"] == "https://dblp.org/.within.website/x/cmd/anubis/api/pass-challenge"
    assert call["params"]["id"] == "mr-id"
    assert call["params"]["challenge"] == "deadbeef"
    assert call["params"]["redir"] == METAREFRESH_RESPONSE.url
    assert call["allow_redirects"] is False
