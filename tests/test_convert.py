from pathlib import Path

import pytest
from click.testing import CliRunner
from pybtex.database import parse_string

from bibtex_dblp.formats import BIB_FORMATS
from bibtex_dblp.cli import main

example_entries = [
    """@inproceedings{DBLP:conf/spire/BastMW06,
title     = {identify this entry by key},
}""",
    """@inproceedings{10.1007/11880561_13,
title     = {identify this entry by key},
}""",
    """@inproceedings{preserve:this:key,
title     = {identify this by biburl},
biburl    = {https://dblp.org/rec/conf/spire/BastMW06.bib},
}""",
    """@inproceedings{preserve:this:key,
title     = {identify this by doi},
doi       = {10.1007/11880561\\_13},
}""",
    """@inproceedings{preserve:this:key,
  title     = {identify this by doi},
  doi       = {10.1007/11880561_13},
}""",
]

FILES_DIR = Path("tests") / Path("files")


def example_file(f):
    bibfile = open(FILES_DIR / Path(f + ".bib")).read()
    parsed = parse_string(bibfile, bib_format="bibtex")
    pybtex_output = parsed.to_string(bib_format="bibtex")
    return pybtex_output


expected = dict((f, example_file(f)) for f in BIB_FORMATS)
expected_from_doi_org = example_file("doi.org")


@pytest.mark.parametrize("entry", example_entries)
@pytest.mark.parametrize("format", BIB_FORMATS)
def test_convert(entry, format):
    runner = CliRunner(mix_stderr=False)
    with runner.isolated_filesystem():
        with open("test.bib", "w") as f:
            f.write(entry)
        result = runner.invoke(
            main, ["--quiet", "--format", format, "convert", "test.bib"]
        )
        assert result.exit_code == 0
        with open("test.bib", "r") as f:
            output = f.read(99999999)
        output = [line.strip() for line in output.strip().split("\n")]
        exp = [line.strip() for line in expected[format].strip().split("\n")]
        assert len(output) == len(exp)
        for i in range(len(output)):
            if i == 0:
                assert output[0] == entry.strip().split("\n")[0]
            elif "timestamp" not in output[i]:
                assert output[i].replace("\\", "") == exp[i].replace("\\", "")
