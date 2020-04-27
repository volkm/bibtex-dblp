import pytest
from click.testing import CliRunner

import bibtex_dblp.database as db
import helpers
from bibtex_dblp.cli import main

expected = {"Mehlhorn:Kurt": set(helpers.example_file("Mehlhorn_Kurt").strip().split())}


@pytest.mark.parametrize("author, existing_papers", expected.items())
def test_get_author(author, existing_papers):
    """
    When retrieving and printing DBLP entries,
    we must produce exactly the same output as DBLP
    (even if the bib-entry was parsed with pybtex in between).
    """
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        main, ["--format", "standard", "get-author", author, "--reparse", "all"]
    )
    assert result.exit_code == 0
    parsed = db.parse_bibtex(result.stdout)
    received_paper_keys = set(parsed.entries.keys())
    for existing_paper in existing_papers:
        assert existing_paper in received_paper_keys


def test_get_nonexisting_author():
    """
    When retrieving non-existing IDs, nothing should be printed.
    """
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        main, ["get-author", "Iamanonexistinglastname:Bogusfirstnameaswell"]
    )
    assert result.exit_code == 0
    output = result.stdout.strip()
    assert output == ""
