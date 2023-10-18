from conftest import bib_path

import bibtex_dblp.database
import bibtex_dblp.dblp_api
from bibtex_dblp.dblp_api import BibFormat


def test_convert():
    bib = bibtex_dblp.database.load_from_file(bib_path("ley.bib"))
    bib, no_changes = bibtex_dblp.database.convert_dblp_entries(bib, bib_format=BibFormat.condensed_doi)
    assert no_changes == 32


def test_convert_invalid_id():
    bib = bibtex_dblp.database.load_from_file(bib_path("invalid_id.bib"))
    bib, no_changes = bibtex_dblp.database.convert_dblp_entries(bib, bib_format=BibFormat.condensed_doi)
    assert no_changes == 0
