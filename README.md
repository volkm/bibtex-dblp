# bibtex-dblp
Create and revise bibtex entries from [DBLP](https://dblp.uni-trier.de/).

# Dependencies
- uses [pybtex](https://pybtex.org/)
- inspired from [dblp-python](https://github.com/scholrly/dblp-python)

# Installation
The package can be installed from [PyPI](https://pypi.org/) with:
```
pip install bibtex-dblp
```


# Usage

# Importing new publications from DBLP
The script `bin/import_dblp.py` searches for a new publication on DBLP and adds the corresponding bibtex entry to the bibliography.

Usage:
```
import_dblp [--query QUERY] [--out OUT] [--format {condensed,standard,crossref}]
```

If the argument `--query` is not given, the search keywords can be given directly in the terminal.
The script then queries the DBLP API and displays the possible matches.
The correct publication can be selected in the terminal (or `0` for abort).
The bibtex entry of the selected publication is either appended to the given bibliography (if `--out` is provided) or displayed on the terminal.

For more options see:
```
import_dblp --help
```

# Converting between DBLP formats
The script `bin/convert_dblp.py` converts the complete bibliography between different DBLP formats (condensed, standard, crossref).

Usage:
```
convert_dblp INPUT_BIB [--out OUTPUT_BIB] [--format {condensed,standard,crossref}]
```
All bibtex entries with either the field `biburl` given or a bibtex name corresponding to a DBLP id are automatically converted.
All other entries are left unchanged.

For more options see:
```
convert_dblp --help
```
