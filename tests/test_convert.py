import pytest
from click.testing import CliRunner

import helpers
from bibtex_dblp.cli import main
from bibtex_dblp.formats import BIB_FORMATS, STANDARD


@pytest.mark.parametrize("input", [helpers.example_file("convert-in.bib")])
@pytest.mark.parametrize("format", BIB_FORMATS)
def test_convert_formats(input, format):
    expected_output = helpers.example_file(f"convert-out-{format}.bib")
    runner = CliRunner(mix_stderr=False)
    with runner.isolated_filesystem():
        with open("test.bib", "w") as f:
            f.write(input)
        result = runner.invoke(
            main, ["--quiet", "--format", format, "convert", "test.bib"]
        )
        assert result.exit_code == 0
        output = open("test.bib", "r").read()
        helpers.compare_line_by_line(output, expected_output)


@pytest.mark.parametrize("input", [helpers.example_file("convert-in.bib")])
@pytest.mark.parametrize("format", [STANDARD])
def test_convert_stdin(input, format):
    expected_output = helpers.example_file(f"convert-out-{format}.bib")
    runner = CliRunner(mix_stderr=False)
    with runner.isolated_filesystem():
        result = runner.invoke(
            main, ["--quiet", "--format", format, "convert"], input=input
        )
        assert result.exit_code == 0
        helpers.compare_line_by_line(result.stdout, expected_output)
