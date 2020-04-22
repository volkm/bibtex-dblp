#!/usr/bin/env python

import json
import logging
import sys

import click

import bibtex_dblp.config as config
import bibtex_dblp.database
import bibtex_dblp.dblp_api as api


@click.group()
@click.version_option(version=config.VERSION)
@click.option("-v", "--verbose", help="Print debug output.", is_flag=True)
@click.option("-q", "--quiet", help="Only produce necessary output.", is_flag=True)
@click.option(
    "-c", "--config-file", help="Use this config file instead of the default."
)
@click.option(
    "--prefer-doi-org",
    help="When retrieving bib-entries via their DOI, try to resolve them with doi.org first.",
    is_flag=True,
)
@click.option(
    "-f",
    "--format",
    help="bib-entry format that should be used for output.",
    envvar="BIBTEX_DBLP_FORMAT",
    type=click.Choice(api.BIB_FORMATS, case_sensitive=False),
)
@click.pass_context
def main(ctx, **kwargs):
    """Tools for querying the DBLP database and processing its data."""

    if kwargs["verbose"]:
        level = logging.DEBUG
    elif kwargs["quiet"]:
        level = logging.ERROR
    else:
        level = logging.INFO

    logging.basicConfig(format="%(levelname)s: %(message)s", level=level)

    ctx.obj = config.Config(kwargs["config_file"])

    ctx.obj.set_cmd_line("format", kwargs["format"])
    ctx.obj.set_cmd_line("quiet", kwargs["quiet"])
    ctx.obj.set_cmd_line("prefer_doi_org", kwargs["prefer_doi_org"])


@main.command()
@click.argument("key", nargs=-1)
@click.pass_context
def get(ctx, key):
    """Retrieve bib entries by their global keys, and print them.

\b
Supported key types:
- DBLP ids (e.g., DBLP:conf/spire/BastMW06)
- DOIs (e.g., doi:10.1007/11880561_13)

If the prefix ("DBLP:" or "doi:") is omitted, we will guess based on the number of slashes.

Examples:

\b
$ dblp get DBLP:conf/spire/BastMW06
$ dblp --format standard get DBLP:conf/spire/BastMW06 10.2307/2268281
$ echo "DBLP:conf/spire/BastMW06\n10.2307/2268281" | dblp get
"""
    if len(key) == 0:
        key = (k.strip() for k in sys.stdin.readlines())
    for k in key:
        b = bibtex_dblp.dblp_api.get_bibtex(
            k,
            bib_format=ctx.obj.get("format"),
            prefer_doi_org=ctx.obj.get("prefer_doi_org"),
        )
        if b is not None:
            click.echo(b)


@main.command("import")
@click.option(
    "-q",
    "--query",
    help="Query for the DBLP database. Will try to match the title field. If not given, an interactive prompt will ask for it.",
)
@click.option(
    "-b",
    "--bib",
    type=click.Path(exists=True),
    help="If specified, the bib-entry will be appended to this .bib file. Otherwise, the bib-entry is printed to standard output.",
)
@click.option(
    "--max-results",
    help="Maximal number of search results to display.",
    envvar="BIBTEX_MAX_SEARCH_RESULTS",
)
@click.pass_context
def import_(ctx, query, bib, max_results):
    """Interactively query the DBLP database and print a bib-entry.

Examples:


$ dblp import

Query DBLP and retrieve a bib-entry in "condensed" format.


$ dblp --format standard import --query "Output-Sensitive Autocompletion Search" --bib references.bib

Query the database for a paper title and append the selected bib-entry to references.bib (if it does not exist there yet).
"""
    if query is None:
        query = click.prompt("Query the DBLP database for these keywords", err=True)
    bib_key, bib_entry = ask_about_possible_duplicates(bib, query)
    ctx.obj.set_cmd_line("max_search_results", max_results)

    if bib_entry is None:
        bib_key = ask_to_select_from_search_result(
            query, ctx.obj.get("max_search_results")
        )
        bib_entry = bibtex_dblp.dblp_api.get_bibtex(
            bib_key,
            bib_format=ctx.obj.get("format"),
            prefer_doi_org=ctx.obj.get("prefer_doi_org"),
        )
    else:
        bib = None

    if bib:
        with open(bib, "a") as f:
            f.write(bib_entry)
        logging.info(f"Bib-entry appended to {bib}.")
    else:
        logging.info("Selected bib-entry:\n")
        print(bib_entry)
    logging.info(f"Use '{bib_key}' to cite it.")


def ask_about_possible_duplicates(bib, query):
    """Check if a match is already found in the existing bib-file."""
    if bib is not None:
        bib_contents = bibtex_dblp.database.load_from_file(bib)
        bib_result = bibtex_dblp.database.search(bib_contents, query)
        if bib_result:
            print(f"Your file {bib} already contains the following, similar matches:")
            for i in range(len(bib_result)):
                print(f"({i+1})\t{bibtex_dblp.database.print_entry(bib_result[i][0])}")
            select = click.prompt(
                "Select the intended publication (0 to search online): ",
                type=click.IntRange(0, len(bib_result)),
                default=0,
                err=True,
            )
            if select > 0:
                selected = bib_result[select - 1][0]
                selected_bib_key = selected.key
                selected_bib_entry = bibtex_dblp.database.print_entry(selected)
                return selected_bib_key, selected_bib_entry
    return None, None


def ask_to_select_from_search_result(query, max_results):
    search_results = bibtex_dblp.dblp_api.search_publication(
        query, max_search_results=max_results
    )
    if search_results.total_matches == 0:
        logging.error("The search returned no matches.")
        exit(1)

    print(
        f"The search returned {search_results.total_matches} matches:", file=sys.stderr
    )
    if search_results.total_matches > max_results:
        print(f"Displaying only the first {max_results} matches.", file=sys.stderr)
    for i in range(len(search_results.results)):
        result = search_results.results[i]
        print(f"({i+1})\t{result.publication}", file=sys.stderr)

    select = click.prompt(
        "Select the intended publication (0 to search online): ",
        type=click.IntRange(0, search_results.total_matches),
        default=0,
        err=True,
    )
    if select == 0:
        print("Cancelled.", file=sys.stderr)
        exit(1)

    publication = search_results.results[select - 1].publication
    return publication.cite_key()


@main.command()
@click.argument("input", type=click.Path(), required=False)
@click.argument("output", type=click.Path(), required=False)
@click.pass_context
def convert(ctx, input, output):
    """Convert bib-entries between different DBLP formats.

Examples:


$ dblp convert references.bib

Reads the file references.bib, converts each entry that is found in DBLP to the configured, and writes the results back to references.bib. (The format can be specified on the command line, be given in the environment as BIBTEX_DBLP_FORMAT, or be set in the config file. See: dblp config --help)


$ dblp --format standard convert

Reads from standard input and writes the output in "standard" format to standard output.


$ dblp convert input.bib output.bib

Reads from input.bib and writes output.bib
"""
    if input is None or input == "-":
        input = sys.stdin
        output = sys.stdout
    else:
        if output is None:
            output = input
        elif output == "-":
            output = sys.stdout

    bib = bibtex_dblp.database.load_from_file(input)
    bib, no_changes = bibtex_dblp.database.convert_dblp_entries(
        bib, bib_format=ctx.obj.get("format")
    )

    if not ctx.obj.get("quiet"):
        click.echo(
            f"Updated {no_changes} entries (out of {len(bib.entries)}) from DBLP",
            file=sys.stderr,
        )
    bibtex_dblp.database.write_to_file(bib, output)
    if not ctx.obj.get("quiet"):
        click.echo(f"Written to {output}", file=sys.stderr)


@main.command()
@click.argument("auxfile", type=click.Path())
@click.pass_context
def citations(ctx, auxfile):
    """Extract all citations from an .aux file.

If you always use DOIs or DBLP ids as citation keys, you can generate the entire bibliography as follows:

\b
$ latex main.tex
$ dblp citations main | dblp get > main.bib
"""
    from pybtex.auxfile import parse_file

    if not auxfile.endswith(".aux"):
        auxfile = auxfile + ".aux"
    aux = parse_file(auxfile)
    click.echo("\n".join(sorted(set(aux.citations))))


@main.command("config")
@click.option("--get", help="get value.")
@click.option(
    "--set", nargs=2, help="Set a key/value pair and write it to the config file."
)
@click.option("--unset", help="Remove a given key from the config file.")
@click.pass_context
def config_(ctx, set, get, unset):
    """Write configuration to the config file.

\b
Examples:

$ dblp config

Prints the current configuration options and the location of the configuarion file.


$ dblp config --set format standard

This sets the default bib-format to "standard". Can be overridden by using --format explicitly.


$ dblp config --unset format

Delete the format setting from the configuration file.
"""
    if get is None and len(set) == 0 and unset is None:
        if len(ctx.obj.config) > 0:
            click.echo(f"Current configuration as read from {ctx.obj.config_file}:")
            j = json.dumps(ctx.obj.config, indent=2)
            click.echo(j)
        else:
            click.echo(
                f"""No configuration options are set in {config.CONFIG_FILE}.
Try: dblp config --help"""
            )
    elif get is not None:
        k = get
        v, c = ctx.obj.get_with_source(k)
        click.echo(f"The value of {k} is:\n{v}\n[This value was defined in {c}]")
    elif len(set) > 0:
        k, v = set
        ctx.obj.set(k, v)
        ctx.obj.save()
    elif unset is not None:
        k = unset
        ctx.obj.unset(k)
        ctx.obj.save()


if __name__ == "__main__":
    main()  # pylint: disable=all
