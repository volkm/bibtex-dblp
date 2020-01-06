import bibtex_dblp.dblp_api
from bibtex_dblp.dblp_api import BibFormat


def test_search_publication():
    search_string = "Output-sensitive autocompletion search"
    search_results = bibtex_dblp.dblp_api.search_publication(search_string, max_search_results=30)
    assert search_results.total_matches == 2
    for i in range(len(search_results.results)):
        result = search_results.results[i].publication
        if result.doi == '10.1007/S10791-008-9048-X':
            result.title = 'Output-sensitive autocompletion search.'
            result.booktitle = None
            result.volume = '11'
            result.venue = 'Inf. Retr.'
            result.pages = '269-286'
            result.year = 2008
            result.type = 'Journal Articles'
            result.key = 'journals/ir/BastMW08'
            result.doi = '10.1007/S10791-008-9048-X'
            result.ee = 'https://doi.org/10.1007/s10791-008-9048-x'
            result.url = 'https://dblp.org/rec/journals/ir/BastMW08'
            authors = [author.name for author in result.authors]
            assert 'H. Bast 0001' in authors
            assert 'Christian Worm Mortensen' in authors
            assert 'Ingmar Weber' in authors
        else:
            assert result.doi == '10.1007/11880561_13'


def test_dblp_bibtex():
    search_string = "Output-sensitive autocompletion search"
    search_results = bibtex_dblp.dblp_api.search_publication(search_string, max_search_results=30)
    assert search_results.total_matches == 2
    result = search_results.results[1].publication
    assert result.doi == '10.1007/11880561_13'

    bibtex_standard = bibtex_dblp.dblp_api.get_bibtex(result.key, bib_format=BibFormat.standard)
    assert "booktitle = {String Processing and Information Retrieval, 13th International Conference," in bibtex_standard
    assert "{SPIRE} 2006, Glasgow, UK, October 11-13, 2006, Proceedings}" in bibtex_standard

    bibtex_crossref = bibtex_dblp.dblp_api.get_bibtex(result.key, bib_format=BibFormat.crossref)
    assert "crossref  = {DBLP:conf/spire/2006}," in bibtex_crossref
    assert "editor " in bibtex_crossref

    bibtex_condensed = bibtex_dblp.dblp_api.get_bibtex(result.key, bib_format=BibFormat.condensed)
    assert "booktitle = {{SPIRE}}" in bibtex_condensed
