from conftest import bib_path

from difflib import unified_diff

import bibtex_dblp.database


def test_import_export(tmp_path):
    """
    Check that importing and exporting multiple times yields the same results
    """
    # Import and export
    bib = bibtex_dblp.database.load_from_file(bib_path("ley.bib"))
    tmp_file1 = tmp_path / "export1.bib"
    bibtex_dblp.database.write_to_file(bib, tmp_file1)

    # Compare files
    with open(bib_path("ley.bib")) as f1:
        with open(tmp_file1) as f2:
            diff = list(unified_diff(f1.readlines(), f2.readlines()))
    # The files differ due to different formatting
    # assert not diff, "Files differ:\n{}".format("".join(diff))

    # Import and export
    bib = bibtex_dblp.database.load_from_file(tmp_file1)
    tmp_file2 = tmp_path / "export2.bib"
    bibtex_dblp.database.write_to_file(bib, tmp_file2)

    # Compare files
    with open(tmp_file1) as f1:
        with open(tmp_file2) as f2:
            diff = list(unified_diff(f1.readlines(), f2.readlines()))
    assert not diff, "Files differ:\n{}".format("".join(diff))
