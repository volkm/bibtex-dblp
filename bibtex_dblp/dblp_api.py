import re
from enum import Enum
from requests.exceptions import HTTPError
from requests_ratelimiter import LimiterSession

import bibtex_dblp.dblp_data


class InvalidDblpIdException(Exception):
    pass


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

    def __init__(self, wait_time, dblp_base_url="https://dblp.org"):
        """
        Create a session for DBLP.
        :param wait_time: Time in seconds to sleep before retrying.
        :param dblp_base_url: Base URL for DBLP.
        """
        self.base_url = dblp_base_url
        self.wait_time = wait_time

        self.publication_search_url = self.base_url + "/search/publ/api"
        self.publication_bibtex = self.base_url + "/rec/{key}.bib?param={bib_format}"

        self.session = LimiterSession(per_second=1.0 / wait_time, per_minute=60.0 / wait_time, burst=3)

    def perform_request(self, url, params=None, **kwargs):
        """
        Perform a GET request to DBLP.
        :param url: URL to access.
        :param params: Optional parameters.
        :param kwargs: Optional arguments.
        :return: Response.
        :raises: HTTPError if request was unsuccessful.
        """
        response = self.session.get(url, params=params, **kwargs)
        response.raise_for_status()
        return response


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
    results = bibtex_dblp.dblp_data.DblpSearchResults(resp.json())
    assert results.status_code == 200
    return results
