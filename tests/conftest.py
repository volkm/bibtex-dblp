import os


def bib_path(*paths):
    return os.path.join(os.path.dirname(__file__), "files", *paths)
