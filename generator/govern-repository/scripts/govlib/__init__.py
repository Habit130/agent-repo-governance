"""The generator's library: stored form, the template store, rendering and exact comparison.

Python 3's standard library at the 3.9 level only (ADR 0026).
"""


class GovernError(Exception):
    """A refusal the command line reports as JSON, with the reason."""
