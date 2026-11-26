"""The materialized-version suite: collect each model version's policy-text checks.

Released versions' checks stay in their version modules; draft changes belong in
its module. Shared rendering setup and checks live in materialized_version_support.
"""

import unittest

from test_materialized_version_one import (
    MaterializedVersionOne,
)
from test_materialized_version_two import (
    VersionTwoPolicy,
)
from test_materialized_version_three import (
    VersionThreeRerunPolicy,
    VersionThreeReviewProviders,
    VersionThreeReviewerStartAndReread,
    VersionThreeHandoffs,
)
from test_materialized_version_four import (
    VersionFourCodexSecurityReview,
    VersionFourDifficulty,
    VersionFourSkillInvocations,
    VersionFourBodyUpdateOrder,
    VersionFourSessionMarks,
    VersionFourReviewLadder,
    VersionFourRefresh,
    VersionFourPureUpgrade,
)
from test_materialized_version_five import (
    VersionFiveBuilderMergeWait,
    VersionFiveCodexPRWait,
    VersionFiveCopilotCompletion,
    VersionFiveInitializeChecks,
    VersionFivePureRevert,
)

from test_materialized_version_six import VersionSixPolicy


if __name__ == "__main__":
    unittest.main()
