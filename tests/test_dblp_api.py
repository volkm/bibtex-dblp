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


def test_sanitize_key():
    assert api.paper_id_from_key("DBLP:conf/spire/2006").namespace == api.DBLP
    assert api.paper_id_from_key("dblp:conf/spire/2006").id == "conf/spire/2006"
    assert api.paper_id_from_key("conf/spire/2006").namespace == api.DBLP
    assert api.paper_id_from_key("conf/spire/2006").id == "conf/spire/2006"
    assert api.paper_id_from_key("doi:10.1007/11880561").namespace == api.DOI
    assert api.paper_id_from_key("doi:10.1007/11880561").id == "10.1007/11880561"
    assert api.paper_id_from_key("DOI:10.1007/11880561").namespace == api.DOI
    assert api.paper_id_from_key("DOI:10.1007/11880561").id == "10.1007/11880561"
    assert api.paper_id_from_key("10.1007/11880561").namespace == api.DOI
    assert api.paper_id_from_key("10.1007/11880561").id == "10.1007/11880561"


def test_extract_dblp_id():
    text = api.get_bibtex("DBLP:conf/spire/2006", bib_format=STANDARD)
    entries = db.parse_bibtex(text).entries.values()
    assert len(entries) == 1
    [entry] = entries
    assert entry.fields["doi"] == "10.1007/11880561"
    assert api.paper_id_from_entry(entry).key() == "DBLP:conf/spire/2006"
    entry.fields["biburl"] = ""
    assert api.paper_id_from_entry(entry).key() == "doi:10.1007/11880561"
    entry.fields["doi"] = None
    assert api.paper_id_from_entry(entry).key() == "DBLP:conf/spire/2006"
