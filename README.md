# bibtex-dblp
Retrieve and revise bibtex entries from [DBLP](https://dblp.org/).

Inspired by [dblp-python](https://github.com/scholrly/dblp-python).

# Dependencies
- [pybtex](https://pybtex.org/) - BibTeX-compatible bibliography processor
- [click](https://click.palletsprojects.com/) - Python composable command line interface toolkit
- [requests](https://requests.readthedocs.io/) - Elegant and simple HTTP library

# Installation
The package can be installed from [PyPI](https://pypi.org/) with:
```
pip install bibtex-dblp
```

## Shell completion
To enable tab-completion, run the following commands, depending on your shell:
```
mkdir -p ~/.local/share/bibtex-dblp/
_DBLP_COMPLETE=source_bash dblp > ~/.local/share/bibtex-dblp/dblp-complete.bash
_DBLP_COMPLETE=source_zsh dblp > ~/.local/share/bibtex-dblp/dblp-complete.zsh
_DBLP_COMPLETE=source_fish dblp > ~/.config/fish/completions/dblp-complete.fish
```
For bash and zsh, these completion scripts need to be sourced in their startup scripts:
```
echo "source ~/.local/share/bibtex-dblp/dblp-complete.bash" >> ~/.bashrc
echo "source ~/.local/share/bibtex-dblp/dblp-complete.zsh" >> ~/.zshrc
```

# Usage

## Importing new publications from DBLP
The command `dblp import` searches for a publication on DBLP and adds the corresponding bibtex entry to a local bibliography.

Usage:
```
dblp import [--query QUERY] [--bib BIBTEX]
```

If the argument `--query` is not given, an interactive prompt will ask for the search keywords.
The script then queries the DBLP API and displays the possible matches.
The correct publication can be selected in the terminal (or `0` for abort).
The bibtex entry of the selected publication is either appended to the given bibliography (if `--bib` is provided) or displayed on the terminal.

For more options see:
```
dblp import --help
```

## Configuration

The DBLP server offers each bib-entry in three different formats: condensed ([example](https://dblp.org/rec/bibtex0/conf/spire/BastMW06)), standard ([example](https://dblp.org/rec/bibtex1/conf/spire/BastMW06)), crossref ([example](https://dblp.org/rec/bibtex2/conf/spire/BastMW06)).
The default setting of `dblp` is condensed, but some users prefer other formats.
To change the default format, `dblp` offers three different mechanisms:

### User configuration file
```
dblp config --set format standard
```
This makes the new setting persistent by writing it to a per-user configuration file.

### Environment variable
```
DBLP_FORMAT=standard dblp [...]
```
If the environment variable `DBLP_FORMAT` is defined, it will be used regardless of what is written in the config file.

### Command line option

```
dblp --format standard import [...]
```
If the `--format` command line option is used, its setting takes precedence. Note that `--format` must be specified _before_ the command (such as `import`).


## Converting between DBLP formats
The command `dblp convert` converts the complete bibliography to the selected DBLP format (condensed, standard, crossref).

Usage:
```
dblp [--format {condensed,standard,crossref}] convert [INPUT_BIB] [OUTPUT_BIB]
```
All bibtex entries with either the field `biburl` given or a bibtex name corresponding to a DBLP id are automatically converted.
All other entries are left unchanged.

For more options see:
```
dblp convert --help
```

## Get bibtex entry from given global id

Every publication listed on DBLP has a unique DBLP id (for example [DBLP:journals/ir/BastMW08](https://dblp.org/rec/bibtex1/journals/ir/BastMW08)).
Most modern peer-reviewed publications have a DOI (for example, 10.1007/s10791-008-9048-x).
The command `dblp get` finds a bibtex entry for the given DBLP id or DOI.

For example:
```
dblp get DBLP:journals/ir/BastMW08
```
fetches the bib entry of the paper [Output-sensitive autocompletion search](https://dblp.org/rec/bibtex1/journals/ir/BastMW08) from the url `https://dblp.org/rec/bib1/journals/ir/BastMW08.bib` and writes it to standard output.
It is also possible to get the same entry via its DOI as follows:
```
dblp get doi:10.1007/s10791-008-9048-x
```
This will fetch the URL `https://dblp.org/doi/bib1/10.1007/s10791-008-9048-x`.
For convenience, the `DBLP:` or `doi:` prefixes are not case sensitive. In case the prefix is missing, `get` will assume that the key is a DBLP id if it contains at least two slashes, and it assumes that it is a DOI if there is exactly one slash.
So both of these commands also work:
```
dblp get journals/ir/BastMW08
dblp get 10.1007/s10791-008-9048-x
```
If you want to append an entry to an existing .bib file, simply use this command:
```
dblp get DBLP:journals/ir/BastMW08 >> references.bib
```
(This does not check for duplicates.)

Is is also possible to get multiple entries:
```
dblp --format standard get DBLP:conf/spire/BastMW06 10.2307/2268281
```
For scripting purposes, the entries can also be read from standard input (one per line):
```
echo "DBLP:conf/spire/BastMW06\n10.2307/2268281" | dblp get
```
ISBNs (as far as they're available on dblp.org) are also supported:
```
dblp get ISBN:3-540-45774-7
```

# Development

Create a development environment in editable mode:
```
pipenv install -e . --dev
```

Run the script in the test environment:
```
pipenv run dblp
```

Run the tests:
```
pipenv run pytest
```

Run the code cleanup and linter tools ([black](https://black.readthedocs.io/en/stable/), [isort](https://timothycrosley.github.io/isort/), [flake8](https://flake8.pycqa.org/en/latest/)):
```
pipenv run black .
pipenv run isort -y
pipenv run flake8
```

Create package and upload to pypi.org:
```
python3 setup.py sdist bdist_wheel
python3 -m twine upload dist/*
```
