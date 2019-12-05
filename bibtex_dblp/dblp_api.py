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

    def bib_url(self):
        """
        Get identifier of format for DBLP urls.
        :return:
        """
        if self is BibFormat.condensed:
            return "bib0"
        elif self is BibFormat.standard:
            return "bib1"
        elif self is BibFormat.crossref:
            return "bib2"
        else:
            assert False

    def __str__(self):
        return self.value


def extract_dblp_id(entry):
    """
    Extract DBLP id by either using the biburl if given or trying to use the entry name.
    :param entry: Bibliography entry.
    :return: DBLP id or None if no could be extracted.
    """
    if "biburl" in entry.fields:
        match = re.search(r"http(s?)://dblp.org/rec/bib/(.*)", entry.fields["biburl"])
        assert match
        return match.group(2)
    else:
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
    resp = requests.get(config.DBLP_PUBLICATION_BIBTEX.format(key=dblp_id, bib_format=bib_format.bib_url()))
    assert resp.status_code == 200
    return resp.content.decode('utf-8')


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

    resp = requests.get(config.DBLP_PUBLICATION_SEARCH_URL, params=parameters)
    assert resp.status_code == 200
    results = bibtex_dblp.dblp_data.DblpSearchResults(resp.json())
    assert results.status_code == 200
    return results
