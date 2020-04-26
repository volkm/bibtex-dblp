from pathlib import Path

import pytest

import bibtex_dblp.database as db
import bibtex_dblp.dblp_api as api
from bibtex_dblp.formats import CONDENSED, CROSSREF, STANDARD


def test_search_publication():
    search_string = "Output-sensitive autocompletion search"
    search_results = api.search_publication(search_string, max_search_results=30)
    assert search_results.total_matches == 2
    for i in range(len(search_results.results)):
        result = search_results.results[i].publication
        if result.doi == "10.1007/S10791-008-9048-X":
            assert result.title == "Output-sensitive autocompletion search."
            assert result.booktitle is None
            assert result.volume == "11"
            assert result.venue == "Inf. Retr."
            assert result.pages == "269-286"
            assert result.year == 2008
            assert result.type == "Journal Articles"
            assert result.key == "journals/ir/BastMW08"
            assert result.doi == "10.1007/S10791-008-9048-X"
            assert result.ee == "https://doi.org/10.1007/s10791-008-9048-x"
            assert result.url == "https://dblp.org/rec/journals/ir/BastMW08"
            authors = [author.name for author in result.authors]
            assert "H. Bast 0001" in authors
            assert "Christian Worm Mortensen" in authors
            assert "Ingmar Weber" in authors
        else:
            assert result.doi == "10.1007/11880561_13"


def test_dblp_bibtex():
    search_string = "Output-sensitive autocompletion search"
    search_results = api.search_publication(search_string, max_search_results=30)
    assert search_results.total_matches == 2
    result = search_results.results[1].publication
    assert result.doi == "10.1007/11880561_13"

    bibtex_standard = api.get_bibtex(result.key, bib_format=STANDARD)
    assert (
        "booktitle = {String Processing and Information Retrieval, 13th International Conference,"
        in bibtex_standard
    )
    assert (
        "{SPIRE} 2006, Glasgow, UK, October 11-13, 2006, Proceedings}"
        in bibtex_standard
    )

    bibtex_crossref = api.get_bibtex(result.key, bib_format=CROSSREF)
    assert "crossref  = {DBLP:conf/spire/2006}," in bibtex_crossref
    assert "editor " in bibtex_crossref

    bibtex_condensed = api.get_bibtex(result.key, bib_format=CONDENSED)
    assert "booktitle = {{SPIRE}}" in bibtex_condensed


KEYS = {
    "key_from_unknown_namespace": (None, "key_from_unknown_namespace"),
    "DBLP:conf/spire/BastMW06": (api.DBLP, "conf/spire/BastMW06"),
    "DbLP:conf/spire/BastMW06": (api.DBLP, "conf/spire/BastMW06"),
    "conf/spire/BastMW06": (api.DBLP, "conf/spire/BastMW06"),
    "doi:10.1007/11880561_13": (api.DOI, "10.1007/11880561_13"),
    "DOi:10.1007/11880561_13": (api.DOI, "10.1007/11880561_13"),
    "10.1007/11880561_13": (api.DOI, "10.1007/11880561_13"),
}


@pytest.mark.parametrize("key, answer", KEYS.items())
def test_paper_id_from_key(key, answer):
    namespace, id = answer
    assert api.paper_id_from_key(key).namespace == namespace
    assert api.paper_id_from_key(key).id == id


FILES_DIR = Path("tests") / Path("files")


def example_file(f):
    return open(FILES_DIR / Path(f + ".bib")).read()


def test_paperid_from_entry():
    text = example_file("standard")
    entries = db.parse_bibtex(text).entries.values()
    assert len(entries) == 1
    [entry] = entries
    assert entry.fields["doi"] == "10.1007/11880561_13"
    assert api.paper_id_from_entry(entry).namespace == api.DBLP
    assert api.paper_id_from_entry(entry).id == "conf/spire/BastMW06"
    entry.fields["biburl"] = ""
    assert api.paper_id_from_entry(entry).namespace == api.DOI
    assert api.paper_id_from_entry(entry).id == "10.1007/11880561_13"
    entry.fields["doi"] = None
    assert api.paper_id_from_entry(entry).namespace == api.DBLP
    assert api.paper_id_from_entry(entry).id == "conf/spire/BastMW06"


ENTRIES = {
    """@article{blabla,
    title = {some title},
    author = {some author and some other author},
    biburl = {https://nonsense.org/nothing/useful}
}""": (
        None,
        "blabla",
    ),
    """@article{10.1007/11880561_13,
    title = {some title}
}""": (
        api.DOI,
        "10.1007/11880561_13",
    ),
    """@article{dOi:10.1007/11880561_13,
    title = {some title}
}""": (
        api.DOI,
        "10.1007/11880561_13",
    ),
    """@article{conf/spire/BastMW06,
    title = {some title}
}""": (
        api.DBLP,
        "conf/spire/BastMW06",
    ),
    """@article{DblP:conf/spire/BastMW06,
    title = {some title}
}""": (
        api.DBLP,
        "conf/spire/BastMW06",
    ),
}


pre = "@inproceedings{preserve,\nbiburl={"
post = "}\n}"
protocols = ["https://", "http://"]
domains = ["dblp.org", "dblp.uni-trier.de", "dblp2.uni-trier.de", "dblp.dagstuhl.de"]
urls = ["/rec/conf/spire/BastMW06.bib", "/rec/bib/conf/spire/BastMW06"]


for p in protocols:
    for d in domains:
        for u in urls:
            ENTRIES[pre + p + d + u + post] = (api.DBLP, "conf/spire/BastMW06")


@pytest.mark.parametrize("entry, answer", ENTRIES.items())
def test_paperid_from_entry_cornercases(entry, answer):
    namespace, id = answer
    entries = db.parse_bibtex(entry).entries.values()
    assert len(entries) == 1
    [entry] = entries
    assert api.paper_id_from_entry(entry).namespace == namespace
    assert api.paper_id_from_entry(entry).id == id
