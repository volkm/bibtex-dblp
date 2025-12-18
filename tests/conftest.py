import os
import pytest

from bibtex_dblp.dblp_api import DblpSession


@pytest.fixture(scope="session")
def dblp_session():
    return DblpSession(wait_time=7)


def bib_path(*paths):
    return os.path.join(os.path.dirname(__file__), "files", *paths)
