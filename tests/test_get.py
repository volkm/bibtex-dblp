from pathlib import Path

import pytest
from click.testing import CliRunner

import bibtex_dblp.dblp_api as api
from bibtex_dblp.cli import main

example_ids = [
    "DBLP:conf/spire/BastMW06",
    "conf/spire/BastMW06",
    "doi:10.1007/11880561_13",
    "10.1007/11880561_13",
]

FILES_DIR = Path("tests") / Path("files")
expected = dict((f, open(FILES_DIR / Path(f"{f}.bib")).read()) for f in api.BIB_FORMATS)
expected_from_doi_org = open(FILES_DIR / Path("doi.org.bib")).read()


@pytest.mark.parametrize("id", example_ids)
@pytest.mark.parametrize("format", api.BIB_FORMATS)
def test_get(id, format):
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, ["--format", format, "get", id])
    assert result.exit_code == 0
    output = result.stdout.strip().split("\n")
    exp = expected[format].strip().split("\n")
    assert len(output) == len(exp)
    for i in range(len(output)):
        if "timestamp" not in output[i]:
            assert output[i] == exp[i]


@pytest.mark.parametrize(
    "id", [id for id in example_ids if api.paper_id_from_key(id).namespace == api.DOI]
)
def test_get_doi_org(id):
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, ["--prefer-doi-org", "get", id])
    assert result.exit_code == 0
    output = result.stdout.strip().split("\n")
    exp = expected_from_doi_org.strip().split("\n")
    assert len(output) == len(exp)
    for i in range(len(output)):
        assert output[i] == exp[i]


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
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, ["get", id])
    assert result.exit_code == 0
    output = result.stdout.strip()
    assert output == ""
