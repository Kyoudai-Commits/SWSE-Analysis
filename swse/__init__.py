"""SWSE character-option analysis workspace.

Public entry points
-------------------
:mod:`swse.cli`        command line interface (``python -m swse.cli --help``)
:mod:`swse.store`      load canonical entities
:mod:`swse.graph`      prerequisite graph
:mod:`swse.space`      the character-creation decision space
:mod:`swse.enumerate`  build enumeration / sampling
:mod:`swse.evaluate`   build scoring

See ``AGENTS.md`` at the repo root before changing anything.
"""

__version__ = "0.1.0"

#: Canonicality tiers, best-first. Used to resolve cross-source field conflicts.
CANON_PRIORITY = ("official", "third_party", "homebrew")
