import pytest
from click.testing import CliRunner
import logging

import bibtex_dblp.config as config
from bibtex_dblp.cli import main
from bibtex_dblp.dblp_api import sanitize_key

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

expected = {
    "condensed": """@inproceedings{DBLP:conf/spire/BastMW06,
    author = "Bast, H. and Mortensen, Christian Worm and Weber, Ingmar",
    title = "Output-Sensitive Autocompletion Search",
    booktitle = "{SPIRE}",
    series = "Lecture Notes in Computer Science",
    volume = "4209",
    pages = "150--162",
    publisher = "Springer",
    year = "2006"
}""",
    "standard": """@inproceedings{DBLP:conf/spire/BastMW06,
    author = "Bast, H. and Mortensen, Christian Worm and Weber, Ingmar",
    editor = "Crestani, Fabio and Ferragina, Paolo and Sanderson, Mark",
    title = "Output-Sensitive Autocompletion Search",
    booktitle = "String Processing and Information Retrieval, 13th International Conference, {SPIRE} 2006, Glasgow, UK, October 11-13, 2006, Proceedings",
    series = "Lecture Notes in Computer Science",
    volume = "4209",
    pages = "150--162",
    publisher = "Springer",
    year = "2006",
    url = "https://doi.org/10.1007/11880561\\_13",
    doi = "10.1007/11880561\\_13",
    timestamp = "Fri, 31 May 2019 11:59:54 +0200",
    biburl = "https://dblp.org/rec/conf/spire/BastMW06.bib",
    bibsource = "dblp computer science bibliography, https://dblp.org"
}""",
    "crossref": """@inproceedings{DBLP:conf/spire/BastMW06,
    author = "Bast, H. and Mortensen, Christian Worm and Weber, Ingmar",
    title = "Output-Sensitive Autocompletion Search",
    booktitle = "String Processing and Information Retrieval, 13th International Conference, {SPIRE} 2006, Glasgow, UK, October 11-13, 2006, Proceedings",
    pages = "150--162",
    year = "2006",
    crossref = "DBLP:conf/spire/2006",
    url = "https://doi.org/10.1007/11880561\\_13",
    doi = "10.1007/11880561\\_13",
    timestamp = "Fri, 31 May 2019 11:59:54 +0200",
    biburl = "https://dblp.org/rec/conf/spire/BastMW06.bib",
    bibsource = "dblp computer science bibliography, https://dblp.org"
}

@proceedings{DBLP:conf/spire/2006,
    editor = "Crestani, Fabio and Ferragina, Paolo and Sanderson, Mark",
    title = "String Processing and Information Retrieval, 13th International Conference, {SPIRE} 2006, Glasgow, UK, October 11-13, 2006, Proceedings",
    series = "Lecture Notes in Computer Science",
    volume = "4209",
    publisher = "Springer",
    year = "2006",
    url = "https://doi.org/10.1007/11880561",
    doi = "10.1007/11880561",
    isbn = "3-540-45774-7",
    timestamp = "Tue, 14 May 2019 10:00:55 +0200",
    biburl = "https://dblp.org/rec/conf/spire/2006.bib",
    bibsource = "dblp computer science bibliography, https://dblp.org"
}""",
}


@pytest.mark.parametrize("entry", example_entries)
@pytest.mark.parametrize("format", config.BIB_FORMATS)
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

