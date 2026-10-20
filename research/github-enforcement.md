# GitHub enforcement and tracker features on personal Free and Pro accounts

## Question

From [issue #9](https://github.com/Habit130/agent-repo-governance/issues/9):

> Which GitHub enforcement and tracker features can a personal account use on its public and private repositories, on the Free and Pro plans?

## Method and source rules

- Primary sources only: `docs.github.com` and `github.blog/changelog`. No secondary sources were used.
- Every quoted passage below is a verbatim contiguous passage from the linked page. Access date for all pages: **2026-10-20**.
- "Personal account" here means repositories owned by a user account rather than an organization.
- "Not stated" means the cited page does not address that dimension; it is recorded under **Open gaps**, not treated as a denial.
- Changelog statements are dated; a changelog passage records what was announced on that date, not necessarily the current setting name.

## Findings

### 1. Repository rulesets versus classic branch protection

**Classic branch protection availability.** Protected branches are available in public repositories on GitHub Free, and in public and private repositories on GitHub Pro, GitHub Team, GitHub Enterprise Cloud, and GitHub Enterprise Server:

> Protected branches are available in public repositories with GitHub Free and GitHub Free for organizations. Protected branches are also available in public and private repositories with GitHub Pro, GitHub Team, GitHub Enterprise Cloud, and GitHub Enterprise Server.
> — [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

**Ruleset availability.** Rulesets are available in public repositories on GitHub Free, and in public and private repositories on GitHub Pro, GitHub Team, and GitHub Enterprise Cloud:

> Rulesets are available in public repositories with GitHub Free and GitHub Free for organizations, and in public and private repositories with GitHub Pro, GitHub Team, and GitHub Enterprise Cloud.
> — [About rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)

**What a ruleset is.** The page defines a ruleset as a named list of rules:

> A ruleset is a named list of rules that applies to a repository or to multiple repositories in an organization for customers on GitHub Team and GitHub Enterprise plans.
> — [About rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)

**Layering difference.** The branch-protection page states that only one classic rule applies to a branch, while rulesets do not have that restriction:

> Only a single branch protection rule can apply at a time, which means it can be difficult to know which rule will apply when multiple versions of a rule target the same branch.
> — [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

> This restriction does not apply to rulesets, see About rulesets.
> — [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

**Enforcement targets.** Rulesets can target branches or tags, and a separate push-ruleset type blocks pushes:

> You can use rulesets to target branches or tags in a repository or to block pushes to a repository and the repository's entire fork network.
> — [About rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)

**Documented availability.**

| Repository visibility | GitHub Free | GitHub Pro |
| --- | --- | --- |
| Public | Classic branch protection and rulesets | Classic branch protection and rulesets |
| Private | Not listed for GitHub Free (the quote names public repositories) | Classic branch protection and rulesets |

The availability quotes also name GitHub Team and GitHub Enterprise; this report covers only the personal GitHub Free and GitHub Pro plans.

### 2. Required status checks

**Classic branch protection.** Required checks accept three successful states, and can be checks or commit statuses:

> Required status checks must have a successful, skipped, or neutral status before collaborators can make changes to a protected branch. Required status checks can be checks or commit statuses.
> — [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

**Restricting the check source.** The page documents an option to accept a status only from a specific app:

> Any person or integration with write permissions to a repository can set the state of any status check in the repository, but in some cases you may only want to accept a status check from a specific GitHub App.
> — [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

**Ruleset equivalent.** A ruleset has a required-status-checks rule:

> Required status checks ensure that all required CI tests are passing before collaborators can make changes to a branch or tag targeted by your ruleset.
> — [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)

> Required status checks can be checks or statuses.
> — [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)

**Up-to-date branches.** The ruleset page's strict option states:

> The topic branch must be up to date with the base branch before merging.
> — [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)

**Documented availability.** The rule is part of branch protection or a ruleset; the pages state availability at the protection/ruleset level (section 1) and do not add a separate status-check availability statement.

### 3. Required pull request reviews, and the repository owner

**Classic requirement.** The number of required approvals is configurable, and approvers are people with write access or a designated code owner:

> Repository administrators or custom roles with the "edit repository rules" permission can require that all pull requests receive a specific number of approving reviews before someone merges the pull request into a protected branch. You can require approving reviews from people with write permissions in the repository or from a designated code owner.
> — [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

**Authors cannot approve their own pull requests.**

> Pull request authors cannot approve their own pull requests.
> — [Reviewing proposed changes in a pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/reviewing-proposed-changes-in-a-pull-request)

**Owners and administrators can merge without an approving review.**

> Repository owners and administrators can merge a pull request even if it hasn't received an approving review, or if a reviewer who requested changes has left the organization or is unavailable.
> — [Approving a pull request with required reviews](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/approving-a-pull-request-with-required-reviews)

**Required reviewers from teams.** A ruleset can require approval from named teams, but that specific rule is not available on user-owned repositories:

> Optionally, you can require review or approval from specific teams when a pull request changes certain files or directories.
> — [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)

> This rule is not available on user-owned repositories as they do not contain teams.
> — [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)

**Documented availability.** The requirement is part of branch protection or a ruleset, with the availability stated in section 1. The pages identify approvers as people with write permissions or code owners; they do not state whether an approval by a repository owner acting as administrator counts toward the required number, and they state separately that owners and administrators may merge without one.

### 4. Dismissing approvals on new commits

**Classic setting.** The option dismisses approvals when pushed commits change the diff:

> Optionally, you can choose to dismiss stale pull request approvals when commits are pushed that affect the diff in the pull request.
> — [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

**Effect on the approval state.**

> If the diff changes from this state (for example, because a contributor pushes new changes to the pull request branch or clicks Update branch, or because a related pull request is merged into the target branch), the approving review is dismissed as stale, and the pull request cannot be merged until someone approves the work again.
> — [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

**Ruleset equivalent.** The ruleset page lists the same option as an additional setting of the require-a-pull-request rule:

> Optionally, you can choose to dismiss stale pull request approvals when commits are pushed that affect the diff in the pull request.
> — [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)

**Documented availability.** Part of branch protection or a ruleset; availability follows section 1.

### 5. Merge queue

**The availability sentence names organization-owned repositories.**

> Pull request merge queues are available in any public repository owned by an organization, or in private repositories owned by organizations using GitHub Enterprise Cloud.
> — [Managing a merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)

**Purpose.**

> A merge queue helps increase velocity by automating pull request merges into a busy branch and ensuring the branch is never broken by incompatible changes.
> — [Managing a merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)

**Documented availability.** Public repositories owned by an organization; private repositories owned by organizations on GitHub Enterprise Cloud. The page does not state availability for repositories owned by a personal account.

### 6. Auto-merge

**Availability.**

> Auto-merge for pull requests is available in public repositories with GitHub Free and GitHub Free for organizations, and in public and private repositories with GitHub Pro, GitHub Team, GitHub Enterprise Cloud, and GitHub Enterprise Server.
> — [Automatically merging a pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/automatically-merging-a-pull-request)

**Behavior.**

> Auto-merge merges a pull request automatically after all required reviews and status checks pass.
> — [Automatically merging a pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/automatically-merging-a-pull-request)

**Repository prerequisite.**

> Before you use auto-merge, it must be enabled for the repository.
> — [Automatically merging a pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/automatically-merging-a-pull-request)

**Documented availability.** Public repositories on GitHub Free; public and private repositories on GitHub Pro, Team, Enterprise Cloud and Enterprise Server.

### 7. CODEOWNERS enforcement

**Availability.**

> You can define code owners in public repositories with GitHub Free and GitHub Free for organizations, and in public and private repositories with GitHub Pro, GitHub Team, GitHub Enterprise Cloud, and GitHub Enterprise Server.
> — [About code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)

**File locations.**

> To use a CODEOWNERS file, create a new file called CODEOWNERS in the .github/, root, or docs/ directory of the repository, in the branch where you'd like to add the code owners.
> — [About code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)

**Enforcement.** Required code-owner review is an option of required reviews:

> When someone with admin or owner permissions has enabled required reviews, they also can optionally require approval from a code owner before the author can merge a pull request in the repository.
> — [About code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)

> When reviews from code owners are required, an approval from any of the owners is sufficient to meet this requirement.
> — [About code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)

**Documented availability.** Public repositories on GitHub Free; public and private repositories on GitHub Pro, Team, Enterprise Cloud and Enterprise Server. The enforcement depends on the required-reviews setting, whose availability is stated in section 1.

### 8. Allowed merge methods

**Configuration.**

> You can allow contributors with push access to your repository to merge their pull requests with different merge options or enforce a specific merge method for all of your repository's pull requests.
> — [About merge methods on GitHub](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/about-merge-methods-on-github)

> You can enforce one type of merge method, such as commit squashing or rebasing, by only enabling the desired method for your repository.
> — [About merge methods on GitHub](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/about-merge-methods-on-github)

**Repository setting.** The merge-commit configuration page describes the setting and its interaction with required linear history:

> If you select more than one merge method, collaborators can choose which type of merge commit to use when they merge a pull request. If there is a protected branch rule in your repository that requires a linear commit history, you must allow squash merging, rebase merging, or both.
> — [Configuring commit merging for pull requests](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/configuring-commit-merging-for-pull-requests)

**Documented availability.** None of the cited merge-method pages state a plan or repository-visibility restriction. This is recorded as a gap, not as availability.

### 9. Deleting head branches on merge

**Behavior.**

> You can have head branches automatically deleted after pull requests are merged in your repository.
> — [Managing the automatic deletion of branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-the-automatic-deletion-of-branches)

**Who can enable it.**

> Anyone with admin permissions to a repository can enable or disable the automatic deletion of branches. Branch protection rules and repository rules can also prevent branches being automatically deleted.
> — [Managing the automatic deletion of branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-the-automatic-deletion-of-branches)

**Fork behavior.**

> For a pull request opened from a fork, GitHub uses the Automatically delete head branches setting on the head repository (the fork), not the base repository where the pull request is merged.
> — [Managing the automatic deletion of branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-the-automatic-deletion-of-branches)

**Documented availability.** The page does not state a plan or repository-visibility restriction. This is recorded as a gap.

### 10. Push rulesets

**Documented plan and visibility.** The ruleset availability box names the GitHub Team plan for internal and private repositories:

> Push rulesets are available for the GitHub Team plan in internal and private repositories, and forks of repositories that have push rulesets enabled.
> — [About rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)

**Scope.**

> You can also create push rulesets to block pushes to a private or internal repository and the repository's entire fork network. Push rulesets allow you to block pushes based on file extensions, file path lengths, file and folder paths, and file sizes.
> — [Creating rulesets for a repository](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository)

**General availability announcement (2024-09-10).**

> You can now restrict pushes into your private and internal repositories and their forks, with push rules - a new type of ruleset.
> — [GitHub Changelog, September 10, 2024](https://github.blog/changelog/2024-09-10-push-rules-are-now-generally-available-and-updates-to-custom-properties/)

**Documented availability.** The docs name the GitHub Team plan for internal and private repositories and do not state availability for personal-account Free or Pro repositories. This is recorded as a gap.

### 11. Bypass actors

**Rulesets.** Bypass is an explicit list, and the page enumerates eligible actors:

> When you create a ruleset, you can allow certain users to bypass the rules in the ruleset.
> — [Creating rulesets for a repository](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository)

> You can grant certain roles, teams, or apps bypass permissions for your ruleset.
> — [Creating rulesets for a repository](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository)

The same page lists the eligible actors as repository admins, organization owners, enterprise owners, the maintain or write role (including custom roles based on write), teams excluding secret teams, GitHub Apps, and Dependabot. The list is introduced by this sentence:

> The following are eligible for bypass access: Repository admins, organization owners, and enterprise owners
> — [Creating rulesets for a repository](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository)

**Classic branch protection.** Actor bypass lists are organization-only, while repository administrators are exempt from the rule by default:

> Actors may only be added to bypass lists when the repository belongs to an organization.
> — [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

> By default, the restrictions of a branch protection rule don't apply to people with admin permissions to the repository or custom roles with the "bypass branch protections" permission.
> — [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

> You can optionally apply the restrictions to administrators and roles with the "bypass branch protections" permission, too.
> — [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

**Documented availability.** Ruleset bypass eligibility includes repository admins on the cited page; the page does not limit that role to organization-owned repositories. Classic branch protection bypass *lists* are organization-only, and admins are exempt by default. Neither page states a Free/Pro restriction for the bypass role list.

### 12. `GITHUB_TOKEN` in Actions

**Token identity and scope.**

> The GITHUB_TOKEN secret is a GitHub App installation access token. You can use the installation access token to authenticate on behalf of the GitHub App installed on your repository. The token's permissions are limited to the repository that contains your workflow.
> — [GITHUB_TOKEN](https://docs.github.com/en/actions/concepts/security/github_token)

**Changing permissions.** The workflow syntax documents the `permissions` key:

> You can define the access that the GITHUB_TOKEN will permit by specifying read, write, or none as the value of the available permissions within the permissions key.
> — [Workflow syntax for GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)

**Default for a new personal repository: no creating or approving pull requests.**

> By default, when you create a new repository in your personal account, workflows are not allowed to create or approve pull requests.
> — [Managing GitHub Actions settings for a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository)

> use the Allow GitHub Actions to create and approve pull requests setting to configure whether GITHUB_TOKEN can create and approve pull requests.
> — [Managing GitHub Actions settings for a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository)

**Permission rows in the workflow-syntax table.** The table maps each scope to a documented example:

> issues Work with issues. For example, issues: write permits an action to add a comment to an issue.
> — [Workflow syntax for GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)

> pull-requests Work with pull requests. For example, pull-requests: write permits an action to add a label to a pull request.
> — [Workflow syntax for GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)

> statuses Work with commit statuses. For example, statuses:read permits an action to list the commit statuses for a given reference.
> — [Workflow syntax for GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)

> checks Work with check runs and check suites. For example, checks: write permits an action to create a check run.
> — [Workflow syntax for GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)

> contents Work with the contents of the repository. For example, contents: read permits an action to list the commits, and contents: write allows the action to create a release.
> — [Workflow syntax for GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)

**Approving or requesting changes.** Submitting a review requires a write permission on pull requests and accepts an action value:

> The fine-grained token must have the following permission set: "Pull requests" repository permissions (write)
> — [REST API endpoints for pull request reviews](https://docs.github.com/en/rest/pulls/reviews)

> The review actions include: APPROVE, REQUEST_CHANGES, or COMMENT.
> — [REST API endpoints for pull request reviews](https://docs.github.com/en/rest/pulls/reviews)

**Merging.** Merging through the REST API requires write access to repository contents:

> The fine-grained token must have the following permission set: "Contents" repository permissions (write)
> — [REST API endpoints for pull requests](https://docs.github.com/en/rest/pulls/pulls)

**Documented availability.** The token's permissions are repository-scoped; the create/approve gate is a repository Actions setting, and the cited page gives the default for a new personal repository as "not allowed". The pages do not state a Free/Pro restriction for the token itself.

### 13. GitHub Apps in Actions

**Installation tokens are accepted by the review and merge endpoints.**

> This endpoint works with the following fine-grained token types: GitHub App user access tokens GitHub App installation access tokens
> — [REST API endpoints for pull request reviews](https://docs.github.com/en/rest/pulls/reviews)

> This endpoint works with the following fine-grained token types: GitHub App user access tokens GitHub App installation access tokens
> — [REST API endpoints for pull requests](https://docs.github.com/en/rest/pulls/pulls)

**Permissions.** The GitHub App [permission reference](https://docs.github.com/en/rest/authentication/permissions-required-for-github-apps) has repository-permission sections for Pull requests, Checks, Commit statuses, and Issues, and the review endpoint requires "Pull requests" (write) while the merge endpoint requires "Contents" (write):

> This endpoint works with the following fine-grained token types: GitHub App user access tokens GitHub App installation access tokens Fine-grained personal access tokens The fine-grained token must have the following permission set: "Pull requests" repository permissions (write)
> — [REST API endpoints for pull request reviews](https://docs.github.com/en/rest/pulls/reviews)

**Checks write access.** The check-runs page limits write access to GitHub Apps:

> Note Write permission for the REST API to interact with checks is only available to GitHub Apps. OAuth apps and authenticated users can view check runs and check suites, but they are not able to create them.
> — [REST API endpoints for check runs](https://docs.github.com/en/rest/checks/runs)

> To create a check run, you must use a GitHub App.
> — [REST API endpoints for check runs](https://docs.github.com/en/rest/checks/runs)

**Bypass eligibility.** GitHub Apps are listed as eligible for ruleset bypass:

> You can grant certain roles, teams, or apps bypass permissions for your ruleset.
> — [Creating rulesets for a repository](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository)

**Documented availability.** The cited API pages accept installation tokens; they do not state a plan or repository-visibility restriction for app installations. Checks write access is limited to GitHub Apps on the cited page.

### 14. Whether an Actions approval counts toward required reviews

**January 2022 changelog.** The announcement describes a policy setting for Actions approvals:

> We have introduced a new policy setting that controls whether GitHub Actions can approve pull requests.
> — [GitHub Changelog, January 14, 2022](https://github.blog/changelog/2022-01-14-github-actions-prevent-github-actions-from-approving-pull-requests/)

> This protects against a user using Actions to satisfy the "Required approvals" branch protection requirement and merging a change that was not reviewed by another user.
> — [GitHub Changelog, January 14, 2022](https://github.blog/changelog/2022-01-14-github-actions-prevent-github-actions-from-approving-pull-requests/)

> Allow GitHub Actions reviews to count towards required approval is enabled by default.
> — [GitHub Changelog, January 14, 2022](https://github.blog/changelog/2022-01-14-github-actions-prevent-github-actions-from-approving-pull-requests/)

> However, an organization admin can disable it under the organization's Actions settings.
> — [GitHub Changelog, January 14, 2022](https://github.blog/changelog/2022-01-14-github-actions-prevent-github-actions-from-approving-pull-requests/)

**May 2022 changelog.** The later announcement says the setting was extended from approving to creating:

> the organization setting to disallow Actions from approving pull requests, which was introduced in January 2022, has been extended to also limit Actions from creating pull requests.
> — [GitHub Changelog, May 3, 2022](https://github.blog/changelog/2022-05-03-github-actions-prevent-github-actions-from-creating-and-approving-pull-requests/)

**Current documentation.** The current settings page uses the combined create/approve setting and does not state whether an approval counts toward required reviews; the default for a new personal repository is "not allowed" (quoted in section 12).

**Documented availability.** The January 2022 page says reviews counted toward required approval by default under the then-current setting and that an organization admin could disable it. The current page states the combined setting and the personal-repository default but omits the counting statement.

### 15. Actions minutes and limits

**Public repositories use standard runners for free.**

> GitHub Actions usage is free for self-hosted runners and for public repositories that use standard GitHub-hosted runners.
> — [About billing for GitHub Actions](https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions)

**Included quota on private repositories.** The page's table lists:

| Plan | Artifact storage | Minutes per month | Cache storage (per repository) |
| --- | --- | --- | --- |
| GitHub Free | 500 MB | 2,000 | 10 GB |
| GitHub Pro | 1 GB | 3,000 | 10 GB |

> At the start of each month, the minutes used by the account are reset to zero.
> — [About billing for GitHub Actions](https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions)

> Any usage beyond the included amounts is billed to your account.
> — [About billing for GitHub Actions](https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions)

**Operating-system cost.** The billing page states that Windows and macOS jobs cost more than Linux jobs:

> For example, jobs that run on Windows and macOS runners hosted by GitHub cost more to run than jobs on Linux runners.
> — [About billing for GitHub Actions](https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions)

The same page's "Baseline minute costs" table lists these per-minute rates (USD):

| Runner | Per-minute rate (USD) |
| --- | --- |
| Linux 1-core (x64) | 0.002 |
| Linux 2-core (x64) | 0.006 |
| Linux 2-core (arm64) | 0.005 |
| Windows 2-core (x64) | 0.010 |
| Windows 2-core (arm64) | 0.010 |
| macOS 3-core or 4-core (M1 or Intel) | 0.062 |

**Execution limits.**

> Each job in a workflow can run for up to 6 hours of execution time. If a job reaches this limit, the job is terminated and fails.
> — [Actions limits](https://docs.github.com/en/actions/reference/limits)

> If a workflow run reaches this limit, the workflow run is cancelled.
> — [Actions limits](https://docs.github.com/en/actions/reference/limits)

The page's system-limits table lists a workflow run time of 35 days per workflow run, a gate approval time of 30 days, and a job matrix maximum of 256 jobs per workflow run:

> A workflow may wait for up to 30 days on environment approvals.
> — [Actions limits](https://docs.github.com/en/actions/reference/limits)

> A job matrix can generate a maximum of 256 jobs per workflow run.
> — [Actions limits](https://docs.github.com/en/actions/reference/limits)

> A workflow file larger than 500 KB will not start runs.
> — [Actions limits](https://docs.github.com/en/actions/reference/limits)

**Documented availability.** Public repositories: free for standard GitHub-hosted runners. Private repositories: included quota per plan (2,000 minutes on Free, 3,000 on Pro), with usage beyond the quota billed.

### 16. Environments and secrets

**Environment availability.**

> Environments, environment secrets, and deployment protection rules are available in public repositories for all current GitHub plans.
> — [Managing environments for deployment](https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment)

> For access to environments, environment secrets, and deployment branches in private or internal repositories, you must use GitHub Pro, GitHub Team, or GitHub Enterprise.
> — [Managing environments for deployment](https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment)

**Free on private.** The page adds a note and a creation note:

> Users with GitHub Free plans can only configure environments for public repositories.
> — [Managing environments for deployment](https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment)

> Creation of an environment in a private repository is available to organizations with GitHub Team and users with GitHub Pro.
> — [Managing environments for deployment](https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment)

**Protection rules on Free, Pro and Team.** Wait timers and required reviewers are public-repository-only on these plans:

> If you are on a GitHub Free, GitHub Pro, or GitHub Team plan, other deployment protection rules, such as a wait timer or required reviewers, are only available for public repositories.
> — [Managing environments for deployment](https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment)

**Environment secrets.** Access is gated by the environment's rules:

> These secrets are only available to workflow jobs that use the environment.
> — [Managing environments for deployment](https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment)

> Additionally, workflow jobs that use this environment can only access these secrets after any configured rules (for example, required reviewers) pass.
> — [Managing environments for deployment](https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment)

**Secrets generally.** Repository, organization and environment secrets are defined as follows:

> Secrets allow you to store sensitive information in your organization, repository, or repository environments.
> — [About secrets](https://docs.github.com/en/actions/concepts/security/secrets)

**Documented availability.** Environments and environment secrets: public repositories on all current plans; private repositories require GitHub Pro, GitHub Team, or GitHub Enterprise. On Free, Pro, and Team, wait timers and required reviewers are public-repository-only; private-repository environment creation is available to GitHub Pro users and Team organizations. The secrets page does not state a separate plan restriction for repository secrets.

### 17. Issue dependencies (blocked by)

**Definition.**

> Issue dependencies let you define issues that are blocked by, or blocking, other work.
> — [Creating issue dependencies](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-issue-dependencies)

**Availability.**

> Issue dependencies are available for users on GitHub Free, GitHub Pro, GitHub Team, and GitHub Enterprise Cloud plans.
> — [Creating issue dependencies](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-issue-dependencies)

**API.**

> Use the REST API to view, add, and remove issue dependencies.
> — [REST API endpoints for issue dependencies](https://docs.github.com/en/rest/issues/issue-dependencies)

The page documents these endpoints (REST API version 2026-03-10):

| Operation | Method and path |
| --- | --- |
| List dependencies an issue is blocked by | `GET /repos/{owner}/{repo}/issues/{issue_number}/dependencies/blocked_by` |
| Add a dependency an issue is blocked by | `POST /repos/{owner}/{repo}/issues/{issue_number}/dependencies/blocked_by` |
| Remove dependency an issue is blocked by | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/dependencies/blocked_by/{issue_id}` |
| List dependencies an issue is blocking | `GET /repos/{owner}/{repo}/issues/{issue_number}/dependencies/blocking` |

**Documented availability.** GitHub Free, GitHub Pro, GitHub Team, and GitHub Enterprise Cloud. The page does not state a repository-visibility restriction.

### 18. Sub-issues

**Definition.**

> You can add sub-issues to an issue to break down larger pieces of work into tasks.
> — [Adding sub-issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/adding-sub-issues)

**Permission.**

> People with at least triage permissions for a repository can add sub-issues.
> — [Adding sub-issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/adding-sub-issues)

**General availability (April 2025).**

> we're thrilled to announce the general availability of sub-issues, issue types, advanced search, and increased item limits in GitHub Projects
> — [GitHub Changelog, April 9, 2025](https://github.blog/changelog/2025-04-08-evolving-github-issues-and-projects/)

**API.**

> Use the REST API to view, add, remove, and reprioritize sub-issues.
> — [REST API endpoints for sub-issues](https://docs.github.com/en/rest/issues/sub-issues)

The page documents these endpoints (REST API version 2026-03-10):

| Operation | Method and path |
| --- | --- |
| Get parent issue | `GET /repos/{owner}/{repo}/issues/{issue_number}/parent` |
| List sub-issues | `GET /repos/{owner}/{repo}/issues/{issue_number}/sub_issues` |
| Add sub-issue | `POST /repos/{owner}/{repo}/issues/{issue_number}/sub_issues` |
| Remove sub-issue | `DELETE /repos/{owner}/{repo}/issues/{issue_number}/sub_issue` |
| Reprioritize sub-issue | `PATCH /repos/{owner}/{repo}/issues/{issue_number}/sub_issues/priority` |

**Documented availability.** The adding-sub-issues page states a triage-permission requirement and does not state a plan or repository-visibility restriction. The changelog announces general availability without a plan list. This is recorded as a gap.

## Availability summary

The table restates the availability statements quoted above. "Not stated" means the cited pages do not address that cell; those cases are listed in **Open gaps**.

| Feature | Public repositories | Private repositories | Evidence |
| --- | --- | --- | --- |
| Classic branch protection | GitHub Free | GitHub Pro, Team, Enterprise Cloud/Server | [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) |
| Repository rulesets (branch/tag) | GitHub Free | GitHub Pro, Team, Enterprise Cloud | [About rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets) |
| Push rulesets | Not stated for personal repositories; docs name GitHub Team | Not stated for personal repositories; docs name GitHub Team for internal/private | [About rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets) |
| Required status checks | Follows protection/ruleset | Follows protection/ruleset | [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) |
| Required PR reviews | Follows protection/ruleset | Follows protection/ruleset | [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) |
| Dismiss stale approvals | Follows protection/ruleset | Follows protection/ruleset | [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) |
| Merge queue | Organization-owned public repositories | Organization-owned private repositories on Enterprise Cloud | [Managing a merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue) |
| Auto-merge | GitHub Free | GitHub Pro, Team, Enterprise Cloud/Server | [Automatically merging a pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/automatically-merging-a-pull-request) |
| CODEOWNERS required reviews | GitHub Free | GitHub Pro, Team, Enterprise Cloud/Server | [About code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners) |
| Allowed merge methods | Not stated | Not stated | [About merge methods](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/about-merge-methods-on-github) |
| Delete head branches on merge | Not stated | Not stated | [Automatic branch deletion](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-the-automatic-deletion-of-branches) |
| Ruleset bypass actors | Repository admins, org/enterprise owners, maintain/write roles, teams, apps, Dependabot | Same listed roles | [Creating rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository) |
| Classic branch-protection bypass lists | Organization-owned repositories only | Organization-owned repositories only | [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) |
| `GITHUB_TOKEN` create/approve PR | Default: not allowed on new personal repositories; repository setting controls it | Default: not allowed on new personal repositories; repository setting controls it | [Actions settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository) |
| Actions minutes | Free for standard GitHub-hosted runners | 2,000/month on Free; 3,000/month on Pro | [Actions billing](https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions) |
| Environments | All current plans | GitHub Pro, Team, Enterprise for access | [Environments](https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment) |
| Environment protection rules (wait timer, required reviewers) | GitHub Free, Pro, Team | Not available on Free, Pro, Team | [Environments](https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment) |
| Issue dependencies | GitHub Free, Pro, Team, Enterprise Cloud | Same plans; no visibility statement | [Issue dependencies](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-issue-dependencies) |
| Sub-issues | Triage permission; no plan/visibility statement | Triage permission; no plan/visibility statement | [Adding sub-issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/adding-sub-issues) |

## Open gaps

These are dimensions the Cover asks about that the cited primary pages do not resolve. They are recorded without conclusions.

1. **Push rulesets on personal Free/Pro repositories.** The ruleset availability box names the GitHub Team plan for internal and private repositories; no cited page states availability for user-owned Free or Pro repositories.
2. **Merge queue on personal-owned repositories.** The merge-queue page's availability sentence names repositories owned by an organization; it does not mention user-owned repositories.
3. **Whether an owner/administrator approval counts toward a required review.** The pages state that approvers are people with write permissions or code owners, that authors cannot approve their own pull requests, and that owners/administrators can merge without an approving review. They do not state whether an owner's approval is counted when the owner is not the author.
4. **Whether a `GITHUB_TOKEN` approval counts toward required reviews under the current setting.** The current settings page documents the create/approve gate but not the counting behavior; the January 2022 changelog documents counting under a then-current organization setting.
5. **Whether a GitHub App approval counts toward required reviews.** The API pages accept installation tokens for reviews, but no cited page states whether such a review satisfies required approvals.
6. **Sub-issues plan or repository-visibility limits.** The docs page states a triage-permission requirement; the GA changelog does not list plans; neither states a visibility limit.
7. **Allowed merge methods and automatic head-branch deletion plan limits.** The cited pages describe the settings but state no plan or visibility restriction.
8. **Pull-request conversation comments by `GITHUB_TOKEN`.** The workflow-syntax permission table gives an issue-comment example for `issues: write` and a label example for `pull-requests: write`; no quoted page states a pull-request conversation-comment capability.
9. **Repository secrets plan limits.** The secrets pages describe repository, organization and environment secrets; only environments and environment secrets carry explicit plan/visibility statements.
10. **Actions per-plan minute rates.** The billing page lists per-minute rates by runner SKU and included minutes by plan, but does not state different rates for Free versus Pro.

## Sources

All sources are primary (`docs.github.com` or `github.blog/changelog`). Accessed 2026-10-20.

### GitHub Docs

- About protected branches — https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- About rulesets — https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets
- Available rules for rulesets — https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets
- Creating rulesets for a repository — https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository
- Managing a merge queue — https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue
- Automatically merging a pull request — https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/automatically-merging-a-pull-request
- About code owners — https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
- About merge methods on GitHub — https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/about-merge-methods-on-github
- Configuring commit merging for pull requests — https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/configuring-commit-merging-for-pull-requests
- Managing the automatic deletion of branches — https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-the-automatic-deletion-of-branches
- Approving a pull request with required reviews — https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/approving-a-pull-request-with-required-reviews
- Reviewing proposed changes in a pull request — https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/reviewing-proposed-changes-in-a-pull-request
- Managing GitHub Actions settings for a repository — https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository
- GITHUB_TOKEN — https://docs.github.com/en/actions/concepts/security/github_token
- Workflow syntax for GitHub Actions — https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- REST API endpoints for pull requests — https://docs.github.com/en/rest/pulls/pulls
- REST API endpoints for pull request reviews — https://docs.github.com/en/rest/pulls/reviews
- REST API endpoints for check runs — https://docs.github.com/en/rest/checks/runs
- Permissions required for GitHub Apps — https://docs.github.com/en/rest/authentication/permissions-required-for-github-apps
- About billing for GitHub Actions — https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions
- Actions limits — https://docs.github.com/en/actions/reference/limits
- Managing environments for deployment — https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment
- Using secrets in GitHub Actions — https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions
- About secrets — https://docs.github.com/en/actions/concepts/security/secrets
- Creating issue dependencies — https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-issue-dependencies
- REST API endpoints for issue dependencies — https://docs.github.com/en/rest/issues/issue-dependencies
- Adding sub-issues — https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/adding-sub-issues
- REST API endpoints for sub-issues — https://docs.github.com/en/rest/issues/sub-issues

### GitHub Changelog

- GitHub Actions: Prevent GitHub Actions from approving pull requests (2022-01-14) — https://github.blog/changelog/2022-01-14-github-actions-prevent-github-actions-from-approving-pull-requests/
- GitHub Actions: Prevent GitHub Actions from creating and approving pull requests (2022-05-03) — https://github.blog/changelog/2022-05-03-github-actions-prevent-github-actions-from-creating-and-approving-pull-requests/
- Push Rules are now generally available, and updates to custom properties (2024-09-10) — https://github.blog/changelog/2024-09-10-push-rules-are-now-generally-available-and-updates-to-custom-properties/
- Evolving GitHub Issues and Projects (published April 9, 2025) — https://github.blog/changelog/2025-04-08-evolving-github-issues-and-projects/
