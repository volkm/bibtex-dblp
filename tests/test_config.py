import json

import pytest
from click.testing import CliRunner

from bibtex_dblp.cli import main
from bibtex_dblp.formats import BIB_FORMATS


@pytest.mark.parametrize(
    "kv",
    [("format", v) for v in BIB_FORMATS]
    + [("max_search_results", v) for v in range(2)],
)
def test_set_unset_get(kv):
    k, v = kv
    runner = CliRunner(mix_stderr=False)
    with runner.isolated_filesystem():
        result = runner.invoke(
            main, ["--config-file", "config.json", "config", "--set", k, v]
        )
        assert result.exit_code == 0
        j = json.load(open("config.json"))
        assert len(j) == 1
        assert j[k] == v
        result = runner.invoke(
            main, ["--config-file", "config.json", "config", "--get", k]
        )
        assert result.exit_code == 0
        assert str(v) == result.stdout.split("\n")[1].strip()
        result = runner.invoke(
            main, ["--config-file", "config.json", "config", "--unset", k]
        )
        assert result.exit_code == 0
        j = json.load(open("config.json"))
        assert len(j) == 0
