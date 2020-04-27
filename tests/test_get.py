import pytest
from click.testing import CliRunner

import bibtex_dblp.database as db
import bibtex_dblp.dblp_api as api
import bibtex_dblp.formats as formats
import helpers
from bibtex_dblp.cli import main

example_ids = [
    "DBLP:conf/spire/BastMW06",
    "conf/spire/BastMW06",
    "doi:10.1007/11880561_13",
    "10.1007/11880561_13",
]

expected = dict((f, helpers.example_file(f"{f}.bib")) for f in formats.BIB_FORMATS)
expected_from_doi_org = helpers.example_file("doi.org.bib")


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
    helpers.compare_line_by_line(result.stdout, expected[format])


@pytest.mark.parametrize("id", ["isbn:3-540-45774-7"])
@pytest.mark.parametrize("format", formats.BIB_FORMATS)
def test_get_isbn(id, format):
    """
    When retrieving and printing DBLP entries,
    we must produce exactly the same output as DBLP
    (even if the bib-entry was parsed with pybtex in between).
    """
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, ["--format", format, "get", id, "--reparse", "all"])
    assert result.exit_code == 0
    helpers.compare_line_by_line(
        result.stdout, helpers.example_file(f"3540457747-{format}.bib")
    )


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
    helpers.compare_parsed(result.stdout, expected_from_doi_org)


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
