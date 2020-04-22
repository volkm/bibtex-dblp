import logging
import re

import requests

import bibtex_dblp.dblp_data

# DBLP URLs
DBLP_BASE_URL = "https://dblp.org/"
DBLP_XML_URL = DBLP_BASE_URL + "xml/dblp.xml.gz"
DBLP_PUBLICATION_SEARCH_URL = DBLP_BASE_URL + "search/publ/api"
DBLP_PUBLICATION_BIBTEX = DBLP_BASE_URL + "rec/{bib_format}/{key}.bib"
DOI_FROM_DBLP = DBLP_BASE_URL + "doi/{bib_format}/{key}"
DOI_FROM_DOI_ORG = "https://doi.org/{key}"

# DBLP bib-entry types
CONDENSED = "condensed"
STANDARD = "standard"
CROSSREF = "crossref"

BIB_FORMATS = [CONDENSED, STANDARD, CROSSREF]


def get_url_part(bib_format):
    """
    Get identifier of format for DBLP urls.
    :return:
    """
    assert bib_format in BIB_FORMATS
    if bib_format == CONDENSED:
        return "bib0"
    elif bib_format == STANDARD:
        return "bib1"
    elif bib_format == CROSSREF:
        return "bib2"


def extract_dblp_id(entry):
    """
    Extract DBLP id or DOI from the entry using the following methods (in this order):
    - If the field biburl is available, extract it from there
    - If the field doi is available, extract it from there
    - If the entry name appears to be a DBLP id oder DOI, use that. 
    :param entry: Bibliography entry.
    :return: DBLP id, DOI, or None if no could be extracted.
    """
    if "biburl" in entry.fields:
        match = re.search(r"http(s?)://dblp.org/rec/(.*)\.bib", entry.fields["biburl"])
        if match:
            return "DBLP:" + match.group(2)

    if "doi" in entry.fields and entry.fields["doi"]:
        k = entry.fields["doi"]
        # weirdly, DBLP escapes "_" with "\_", so we have to remove all backslashes:
        return "doi:" + k.replace("\\", "")

    t, k = sanitize_key(entry.key)
    if t == "DBLP":
        return "DBLP:" + k
    elif t == "DOI":
        return "doi:" + k
    else:
        return None


def sanitize_key(k):
    """
    Given a key in one of these formats:
    DBLP:conf/spire/2006
    conf/spire/2006
    doi:10.1007/11880561
    10.1007/11880561
    Determine the key type and remove the type prefix if present.
    :param k: DBLP id or DOI for entry.
    :return: A tuple type, key.
    """
    if k[:5].upper() == "DBLP:":
        return "DBLP", k[5:]
    elif k[:4].upper() == "DOI:":
        return "DOI", k[4:]
    elif k.count("/") >= 2:
        logging.debug(f"Key {k} was *guessed* to be a DBLP id.")
        return "DBLP", k
    elif k.count("/") == 1:
        logging.debug(f"Key {k} was *guessed* to be a DOI.")
        return "DOI", k
    else:
        logging.error(f"Could not determine type of {k}.")
        return None, k


def bibtex_requests(type, key, bib_format, prefer_doi_org):
    part = get_url_part(bib_format)
    if type == "DBLP":
        url = DBLP_PUBLICATION_BIBTEX.format(key=key, bib_format=part)
        headers = None
        yield url, headers
    elif type == "DOI":
        url1 = DOI_FROM_DBLP.format(key=key, bib_format=part)
        headers1 = None
        url2 = DOI_FROM_DOI_ORG.format(key=key)
        headers2 = {"Accept": "application/x-bibtex; charset=utf-8"}
        if prefer_doi_org:
            yield url2, headers2
            yield url1, headers1
        else:
            yield url1, headers1
            yield url2, headers2


def get_bibtex(id, bib_format, prefer_doi_org=False):
    """
    Get bibtex entry in specified format.
    :param id: DBLP id or DOI for entry.
    :param bib_format: Format of bibtex export.
    :return: Bibtex as binary string.
    """
    assert bib_format in BIB_FORMATS
    t, k = sanitize_key(id)
    logging.debug(
        f"In get_bibtex({id}, {bib_format}): key has been sanitized to {t}, {k}"
    )
    for url, headers in bibtex_requests(t, k, bib_format, prefer_doi_org):
        if headers:
            resp = requests.get(url, headers=headers)
        else:
            resp = requests.get(url)
        if resp.status_code == 200:
            return resp.content.decode("utf-8")
        else:
            logging.warning(f"Could not retrieve {id} from {url}.")


def search_publication(pub_query, max_search_results):
    """
    Search for publication according to given query.
    :param pub_query: Query for publication.
    :param max_search_results: Maximal number of search results to return.
    :return: Search results.
    """
    parameters = dict(q=pub_query, format="json", h=max_search_results)

    resp = requests.get(DBLP_PUBLICATION_SEARCH_URL, params=parameters)
    assert resp.status_code == 200
    results = bibtex_dblp.dblp_data.DblpSearchResults(resp.json())
    assert results.status_code == 200
    return results
