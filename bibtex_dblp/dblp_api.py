import logging
import re

import requests

import bibtex_dblp.database as db
import bibtex_dblp.dblp_data
import bibtex_dblp.formats as formats

# DBLP URLs
DBLP_BASE_URL = "https://dblp.org/"
DBLP_XML_URL = DBLP_BASE_URL + "xml/dblp.xml.gz"
DBLP_PUBLICATION_SEARCH_URL = DBLP_BASE_URL + "search/publ/api"
DBLP_PUBLICATION_BIBTEX = DBLP_BASE_URL + "rec/{bib_format}/{key}.bib"
DOI_FROM_DBLP = DBLP_BASE_URL + "doi/{bib_format}/{key}"
DOI_FROM_DOI_ORG = "https://doi.org/{key}"
ISBN_FROM_DBLP = DBLP_BASE_URL + "isbn/{bib_format}/{key}"


DBLP = "DBLP"
DOI = "doi"
ISBN = "ISBN"
NAMESPACES = [DBLP, DOI, ISBN, None]
PROVIDERS = ["dblp.org", "doi.org"]
sessions = {}


def sanitize_reparse(reparse):
    """
    If reparse is a list, check that it is a subset of PROVIDERS.
    Otherwise, it must be a string ("all", "none", or one of PROVIDERS).
    :param entry: Which to reparse.
    :return: List of provides that should be reparsed.
    """
    if type(reparse) == str:
        if reparse in PROVIDERS:
            reparse = [reparse]
        elif reparse == "none":
            reparse = []
        elif reparse == "all":
            reparse = PROVIDERS
    for p in reparse:
        if p not in PROVIDERS:
            logging.error(
                "Set provider {p} to force reparsing, but it is not one of {PROVIDERS}"
            )
            reparse.remove(p)
    return reparse


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
            part = formats.dblp_article_url_part(bib_format)
            if self.namespace == DBLP:
                return {
                    "provider": "dblp.org",
                    "session": sessions[provider],
                    "url": DBLP_PUBLICATION_BIBTEX.format(key=self.id, bib_format=part),
                }
            elif self.namespace == DOI:
                return {
                    "provider": "doi.org",
                    "session": sessions[provider],
                    "url": DOI_FROM_DBLP.format(key=self.id, bib_format=part),
                }
            elif self.namespace == ISBN:
                return {
                    "provider": "dblp.org",
                    "session": sessions[provider],
                    "url": ISBN_FROM_DBLP.format(key=self.id, bib_format=part),
                }
        elif provider == "doi.org":
            if self.namespace == DOI:
                return {
                    "provider": "doi.org",
                    "session": sessions[provider],
                    "url": DOI_FROM_DOI_ORG.format(key=self.id),
                    "headers": {"Accept": "application/x-bibtex; charset=utf-8"},
                }

    def get_requests(self, bib_format, providers=PROVIDERS):
        for p in providers:
            r = self.get_request(bib_format=bib_format, provider=p)
            if r is not None:
                yield r


def is_isbn(i):
    return len(i) in [10, 13] and re.match("^[0-9]*$", i)


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
        patterns = [
            r"http(s?)://(.*)dblp(.*)/rec/(.*)\.bib",
            r"http(s?)://(.*)dblp(.*)/rec/bib/(.*)",
        ]
        for p in patterns:
            match = re.search(p, entry.fields["biburl"])
            if match:
                return PaperId(DBLP, match.group(4))

    if "doi" in entry.fields:
        k = entry.fields["doi"]
        if k and len(k) > 0:
            # DBLP escapes "_" with "\_", so we invert that:
            return PaperId(DOI, k.replace("\\_", "_"))

    if "isbn" in entry.fields:
        k = entry.fields["isbn"]
        if k and len(k) > 0:
            i = k.replace("-", "")
            if is_isbn(i):
                return PaperId(ISBN, i)
            else:
                logging.error(
                    f"ISBN field {k} of entry {entry.key} is not a valid ISBN."
                )

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
    elif k[:5].upper() == "ISBN:":
        i = k[5:].replace("-", "")
        if is_isbn(i):
            return PaperId(ISBN, i)
        else:
            logging.error(f"{k} is not a valid ISBN.")
            return PaperId(None, k)
    elif k.count("/") >= 2:
        logging.debug(f"Citation key {k} was *guessed* to be a DBLP id.")
        return PaperId(DBLP, k)
    elif k.count("/") == 1:
        logging.debug(f"Citation key {k} was *guessed* to be a DOI.")
        return PaperId(DOI, k)
    else:
        i = k.replace("-", "")
        if is_isbn(i):
            logging.debug(f"Citation key {k} was *guessed* to be an ISBN.")
            return PaperId(ISBN, i)
        else:
            logging.debug(f"Citation key {k} does not seem to belong to any namespace.")
            return PaperId(None, k)


def get_bibtex(paper_id, bib_format, prefer_doi_org=False, reparse=PROVIDERS):
    """
    Get bibtex entry in specified format.
    :param id: DBLP id or DOI for entry.
    :param bib_format: Format of bibtex export.
    :param prefer_doi_org: Prefer to retrieve data from doi.org.
    :param reparse: Directly use server response, or reparse and print it using our pretty-printer.
    :return: Bibtex as binary string.
    """
    if type(paper_id) == str:
        paper_id = paper_id_from_key(paper_id)
    providers = PROVIDERS if not prefer_doi_org else reversed(PROVIDERS)
    for r in paper_id.get_requests(bib_format=bib_format, providers=providers):
        p = r["provider"]
        s = r["session"]
        if "headers" in r:
            resp = s.get(r["url"], headers=r["headers"])
        else:
            resp = s.get(r["url"])
        if resp.status_code == 200:
            text = resp.content.decode("utf-8")
            if p not in reparse:
                return text
            else:
                return "\n\n".join(
                    db.entry_to_string(e, bib_format=bib_format)
                    for e in db.parse_bibtex(text).entries.values()
                )
        else:
            logging.warning(f"Could not retrieve {id} from {r['url']}.")


def get_author(author, bib_format, prefer_doi_org=False, reparse=PROVIDERS):
    """
    Get bibtex entries of an author in specified format.
    :param author: Author's id on DBLP (typically Lastname:Firstname)
    :param bib_format: Format of bibtex export.
    :return: Bibtex as binary string.
    """
    format_specifier = formats.dblp_author_url_part(bib_format)
    initial_lastname = author[0].lower()
    url = f"https://dblp.org/pers/{format_specifier}/{initial_lastname}/{author}"
    resp = requests.get(url)
    if resp.status_code == 200:
        text = resp.content.decode("utf-8")
        if "dblp.org" not in reparse:
            return text
        else:
            return "\n\n".join(
                db.entry_to_string(e, bib_format=bib_format)
                for e in db.parse_bibtex(text).entries.values()
            )
    else:
        logging.warning(f"Could not retrieve {author} data from {url}.")


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
