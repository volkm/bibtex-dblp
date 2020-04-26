from pathlib import Path

import pytest
from click.testing import CliRunner

from bibtex_dblp.cli import main
from bibtex_dblp.formats import BIB_FORMATS, STANDARD

FILES_DIR = Path("tests") / Path("files")


def example_file(f):
    return open(FILES_DIR / Path(f + ".bib")).read()


def bibfiles_same(a, b):
    a = [line.strip() for line in a.strip().split("\n")]
    b = [line.strip() for line in b.strip().split("\n")]
    assert len(a) == len(b)
    for i in range(len(a)):
        if "timestamp" not in a[i]:
            assert a[i].replace("\\", "") == b[i].replace("\\", "")


@pytest.mark.parametrize("input", [example_file("convert-in")])
@pytest.mark.parametrize("format", BIB_FORMATS)
def test_convert_formats(input, format):
    expected_output = example_file(f"convert-out-{format}")
    runner = CliRunner(mix_stderr=False)
    with runner.isolated_filesystem():
        with open("test.bib", "w") as f:
            f.write(input)
        result = runner.invoke(
            main, ["--quiet", "--format", format, "convert", "test.bib"]
        )
        assert result.exit_code == 0
        with open("test.bib", "r") as f:
            output = f.read()
        bibfiles_same(output, expected_output)


@pytest.mark.parametrize("input", [example_file("convert-in")])
@pytest.mark.parametrize("format", [STANDARD])
def test_convert_stdin(input, format):
    expected_output = example_file(f"convert-out-{format}")
    runner = CliRunner(mix_stderr=False)
    with runner.isolated_filesystem():
        result = runner.invoke(
            main, ["--quiet", "--format", format, "convert"], input=input
        )
        assert result.exit_code == 0
        bibfiles_same(result.stdout, expected_output)
