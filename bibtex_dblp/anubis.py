"""
Solve the Anubis proof-of-work bot protection used by DBLP.

See https://anubis.techaro.lol/ for details.
"""

import datetime
import hashlib
import json
import re
import time
import urllib.parse

ANUBIS_PATH_PREFIX = "/.within.website/x/cmd/anubis"
CHALLENGE_ELEMENT_ID = "anubis_challenge"
BASE_PREFIX_ELEMENT_ID = "anubis_base_prefix"


class AnubisChallengeException(Exception):
    pass


def is_challenge(response):
    """
    Check whether a response is an Anubis challenge.
    :param response: Response.
    :return: True if the response is a challenge.
    """
    if response.status_code != 202 or "html" not in response.headers.get("content-type", ""):
        return False
    return ANUBIS_PATH_PREFIX in response.text and 'id="{}"'.format(CHALLENGE_ELEMENT_ID) in response.text


def solve(response, session):
    """
    Solve the challenge in the given response and store the authorization cookie in the session.
    :param response: Response containing the challenge.
    :param session: Requests session used for the pass-challenge request.
    :raises: AnubisChallengeException if the challenge cannot be parsed or solved.
    """
    challenge = _extract_json_script(response, CHALLENGE_ELEMENT_ID)
    if challenge is None:
        raise AnubisChallengeException("Could not parse DBLP bot protection challenge.")

    rules = challenge["rules"]
    data = challenge["challenge"]
    algorithm = rules.get("algorithm", "fast")
    difficulty = rules["difficulty"]

    if algorithm == "metarefresh":
        parameters = _solve_metarefresh(data, difficulty)
    elif algorithm in ("fast", "slow"):
        parameters = _solve_proof_of_work(data, difficulty)
    else:
        raise AnubisChallengeException("Unsupported DBLP bot protection algorithm '{}'.".format(algorithm))

    base_prefix = _extract_json_script(response, BASE_PREFIX_ELEMENT_ID) or ""
    parsed_url = urllib.parse.urlparse(response.url)
    pass_url = "{}://{}{}{}/api/pass-challenge".format(parsed_url.scheme, parsed_url.netloc, base_prefix, ANUBIS_PATH_PREFIX)
    parameters["redir"] = response.url
    pass_response = session.get(pass_url, params=parameters, allow_redirects=False)
    pass_response.raise_for_status()


def solve_proof_of_work(random_data, difficulty):
    """
    Find a nonce such that the SHA-256 digest of ``random_data`` followed by the nonce
    starts with ``difficulty`` zero hex digits.
    :param random_data: Random data of the challenge.
    :param difficulty: Number of leading zero hex digits required.
    :return: Tuple of the matching digest and the nonce.
    """
    target = "0" * difficulty
    nonce = 0
    while True:
        digest = hashlib.sha256((random_data + str(nonce)).encode("utf-8")).hexdigest()
        if digest.startswith(target):
            return digest, nonce
        nonce += 1


def _solve_proof_of_work(data, difficulty):
    """
    Solve the proof-of-work challenge.
    :param data: Challenge data.
    :param difficulty: Number of required leading zero hex digits.
    :return: Parameters for the pass-challenge request.
    """
    start = time.time()
    digest, nonce = solve_proof_of_work(data["randomData"], difficulty)
    elapsed_time = int((time.time() - start) * 1000)
    return {
        "id": data["id"],
        "response": digest,
        "nonce": str(nonce),
        "elapsedTime": str(elapsed_time),
    }


def _solve_metarefresh(data, difficulty):
    """
    Wait for the meta-refresh challenge, which requires no proof of work.
    :param data: Challenge data.
    :param difficulty: Number of 800ms intervals to wait.
    :return: Parameters for the pass-challenge request.
    """
    issued_at = datetime.datetime.fromisoformat(data["issuedAt"])
    wait_until = issued_at + datetime.timedelta(milliseconds=800 * difficulty)
    delay = (wait_until - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
    if delay > 0:
        time.sleep(delay + 1)
    return {
        "id": data["id"],
        "challenge": data["randomData"],
    }


def _extract_json_script(response, element_id):
    """
    Extract the JSON content of a script element from an HTML response.
    :param response: Response.
    :param element_id: Id of the script element.
    :return: Parsed JSON content or None if not found.
    """
    match = re.search(r'<script[^>]*id="{}"[^>]*>(.*?)</script>'.format(element_id), response.text, re.DOTALL)
    if match is None:
        return None
    return json.loads(match.group(1).strip())
