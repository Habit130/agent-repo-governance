"""Governance model version five, the unpublished draft: rendered policy-text checks."""

from materialized_version_support import VersionThreeRendered, flat, level_three_section  # noqa: F401


class VersionFiveInitializeChecks(VersionThreeRendered):
    """#207: the checks an Initialize PR is judged by, in version 5's review.md."""

    VERSION = 5


class VersionFivePureRevert(VersionThreeRendered):
    """#206: the pure-revert rule in version 5's builder.md."""

    VERSION = 5
