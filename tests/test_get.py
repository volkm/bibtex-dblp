from pathlib import Path

import pytest
from click.testing import CliRunner

import bibtex_dblp.dblp_api as api
import bibtex_dblp.database as db
import bibtex_dblp.formats as formats
from bibtex_dblp.cli import main

example_ids = [
    "DBLP:conf/spire/BastMW06",
    "conf/spire/BastMW06",
    "doi:10.1007/11880561_13",
    "10.1007/11880561_13",
]

FILES_DIR = Path("tests") / Path("files")
expected = dict((f, open(FILES_DIR / Path(f"{f}.bib")).read()) for f in formats.BIB_FORMATS)
expected_from_doi_org = open(FILES_DIR / Path("doi.org.bib")).read()


@pytest.mark.parametrize("id", example_ids)
@pytest.mark.parametrize("format", formats.BIB_FORMATS)
def test_get_from_dblp_org(id, format):
    """
    When retrieving and printing DBLP entries,
    we must produce exactly the same output as DBLP
    (even if the bib-entry was parsed with pybtex in between).
    """
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, ["--format", format, "get", id, "--reparse", "all"])
    assert result.exit_code == 0
    output = result.stdout.strip().split("\n")
    exp = expected[format].strip().split("\n")
    assert len(output) == len(exp)
    for i in range(len(output)):
        if "timestamp" not in output[i]:
            assert output[i] == exp[i]


def same_when_parsed(bibtext1, bibtext2):
    """
    Check that two bib-entries (given as text) are semantically the same,
    that is, when parsed with pybtex they're the same.
    """
    bib1, bib2 = db.parse_bibtex(bibtext1), db.parse_bibtex(bibtext2)
    assert(set(bib1.entries.keys()) == set(bib2.entries.keys()))
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


@pytest.mark.parametrize(
    "id", [id for id in example_ids if api.paper_id_from_key(id).namespace == api.DOI]
)
def test_get_doi_org(id):
    """
    When retrieving bibtex from doi.org, we only require semantic equivalence.
    """
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, ["--prefer-doi-org", "get", id, "--reparse", "all"])
    assert result.exit_code == 0
    same_when_parsed(result.stdout, expected_from_doi_org)


@pytest.mark.parametrize(
    "id",
    [
        "nonexistent",
        "nonexistend:id",
        "DBLP:thisdoesnotexist",
        "doi:thisdoesnotexist",
        "this/does/not/exist/at/all",
    ],
)
def test_nonexisting(id):
    """
    When retrieving non-existing IDs, nothing should be printed.
    """
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, ["get", id])
    assert result.exit_code == 0
    output = result.stdout.strip()
    assert output == ""
