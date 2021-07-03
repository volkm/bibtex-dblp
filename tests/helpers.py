from pathlib import Path

import bibtex_dblp.database as db

FILES_DIR = Path("tests") / Path("files")


def example_file(f):
    return open(FILES_DIR / Path(f)).read()


def compare_line_by_line(a, b):
    """
    Compare two bib-files (given as string) line by line
    However:
      - ignore "timestamp" lines
      - always unescape \_ to _.

    Beware: This also checks the text wrapping!
    We cannot currently correctly reproduce DBLP's text wrapping.
    """
    a = [line.strip() for line in a.strip().split("\n")]
    b = [line.strip() for line in b.strip().split("\n")]
    assert len(a) == len(b)
    for i in range(len(a)):
        if "timestamp" not in a[i]:
            assert a[i].replace("\\_", "_") == b[i].replace("\\_", "_")


def compare_parsed(bibtext1, bibtext2):
    """
    Check that two bib-entries (given as text) are semantically the same,
    that is, when parsed with pybtex they're the same.
    """
    bib1, bib2 = db.parse_bibtex(bibtext1), db.parse_bibtex(bibtext2)
    assert set(bib1.entries.keys()) == set(bib2.entries.keys())
    for i in bib1.entries.keys():
        e1, e2 = bib1.entries[i], bib2.entries[i]
        assert e1.type == e2.type
        assert e1.key == e2.key
        assert set(e1.fields.keys()) == set(e2.fields.keys())
        for f, v1 in e1.fields.items():
            v2 = e2.fields[f]
            assert v1 == v2
        assert set(e1.persons.keys()) == set(e2.persons.keys())
        for g, g1 in e1.persons.items():
            g2 = e2.persons[g]
            g1 = set(str(person) for person in g1)
            g2 = set(str(person) for person in g2)
            assert g1 == g2
