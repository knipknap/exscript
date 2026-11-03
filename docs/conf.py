"""
Sphinx configuration for the Exscript documentation.

Build it from the repository root::

    uv run --group docs sphinx-build -W --keep-going docs docs/_build/html
"""

import importlib.metadata

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
