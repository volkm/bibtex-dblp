# bibtex-dblp
[![Build Status](https://github.com/volkm/bibtex-dblp/workflows/Build%20and%20Test/badge.svg)](https://github.com/volkm/bibtex-dblp/actions)
[![GitHub release](https://img.shields.io/github/release/volkm/bibtex-dblp.svg)](https://github.com/volkm/bibtex-dblp/releases/)
[![PyPi](https://img.shields.io/pypi/v/bibtex-dblp)](https://pypi.org/project/bibtex-dblp/)

Create and revise bibtex entries from [DBLP](https://dblp.uni-trier.de/).

## Dependencies
- uses [pybtex](https://pybtex.org/)
- inspired from [dblp-python](https://github.com/scholrly/dblp-python)

## Installation
The package can be installed from [PyPI](https://pypi.org/) with:
```
pip install bibtex-dblp
```

Manual installation is possible by cloning this repository and building the Python package:
```
pip install .
```


## Usage

All relevant scripts can be found in the `bin` directory.
Every script provides information about the expected input and additional arguments via `--help`.


### Importing new publications from DBLP
The script `bin/import_dblp.py` searches for a new publication on DBLP and adds the corresponding bibtex entry to the bibliography.

Usage:
```
import_dblp [--query QUERY] [--bib BIBTEX] [--format FORMAT]
```

If the argument `--query` is not given, the search keywords can be given directly in the terminal.
The script then queries the DBLP API and displays the possible matches.
The correct publication number can be selected in the terminal (or `0` for abort).
The bibtex entry of the selected publication is either appended to the given bibliography (if `--bib` is provided) or displayed on the terminal.

### Converting between DBLP formats
The script `bin/convert_dblp.py` converts the complete bibliography between different DBLP formats.

Usage:
```
convert_dblp INPUT_BIB [--out OUTPUT_BIB] [--format FORMAT]
```
All bibtex entries with either the field `biburl` given or a bibtex name corresponding to a DBLP id are automatically converted into the desired format.
All other entries are left unchanged.

### Updating existing bibliography from DBLP
The script `bin/update_from_dblp.py` updates the entries in an existing bibliography by looking up the information from DBLP.

Usage:
```
update_from_dblp INPUT_BIB [--out OUTPUT_BIB] [--format FORMAT]
```
For each bibtex entry without a DBLP id, the scripts searches DBLP for a possible match.
The user can select the correct entry from a list of possible matches and the bibliography is updated accordingly.
Bibtex entries which already have a DBLP id are left unchanged.


### Modifying bibliography
The script `bin/modify_bibtex.py` allows apply some modifications on the bibtex file:
- `--no-escape` removes the escape characters in front of underscores for fields `url` and `doi`. So `\_` becomes `_`. Note that this requires the packages such as `hyperref` in LaTeX to properly compile.
- `--no-timestamp`, `--no-biburl` and `--no-bibsource` can be added to remove the corresponding fields `timestamp`, `biburl` and `bibsource`, respectively, from the bibtex file.

## Supported DBLP formats
The following bibtex formats from DBLP are currently supported:
- `condensed`: Condensed format where e.g. journals and conferences are abbreviated. Default value.
- `standard`: Default format from DBLP.
- `crossref`: Extensive format in which conferences have their own bibtex entry
- `condensed_doi`: Corresponds to `condensed` but additionally includes the DOI
