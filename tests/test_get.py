import pytest
from click.testing import CliRunner

import bibtex_dblp.config as config
from bibtex_dblp.cli import main
from bibtex_dblp.dblp_api import sanitize_key

example_ids = [
    "DBLP:conf/spire/BastMW06",
    "conf/spire/BastMW06",
    "doi:10.1007/11880561_13",
    "10.1007/11880561_13",
]

expected = {
    "condensed": """@inproceedings{DBLP:conf/spire/BastMW06,
  author    = {H. Bast and
               Christian Worm Mortensen and
               Ingmar Weber},
  title     = {Output-Sensitive Autocompletion Search},
  booktitle = {{SPIRE}},
  series    = {Lecture Notes in Computer Science},
  volume    = {4209},
  pages     = {150--162},
  publisher = {Springer},
  year      = {2006}
}""",
    "standard": """@inproceedings{DBLP:conf/spire/BastMW06,
  author    = {H. Bast and
               Christian Worm Mortensen and
               Ingmar Weber},
  editor    = {Fabio Crestani and
               Paolo Ferragina and
               Mark Sanderson},
  title     = {Output-Sensitive Autocompletion Search},
  booktitle = {String Processing and Information Retrieval, 13th International Conference,
               {SPIRE} 2006, Glasgow, UK, October 11-13, 2006, Proceedings},
  series    = {Lecture Notes in Computer Science},
  volume    = {4209},
  pages     = {150--162},
  publisher = {Springer},
  year      = {2006},
  url       = {https://doi.org/10.1007/11880561\\_13},
  doi       = {10.1007/11880561\\_13},
  timestamp = {Fri, 31 May 2019 11:59:54 +0200},
  biburl    = {https://dblp.org/rec/conf/spire/BastMW06.bib},
  bibsource = {dblp computer science bibliography, https://dblp.org}
}""",
    "crossref": """@inproceedings{DBLP:conf/spire/BastMW06,
  author    = {H. Bast and
               Christian Worm Mortensen and
               Ingmar Weber},
  title     = {Output-Sensitive Autocompletion Search},
  booktitle = {String Processing and Information Retrieval, 13th International Conference,
               {SPIRE} 2006, Glasgow, UK, October 11-13, 2006, Proceedings},
  pages     = {150--162},
  year      = {2006},
  crossref  = {DBLP:conf/spire/2006},
  url       = {https://doi.org/10.1007/11880561\\_13},
  doi       = {10.1007/11880561\\_13},
  timestamp = {Fri, 31 May 2019 11:59:54 +0200},
  biburl    = {https://dblp.org/rec/conf/spire/BastMW06.bib},
  bibsource = {dblp computer science bibliography, https://dblp.org}
}

@proceedings{DBLP:conf/spire/2006,
  editor    = {Fabio Crestani and
               Paolo Ferragina and
               Mark Sanderson},
  title     = {String Processing and Information Retrieval, 13th International Conference,
               {SPIRE} 2006, Glasgow, UK, October 11-13, 2006, Proceedings},
  series    = {Lecture Notes in Computer Science},
  volume    = {4209},
  publisher = {Springer},
  year      = {2006},
  url       = {https://doi.org/10.1007/11880561},
  doi       = {10.1007/11880561},
  isbn      = {3-540-45774-7},
  timestamp = {Tue, 14 May 2019 10:00:55 +0200},
  biburl    = {https://dblp.org/rec/conf/spire/2006.bib},
  bibsource = {dblp computer science bibliography, https://dblp.org}
}""",
}

expected_from_doi_org = """@incollection{Bast_2006,
	doi = {10.1007/11880561_13},
	url = {https://doi.org/10.1007%2F11880561_13},
	year = 2006,
	publisher = {Springer Berlin Heidelberg},
	pages = {150--162},
	author = {Holger Bast and Christian W. Mortensen and Ingmar Weber},
	title = {Output-Sensitive Autocompletion Search},
	booktitle = {String Processing and Information Retrieval}
}"""


@pytest.mark.parametrize("id", example_ids)
@pytest.mark.parametrize("format", config.BIB_FORMATS)
def test_get(id, format):
    runner = CliRunner(mix_stderr=False)
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["--format", format, "get", id])
        assert result.exit_code == 0
        output = result.stdout.strip().split("\n")
        exp = expected[format].strip().split("\n")
        assert len(output) == len(exp)
        for i in range(len(output)):
            if "timestamp" not in output[i]:
                assert output[i] == exp[i]


@pytest.mark.parametrize(
    "id", [id for id in example_ids if sanitize_key(id)[0] == "DOI"]
)
def test_get_doi_org(id):
    runner = CliRunner(mix_stderr=False)
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["--prefer-doi-org", "get", id])
        assert result.exit_code == 0
        output = result.stdout.strip().split("\n")
        exp = expected_from_doi_org.strip().split("\n")
        assert len(output) == len(exp)
        for i in range(len(output)):
            assert output[i] == exp[i]
