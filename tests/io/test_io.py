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


def test_modify_entries():
    def count_entries(_bib):
        num_escapes = num_timestamp = num_biburl = num_bibsource = 0
        for entry_str, entry in _bib.entries.items():
            if "url" in entry.fields and "\\_" in entry.fields["url"]:
                num_escapes += 1
            if "doi" in entry.fields and "\\_" in entry.fields["doi"]:
                num_escapes += 1
            if "timestamp" in entry.fields:
                num_timestamp += 1
            if "biburl" in entry.fields:
                num_biburl += 1
            if "bibsource" in entry.fields:
                num_bibsource += 1
        return num_escapes, num_timestamp, num_biburl, num_bibsource

    bib = bibtex_dblp.database.load_from_file(bib_path("ley.bib"))
    assert count_entries(bib) == (2, 9, 9, 9)
    bib = bibtex_dblp.database.modify_entries(bib, remove_escapes=True, remove_timestamp=True, remove_biburl=True, remove_bibsource=True)
    assert count_entries(bib) == (0, 0, 0, 0)
