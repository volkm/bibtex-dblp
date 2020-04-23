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


DBLP = "DBLP"
DOI = "doi"
NAMESPACES = [DBLP, DOI, None]
PROVIDERS = ["dblp.org", "doi.org"]
sessions = {}


class PaperId:
    namespace = None
    id = None

    def __init__(self, namespace, id):
        assert namespace in NAMESPACES
        self.namespace = namespace
        self.id = id

    def key(self):
        if self.namespace is None:
            return self.id
        else:
            return self.namespace + ":" + self.id

    def get_request(self, bib_format, provider):
        assert provider in PROVIDERS
        if provider is not None and provider not in sessions:
            sessions[provider] = requests.Session()
        if provider == "dblp.org":
            part = get_url_part(bib_format)
            if self.namespace == DBLP:
                return {
                    "session": sessions[provider],
                    "url": DBLP_PUBLICATION_BIBTEX.format(key=self.id, bib_format=part),
                }
            elif self.namespace == DOI:
                return {
                    "session": sessions[provider],
                    "url": DOI_FROM_DBLP.format(key=self.id, bib_format=part),
                }
        elif provider == "doi.org":
            if self.namespace == DOI:
                return {
                    "session": sessions[provider],
                    "url": DOI_FROM_DOI_ORG.format(key=self.id),
                    "headers": {"Accept": "application/x-bibtex; charset=utf-8"},
                }

    def get_requests(self, bib_format, providers=PROVIDERS):
        for p in providers:
            r = self.get_request(bib_format=bib_format, provider=p)
            if r is not None:
                yield r


def paper_id_from_entry(entry):
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
            return PaperId(DBLP, match.group(2))

    if "doi" in entry.fields and entry.fields["doi"]:
        k = entry.fields["doi"]
        if len(k) > 0:
            # weirdly, DBLP escapes "_" with "\_", so we have to remove all backslashes:
            return PaperId(DOI, k.replace("\\", ""))

    return paper_id_from_key(entry.key)


def paper_id_from_key(k):
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
        return PaperId(DBLP, k[5:])
    elif k[:4].upper() == "DOI:":
        return PaperId(DOI, k[4:])
    elif k.count("/") >= 2:
        logging.debug(f"Citation key {k} was *guessed* to be a DBLP id.")
        return PaperId(DBLP, k)
    elif k.count("/") == 1:
        logging.debug(f"Citation key {k} was *guessed* to be a DOI.")
        return PaperId(DOI, k)
    else:
        logging.debug(f"Citation key {k} does not seem to belong to any namespace.")
        return PaperId(None, k)


def get_bibtex(paper_id, bib_format, prefer_doi_org=False):
    """
    Get bibtex entry in specified format.
    :param id: DBLP id or DOI for entry.
    :param bib_format: Format of bibtex export.
    :return: Bibtex as binary string.
    """
    assert bib_format in BIB_FORMATS
    if type(paper_id) == str:
        paper_id = paper_id_from_key(paper_id)
    providers = PROVIDERS if not prefer_doi_org else reversed(PROVIDERS)
    for r in paper_id.get_requests(bib_format=bib_format, providers=providers):
        s = r["session"]
        if "headers" in r:
            resp = s.get(r["url"], headers=r["headers"])
        else:
            resp = s.get(r["url"])
        if resp.status_code == 200:
            return resp.content.decode("utf-8")
        else:
            logging.warning(f"Could not retrieve {id} from {r['url']}.")


def search_publication(pub_query, max_search_results):
    """
    Search for publication according to given query.
    :param pub_query: Query for publication.
    :param max_search_results: Maximal number of search results to return.
    :return: Search results.
    """
    parameters = dict(q=pub_query, format="json", h=max_search_results)

    if "dblp.org" not in sessions:
        sessions["dblp.org"] = requests.Session()
    resp = sessions["dblp.org"].get(DBLP_PUBLICATION_SEARCH_URL, params=parameters)
    assert resp.status_code == 200
    results = bibtex_dblp.dblp_data.DblpSearchResults(resp.json())
    assert results.status_code == 200
    return results
