from enum import Enum
import re
import requests

import bibtex_dblp.config as config
import bibtex_dblp.dblp_data


class BibFormat(Enum):
    """
    Format of DBLP bibtex.
    """
    condensed = 'condensed'
    standard = 'standard'
    crossref = 'crossref'
    condensed_doi = 'condensed_doi'

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


def perform_request(url, params=None, **kwargs):
    """
    Perform a GET request to DBLP.
    :param url: URL to access.
    :param params: Optional parameters.
    :param kwargs: Optional arguments.
    :return: Response.
    :raises: HTTPError if request was unsuccessful.
    """
    response = requests.get(url, params=params, **kwargs)
    if response.status_code == 200:
        return response
    else:
        response.raise_for_status()
        return None


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


def get_bibtex(dblp_id, bib_format=BibFormat.condensed):
    """
    Get bibtex entry in specified format.
    :param dblp_id: DBLP id for entry.
    :param bib_format: Format of bibtex export (see BibFormat).
    :return: Bibtex as binary string.
    """
    resp = perform_request(config.DBLP_PUBLICATION_BIBTEX.format(key=dblp_id, bib_format=bib_format.bib_url()))
    bibtex = resp.content.decode('utf-8')

    if bib_format == BibFormat.condensed_doi:
        # Also get DOI and insert it into bibtex
        resp = perform_request(
            config.DBLP_PUBLICATION_BIBTEX.format(key=dblp_id, bib_format=BibFormat.standard.bib_url()))
        lines = resp.content.decode('utf-8').split('\n')
        keep_lines = [line for line in lines if line.startswith("  doi")]
        assert len(keep_lines) <= 1
        if keep_lines:
            doi = keep_lines[0][:-1]  # Remove comma
            # Insert into bibtex
            bibtex = bibtex[:-4] + ",\n" + doi + bibtex[-4:]

    return bibtex


def search_publication(pub_query, max_search_results=config.MAX_SEARCH_RESULTS):
    """
    Search for publication according to given query.
    :param pub_query: Query for publication.
    :param max_search_results: Maximal number of search results to return.
    :return: Search results.
    """
    parameters = dict(
        q=pub_query,
        format="json",
        h=max_search_results
    )

    resp = perform_request(config.DBLP_PUBLICATION_SEARCH_URL, params=parameters)
    results = bibtex_dblp.dblp_data.DblpSearchResults(resp.json())
    assert results.status_code == 200
    return results
