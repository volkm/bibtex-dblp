import os
from setuptools import setup

# Get the long description from the README file
with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'README.md')) as f:
    long_description = f.read()

setup(
    name="bibtex-dblp",
    version="0.1",
    author="M. Volk",
    author_email="matthias.volk@cs.rwth-aachen.de",
    maintainer="M. Volk",
    maintainer_email="matthias.volk@cs.rwth-aachen.de",
    url="https://github.com/volkm/bibtex-dblp",
    description="Create and revise bibtex entries from DBLP.",
    long_description=long_description,
    long_description_content_type='text/markdown',

    packages=["bibtex_dblp"],
    install_requires=[
        "requests",
        "pybtex"
    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    python_requires='>=3',
)
