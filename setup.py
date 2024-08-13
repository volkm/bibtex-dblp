from setuptools import setup

setup(
    packages=["bibtex_dblp"],
    scripts=[
        "bin/import_dblp.py",
        "bin/convert_dblp.py",
        "bin/update_from_dblp.py",
    ],
)
