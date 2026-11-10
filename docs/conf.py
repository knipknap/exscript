"""
Sphinx configuration for the Exscript documentation.

Build it from the repository root::

    uv run --group docs sphinx-build -W --keep-going docs docs/_build/html
"""

import importlib.metadata
import os
import subprocess
import sys
from pathlib import Path

# The command line reference includes the output of "exscript --help". Sphinx
# runs this file in the docs directory.
_help = subprocess.run(
    [sys.executable, "-m", "Exscript", "--help"],
    capture_output=True,
    check=True,
    encoding="utf-8",
    env=dict(os.environ, COLUMNS="80", NO_COLOR="1"),
).stdout
Path("_generated").mkdir(exist_ok=True)
Path("_generated/exscript-help.txt").write_text(_help, encoding="utf-8")

# The list of drivers, from the docstrings of their modules.
from Exscript.protocols.drivers import driver_map  # noqa: E402

_rows = ["   * - Name\n     - System\n"]
for _name, _driver in sorted(driver_map.items()):
    if _name != "unknown":  # an alias of generic
        _doc = sys.modules[type(_driver).__module__].__doc__.strip().splitlines()[0]
        _doc = _doc.removeprefix("A driver for ")
        _rows.append(f"   * - ``{_name}``\n     - {_doc[0].upper()}{_doc[1:]}\n")
Path("_generated/drivers.inc").write_text(
    ".. list-table::\n   :header-rows: 1\n\n" + "".join(_rows), encoding="utf-8"
)

project = "Exscript"
author = "Samuel Abels and contributors"
copyright = "2007-2026, Samuel Abels and contributors"
release = importlib.metadata.version("Exscript")
version = ".".join(release.split(".")[:2])

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "myst_parser",  # for the changelog, which is Markdown
]
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
exclude_patterns = ["_build"]

# The API reference is generated from the docstrings at build time.
autosummary_generate = True
autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
    # Document each class once, in the module that defines it, not again
    # where a package re-exports it (e.g. Exscript.Account).
    "ignore-module-all": True,
}
autodoc_member_order = "bysource"
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}

html_theme = "furo"
html_title = project  # the version is long between releases, e.g. 3.0.1.dev4+g1a2b3c4
html_logo = "_static/logo.png"
html_static_path = ["_static"]
