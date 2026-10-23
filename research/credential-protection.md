# Credential protection in a personal account: secret scanning, push protection and what a write collaborator can see

## Question

From [ticket #37](https://github.com/Habit130/agent-repo-governance/issues/37):

> Which GitHub features stop an agent from committing a credential, or from exposing one in a pull request, issue or comment, in repositories of habit's personal account? And can the owner script turn them on?

Ticket context:

> Governance guards only against mistakes by rule-following agents, per [Which GitHub identity agents act under](https://github.com/Habit130/agent-repo-governance/issues/18). The plausible mistakes here are an agent committing a token or key in a file, or pasting one into a PR body, a comment or a log. Writes to Actions secrets are already guarded at machine level, per [Which rules are enforced deterministically](https://github.com/Habit130/agent-repo-governance/issues/15) and [How Codex joins the governance model](https://github.com/Habit130/agent-repo-governance/issues/24).

## Method and source rules

- Primary sources only: `docs.github.com`, `github.blog/changelog`, and live read-only GitHub API responses.
- Access date for every source: **2026-10-22**. Docs pages were read in the `free-pro-team@latest` (Free, Pro, & Team) version.
- Every quoted passage is a verbatim contiguous passage from the linked page, with ellipses marking an elision, unless marked otherwise. Where a table cell is quoted, the cell text is reproduced and the column it belongs to is named.
- "Documented" = stated by a cited page. "Observed" = a live read-only response recorded under **Live checks**. "Not stated" = the cited pages do not address the point; it is listed under **Open gaps** and is not treated as a denial.
- No non-GET API calls were made: no PATCH/POST/PUT/DELETE, no enabling, no test secrets, no comments or pushes. No credential file was read. Token values are not reproduced.
- Availability statements are quoted from the pages' prose access sections and from the availability table on [About GitHub Advanced Security](https://docs.github.com/en/get-started/learning-about-github/about-github-advanced-security), whose cells carry `aria-label="Yes"`/`"No"` in the raw HTML. Some pages also carry a rendered "Who can use this feature?" box; where they do, it is quoted as such. The secret scanning page instead uses a prose section, "How can I access this feature?"
- Two docs pages conflict on whether repository-level push protection requires the paid product; the conflict is reported in Finding 2 and Open gaps 3 rather than resolved.
- Docs URLs were resolved live: `code-security/secret-scanning/introduction/*` redirects to `code-security/concepts/secret-security/*`. The canonical URLs fetched are the ones cited.

## Findings

### 1. Availability on a personal account: public is free, private is not available at all

**Secret scanning, by repository type (documented).** The page's access section says:

> Secret scanning is available for the following repository types:
> - Public repositories: Secret scanning runs automatically for free.
> - Organization-owned private and internal repositories: Available with GitHub Secret Protection enabled on GitHub Team or GitHub Enterprise Cloud.
> - User-owned repositories: Available on GitHub Enterprise Cloud with Enterprise Managed Users. Available on GitHub Enterprise Server when the enterprise has GitHub Secret Protection enabled.
> — [Secret scanning](https://docs.github.com/en/code-security/concepts/secret-security/secret-scanning)

The "user-owned repositories" line is the one that governs habit's private repositories. It names GitHub Enterprise Cloud with Enterprise Managed Users and GitHub Enterprise Server only; it does not name GitHub Pro, and it does not name GitHub Free or Team for user-owned private repositories.

**The two free-for-public features (documented).** The same page lists both under "Available with GitHub Secret Protection" but marks each as free for public repositories:

> Secret scanning alerts for users
> Automatically detect hardcoded credentials that have been checked into a repository. … Available for public repositories by default.

> Push protection
> Push protection proactively scans your code, and any repository contributors' code, for hardcoded secrets during the push process and blocks the push if any credential leaks are detected. If a contributor bypasses the block, an alert is generated. … Available for public repositories by default.
> — [GitHub security features](https://docs.github.com/en/code-security/getting-started/github-security-features)

The same page opens by scoping the paid product to organizations:

> Additional features are available to organizations on GitHub Team and GitHub Enterprise Cloud that purchase a GitHub Advanced Security product:
> — [GitHub security features](https://docs.github.com/en/code-security/getting-started/github-security-features)

**The availability table (documented, parsed from raw HTML).** The Secret Protection table on the GitHub Advanced Security page has these columns and cells:

| Feature | Public repository without GitHub Secret Protection | Private repository without GitHub Secret Protection | Public or private repository with GitHub Secret Protection |
| --- | --- | --- | --- |
| Secret scanning | Yes | No | Yes |
| Push protection | Yes | No | Yes |
| AI-detected secrets | No | No | Yes |
| Custom patterns | No | No | Yes |
| Delegated bypass for push protection | No | No | Yes |
| Security campaigns | No | No | Yes |
| Security overview | No | No | Yes |

— [About GitHub Advanced Security](https://docs.github.com/en/get-started/learning-about-github/about-github-advanced-security)

**A personal account cannot buy the paid product (documented).**

> You must be on a GitHub Team or GitHub Enterprise plan in order to purchase GitHub Code Security or GitHub Secret Protection.
> — [About GitHub Advanced Security](https://docs.github.com/en/get-started/learning-about-github/about-github-advanced-security)

The plans page agrees by omission and inclusion. The GitHub Pro section is introduced by this sentence, and the bulleted feature list that follows it contains no Advanced Security or secret scanning item (email support, Actions minutes, Packages storage, Codespaces hours and storage, "Advanced tools and insights in private repositories" for reviewers/branches/code owners/Pages/wikis/insights):

> In addition to the features available with GitHub Free for personal accounts, GitHub Pro includes:
> — [GitHub's plans](https://docs.github.com/en/get-started/learning-about-github/githubs-plans)

The GitHub Team list is the one that carries the purchase option; its bulleted list names GitHub Code Security and GitHub Secret Protection:

> The option to purchase GitHub Advanced Security products:
> — [GitHub's plans](https://docs.github.com/en/get-started/learning-about-github/githubs-plans)

**Answer to "does Pro cover private repositories?".** No, by three independent documented statements: user-owned private repositories need GitHub Enterprise Cloud with Enterprise Managed Users (or GHES), Secret Protection can only be purchased on Team or Enterprise, and Pro's documented feature list contains no secret scanning or push protection item. On a personal account, a private repository therefore has neither feature regardless of Pro; the paid product is not purchasable by a personal account at all.

**What Education provides (documented).** The student benefits page lists two GitHub benefits and no plan upgrade or secret protection:

> GitHub Copilot: Verified students get free access to Copilot and its premium features.

> GitHub Codespaces: Verified students get free use of GitHub Codespaces, up to 180 core hours per month, for their personal accounts. The monthly amount of storage and core hours of usage available to students is equivalent to the amount included with GitHub Pro accounts.
> — [About GitHub Education for students](https://docs.github.com/en/education/about-github-education/github-education-for-students/about-github-education-for-students)

The only mention of "GitHub Pro" on that page is the Codespaces-equivalence sentence. The ticket's premise that Habit130 "gets Pro through GitHub Education from about 2026-10-25" is **not stated** by this page, and no Education page found in this pass states a Pro entitlement. Even if Pro is granted, Finding 1's plan citations show Pro carries no secret scanning or push protection for private repositories, and Secret Protection cannot be purchased on a personal account.

**Related features on a personal account (documented).**

- Secret scanning alerts for partners run free on public repositories (list above, "Secret scanning alerts for partners").
- Custom patterns require Secret Protection and are marked No for a public repository without it (table above).
- Delegated bypass for push protection requires Secret Protection and is marked No for a public repository without it (table above).
- AI-detected secrets require Secret Protection and are marked No for a public repository without it (table above).
- Security overview is organization-scoped:

> Security overview provides insights into the security of code stored in repositories in your organization.
> — [Security overview](https://docs.github.com/en/code-security/concepts/security-at-scale/security-overview)

- Validity checks are documented under the repository's Secret Protection settings, with a REST note:

> Under "Secret Protection", to the right of "Validity checks", click Enable.
> …
> You can also use the REST API to enable validity checks for partner patterns for your repository.
> — [Enabling validity checks](https://docs.github.com/en/code-security/how-tos/secure-your-secrets/customize-leak-detection/enable-validity-checks)

  The Secret Protection availability table does not contain a validity-checks row, so its availability on a public repository without Secret Protection is **not stated**; the enablement instructions place it under Secret Protection.

### 2. Defaults: what is on with no setting

**New public repository owned by a personal account (documented, dated changelog).**

> All new public repositories owned by personal accounts will now have secret scanning and push protection enabled by default. Pushes to the repository that include known secrets will be blocked by push protection, and any known secrets that are detected in the repository will generate a secret scanning alert. Secret scanning and push protection can be disabled by the repository administrator after the repository is created.

> Existing public repositories are not affected, nor are new public repositories that belong to an organization.
> — [GitHub Changelog, March 11, 2024](https://github.blog/changelog/2024-03-11-secret-scanning-and-push-protection-are-enabled-by-default-on-new-public-repositories)

This is the only page found that separates new from existing repositories for these two features. Consequences that follow directly from its text:

| Repository | Secret scanning | Push protection (repository) |
| --- | --- | --- |
| New public, personal account (created on/after 2024-03-11) | On by default | On by default |
| Existing public (created before 2024-03-11) | "Not affected" by this change; the page states no default | "Not affected"; earlier enablement was advertised as opt-in (changelogs below) |
| New or existing private, personal account | Not available (Finding 1) | Not available (Finding 1) |

**Push protection for users (documented, account-level).**

> Push protection for users automatically protects you from accidentally committing secrets to public repositories, regardless of whether the repository itself has secret scanning enabled. Push protection for users is on by default, but you can disable the feature at any time through your personal account settings.
> — [GitHub security features](https://docs.github.com/en/code-security/getting-started/github-security-features)

The rollout announcement is dated and narrower than today's docs:

> We’ve started the rollout for enabling push protection on all free user accounts on GitHub. This automatically protects you from accidentally committing secrets to public repositories, regardless of whether the repository itself has secret scanning enabled. … It might take a week or two for this change to apply to your account; you can verify status and opt-in early in your code security and analysis settings. Once enabled, you also have the option to opt-out.
> — [GitHub Changelog, February 29, 2024](https://github.blog/changelog/2024-02-29-push-protection-is-enabled-for-free-users-on-github)

**Documented conflict on the repository-level default.** The push protection concept page describes repository-level push protection as off by default and gated on the paid product:

> Push protection for repositories
> You can enable push protection for repositories at the repository, organization, or enterprise level. This form of push protection:
> - Requires GitHub Secret Protection to be enabled
> - Is disabled by default, and can be enabled by a repository administrator, organization owner, security manager, or enterprise owner
> - Blocks pushes containing secrets from reaching specific protected repositories
> - Generates alerts for push protection bypasses in the Security and quality tab of the repository, organization, and enterprise
> — [Push protection](https://docs.github.com/en/code-security/concepts/secret-security/push-protection)

That contradicts the March 2024 changelog and the availability table, which mark repository-level push protection as on by default (and available) for public repositories without Secret Protection. The most consistent reading of the three sources is that "Requires Secret Protection … disabled by default" describes the paid/private-repository case, while public repositories get the free, default-on behaviour. The pages do not reconcile this explicitly, so the conflict is reported rather than resolved.

**Earlier public-repository enablement (documented, dated).** For existing public repositories the earlier changelogs describe opt-in, not default:

> Secret scanning’s push protection feature is now generally available for all free public repositories on GitHub.com. You can enable push protection for any public repository on GitHub.com from your repository's "Code security and analysis" settings in the UI or REST API. … For your repositories that are not a part of an organization, you can bulk-enable secret scanning and push protection in your personal "Code security and analysis" settings.
> — [GitHub Changelog, May 9, 2023](https://github.blog/changelog/2023-05-09-secret-scannings-push-protection-is-available-on-public-repositories-for-free)

> You can now enable secret scanning alerts on all your personal public repositories from your account's code security and analysis settings.
> — [GitHub Changelog, February 28, 2023](https://github.blog/changelog/2023-02-28-enable-secret-scanning-alerts-on-all-your-public-repositories)

**Habit's repository (observed + documented).** `Habit130/agent-repo-governance` was created `2026-10-20T01:48:27Z` and is public (Live checks). It is therefore a new public repository owned by a personal account under the March 2024 default: documented default is secret scanning on and push protection on. Whether habit has since disabled either is not observable from Habit098 (Finding 5).

**Secret scanning versus push protection in the default picture (documented).** Two differences follow from the quoted pages. First, push protection exists in a second, account-level form that is on by default regardless of repository settings, while secret scanning has no account-level form: it is enabled per repository (or in bulk from the personal or organization "code security and analysis" settings). Second, when a public repository's own settings are off, the account-level form still blocks the push, but without a bypass reason and without an alert ([Working with push protection from the command line](https://docs.github.com/en/code-security/how-tos/secure-your-secrets/work-with-leak-prevention/push-protection-on-the-command-line)).

### 3. Turning it on: API, `gh`, permission and who can do it

**REST endpoint and fields (documented).** Repositories are updated with `PATCH /repos/{owner}/{repo}` and the `security_and_analysis` object:

> security_and_analysis object or null
> Specify which security and analysis features to enable or disable for the repository. To use this parameter, you must have admin permissions for the repository or be an owner or security manager for the organization that owns the repository.
> — [REST API endpoints for repositories](https://docs.github.com/en/rest/repos/repos)

The documented properties are:

| Property | Field | Values |
| --- | --- | --- |
| Secret scanning | `security_and_analysis.secret_scanning.status` | `enabled`, `disabled` |
| Push protection | `security_and_analysis.secret_scanning_push_protection.status` | `enabled`, `disabled` |
| Non-provider patterns | `security_and_analysis.secret_scanning_non_provider_patterns.status` | `enabled`, `disabled` |
| AI detection | `security_and_analysis.secret_scanning_ai_detection.status` | `enabled`, `disabled` |
| Delegated bypass | `security_and_analysis.secret_scanning_delegated_bypass.status` plus `..._options` | `enabled`, `disabled`; reviewer list |
| Delegated alert dismissal | `security_and_analysis.secret_scanning_delegated_alert_dismissal.status` | `enabled`, `disabled` |
| Code Security | `security_and_analysis.code_security.status` | `enabled`, `disabled` |
| Advanced Security | `security_and_analysis.advanced_security.status` | `enabled`, `disabled`; "For standalone Code Scanning or Secret Protection products, this parameter cannot be used." |

— [REST API endpoints for repositories](https://docs.github.com/en/rest/repos/repos)

The same endpoint documents its token permission:

> The fine-grained token must have the following permission set: "Administration" repository permissions (write)
> — [REST API endpoints for repositories](https://docs.github.com/en/rest/repos/repos) (Update a repository)

The same page documents the secret-scanning API surface:

> You can use the API to:
> - Enable or disable secret scanning and push protection for a repository. For more information, see REST API endpoints for repositories and expand the "Properties of the security_and_analysis object" section.
> - Retrieve and update secret scanning alerts from a repository.
> — [REST API endpoints for secret scanning](https://docs.github.com/en/rest/secret-scanning/secret-scanning)

No `secret_scanning_validity_checks` property appears in the current property list, although the validity-checks how-to says the REST API can enable validity checks for partner patterns. That discrepancy is recorded in **Open gaps**.

**`gh` (observed).** `gh` 2.98.0 exposes the two toggles through `gh repo edit`, the repository-settings command:

```
      --enable-advanced-security                 Enable advanced security in the repository
      --enable-secret-scanning                   Enable secret scanning in the repository
      --enable-secret-scanning-push-protection   Enable secret scanning push protection in the repository. Secret scanning must be enabled first
```

Observed with `gh repo edit --help` on 2026-10-22. There is no top-level `gh` command for secret scanning, push protection or security settings (observed: `gh --help` lists no such command).

**Permission and role (documented).**

- Repository update with `security_and_analysis` requires "admin permissions for the repository" (quote above).
- Secret scanning enablement is an administrator action: "A repository administrator can choose to disable secret scanning for a repository at any time." ([Enabling secret scanning](https://docs.github.com/en/code-security/how-tos/secure-your-secrets/detect-secret-leaks/enable-secret-scanning))
- On a personal account repository, changing these settings is owner-only. The permission page separates owner actions from collaborator actions:

> Repositories owned by personal accounts have a single owner who has full control of the repository. In addition to the actions that any collaborator can perform, the repository owner can perform the following actions.
> — [Permission levels for a personal account repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/permission-levels-for-a-personal-account-repository)

  The owner-only list in that table includes "Manage security and analysis settings for the repository", while the collaborator list contains code, issue, PR, wiki and release actions and no settings action. The same page states: "Collaborators on a personal repository can pull (read) the contents of the repository and push (write) changes to the repository."

**Can the owner script turn them on for a user-owned repository?** Documented yes, per repository: the PATCH parameter's documented condition is "admin permissions for the repository", not organization ownership, and no cited page limits the parameter to organization-owned repositories. The owner script running as habit (sole owner of a personal repository) meets that condition. The same admin condition governs reading: habit's token can `GET` the repository and see `security_and_analysis`, so the script can check state before patching. What the call can achieve is bounded by availability: on a public repository the feature is free and the call can re-enable it after a disable; on a private repository owned by a personal account the feature is not available (Finding 1), so the documented enablement path cannot deliver it there. The API's response for that private-repository case was not tested and is **not stated**.

**Bulk enablement for all of a personal account's repositories is documented as a UI setting, not an API.** The 2023 changelogs quoted in Finding 2 describe the personal "code security and analysis" settings as the bulk path; no REST endpoint for those account-level defaults was found in the repository or secret scanning API pages.

**What the write collaborator can read (documented).**

> In order to see the security_and_analysis block for a repository you must have admin permissions for the repository or be an owner or security manager for the organization that owns the repository.
> — [REST API endpoints for repositories](https://docs.github.com/en/rest/repos/repos)

> The authenticated user must be an administrator for the repository or for the organization that owns the repository to use this endpoint.
> — [REST API endpoints for secret scanning](https://docs.github.com/en/rest/secret-scanning/secret-scanning) (List, Get and Update secret scanning alerts; List locations)

The scan-history endpoint adds a product gate:

> This endpoint requires GitHub Advanced Security.
> — [REST API endpoints for secret scanning](https://docs.github.com/en/rest/secret-scanning/secret-scanning) (Get secret scanning scan history for a repository)

In the web UI, alert visibility is wider than API access:

> Security alerts for a repository are visible to people with write, maintain, or admin access to the repository and, when the repository is owned by an organization, organization owners.
> — [Managing security and analysis settings for your repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-security-and-analysis-settings-for-your-repository)

So Habit098, as a write collaborator, is documented by the repository-settings page to see repo security alerts in the UI but not to read `security_and_analysis` or the secret scanning alert API. That UI rule conflicts with the "Who can use this feature?" box on the alerts concept page, which names "Repository owners, organization owners, security managers, and users with the admin role" for secret scanning alerts; the API rule is unambiguously admin-only. Habit098's UI alert access is therefore documented inconsistently. Whether the UI shows the *enablement state* of secret scanning and push protection to a write collaborator is **not stated**; the settings page that displays those toggles is the admin Settings page.

### 4. Push protection for users (the account-level setting)

**Where it lives (documented).**

> In the upper-right corner of any page on GitHub, click your profile picture, then click Settings.
> In the "Security" section of the sidebar, click Code security.
> Under "User", to the right of "Push protection for yourself", update your settings.
> — [Managing push protection for users](https://docs.github.com/en/code-security/how-tos/secure-your-secrets/prevent-future-leaks/manage-user-push-protection)

**Default and scope (documented).** On by default; public repositories only; account-specific:

> Push protection for users is only available on GitHub.com, and is specific to your GitHub account. This form of push protection:
> - Is enabled by default
> - Stops you from pushing secrets to public repositories on GitHub
> - Does not generate alerts when you bypass push protection unless push protection is also enabled at the repository level
> — [Push protection](https://docs.github.com/en/code-security/concepts/secret-security/push-protection)

**Does it cover Habit098's pushes to repositories it can write to?** Documented as account-scoped and public-repository-scoped, so it covers Habit098's pushes to any public repository it can write to, including `Habit130/agent-repo-governance`, independently of that repository's own setting. It gives no protection on a private repository. Because it is "specific to your GitHub account", the account holder (Habit098) is the one who can disable it; no page documents a way for another account, including the repository owner, to read or enforce it.

**API / `gh` (not stated).** No REST endpoint or `gh` command for this setting was found: the [REST users](https://docs.github.com/en/rest/users/users) and [REST secret scanning](https://docs.github.com/en/rest/secret-scanning/secret-scanning) pages contain no mention of "push protection for users", and the Docs search API for "push protection for yourself" and "user push protection API" returned only the UI how-to, the two concept pages and the CLI/UI guides, no API reference. The documented control is the personal Settings page.

### 5. A blocked push: message, bypass, record

**What the pushing session sees (documented).** The CLI how-to shows the secret-specific part of the error, including the secret type and every commit and path that contains it:

```
remote:   —— GitHub Personal Access Token ——————————————————————
remote:    locations:
remote:      - commit: 8728dbe67
remote:        path: README.md:4
remote:      - commit: 03d69e5d3
remote:        path: README.md:4
remote:      - commit: 8053f7b27
remote:        path: README.md:4
```

> Examine the error message that displayed when you tried to push your branch, which lists all of the commits that contain the secret.
> — [Working with push protection from the command line](https://docs.github.com/en/code-security/how-tos/secure-your-secrets/work-with-leak-prevention/push-protection-on-the-command-line)

**`GH013` (partially documented, not for secret scanning).** A Docs search for `GH013` over `free-pro-team@latest` returned exactly one page, and it ties `GH013` to ruleset violations, not to secret scanning:

> If you receive a Repository rule violations found error, such as GH013: Repository rule violations found for refs/heads/main, data in the origin repository conflicts with rulesets configured on the destination organization.
> — [Troubleshooting your migration with GitHub Enterprise Importer](https://docs.github.com/en/migrations/troubleshooting/troubleshooting-your-migration-with-github-enterprise-importer)

The secret scanning pages quoted above do not show a `GH013` prefix or a `! [remote rejected]` trailer. Whether a secret-scanning block emits `GH013: Repository rule violations found` is therefore **not stated** in the current docs and is listed in **Open gaps**; the documented secret-scanning output is the `remote:` block quoted above.

**Who may bypass (documented).**

> For push protection for repositories, by default, anyone with write access to the repository can bypass push protection by specifying a bypass reason.
> — [Push protection](https://docs.github.com/en/code-security/concepts/secret-security/push-protection)

For habit's repository, if repository-level push protection is active (the documented default for a public repository created in 2026, Finding 2), that means Habit098, the write collaborator, can bypass by default. The stricter alternative is a paid, organization-shaped feature:

> With delegated bypass for push protection, you can:
> - Grant bypass permissions to select individuals, roles, and teams …
> - Introduce a review cycle for bypass requests from all other contributors. Requests expire after 7 days.
> — [Delegated bypass for push protection](https://docs.github.com/en/code-security/concepts/secret-security/delegated-bypass)

Delegated bypass requires Secret Protection (Finding 1 table), and its bypass actors are organization owners, security managers, listed teams/roles and custom-role holders. No page documents delegated bypass for a user-owned repository.

**How bypass works (documented).**

> Visit the URL returned by GitHub when your push was blocked, as the same user that performed the push. If a different user attempts to visit this URL, they will receive a 404 error.
> …
> Click Allow me to push this secret.
> Reattempt the push on the command line within three hours. If you have not pushed within three hours, you will need to repeat this process.
> — [Working with push protection from the command line](https://docs.github.com/en/code-security/how-tos/secure-your-secrets/work-with-leak-prevention/push-protection-on-the-command-line)

> You are required to specify a reason for bypassing push protection if the repository has secret scanning enabled.
> — [Working with push protection from the command line](https://docs.github.com/en/code-security/how-tos/secure-your-secrets/work-with-leak-prevention/push-protection-on-the-command-line)

For a public repository that has only user-level push protection (no repository-level secret scanning), the flow is weaker:

> When pushing to a public repository that doesn't have secret scanning enabled, you are still protected from accidentally pushing secrets thanks to push protection for users … you won't need to specify a reason for allowing the secret, and GitHub won't generate an alert.
> — [Working with push protection from the command line](https://docs.github.com/en/code-security/how-tos/secure-your-secrets/work-with-leak-prevention/push-protection-on-the-command-line)

**What is recorded (documented).** On bypass, the push protection concept page states that GitHub:

> Creates an alert in the Security and quality tab of the repository, organization, and enterprise … Adds the bypass event to the audit log … Sends an email alert to personal account, organization, and enterprise owners, security managers, and repository administrators who are watching the repository, with a link to the secret and the reason it was allowed
> — [Push protection](https://docs.github.com/en/code-security/concepts/secret-security/push-protection)

The audit-log event is named and defined on the organization audit-log page:

> secret_scanning_push_protection.bypass — Triggered when a user bypasses the push protection on a secret detected by secret scanning.
> — [Audit log events for your organization](https://docs.github.com/en/organizations/keeping-your-organization-secure/managing-security-settings-for-your-organization/audit-log-events-for-your-organization)

That event page is an organization page. The changelog that introduced the recording scoped it the same way:

> GitHub Advanced Security customers can now view bypasses of secret scanning's push protection in the enterprise and organization audit logs.
> — [GitHub Changelog, June 17, 2022](https://github.blog/changelog/2022-06-17-secret-scanning-push-protection-bypasses-are-now-shown-in-the-audit-log-and-api)

**Does a personal account have an audit log that records the bypass?** No audit log is documented for personal accounts; the personal equivalent is the security log, and it is scoped to the account holder's own actions:

> The security log lists all actions performed within the last 90 days.
> — [Reviewing your security log](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/reviewing-your-security-log)

> The events listed in your security log are triggered by your actions.
> — [Reviewing your security log](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/reviewing-your-security-log)

The [Security log events](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/security-log-events) page lists no `secret_scanning` event (zero occurrences on the page as fetched). So for habit's repository the documented durable record of a collaborator's bypass is the repository secret scanning alert (plus the email to owners/administrators watching the repository), not an audit log.

**Does a blocked push that is not bypassed create an alert? (documented).** No. Push protection alerts are the bypass record:

> If push protection detects a supported secret, it will block the push. When a contributor bypasses push protection to push a secret to the repository, a push protection alert is generated and displayed in the Security and quality tab of the repository. To see all push protection alerts for a repository, you must filter by bypassed: true on the alerts page.
> — [About secret scanning alerts](https://docs.github.com/en/code-security/concepts/secret-security/about-alerts)

> Alerts are not created if you choose to bypass your user-based push protection only. Alerts are only created if the repository itself has push protection enabled.
> — [About secret scanning alerts](https://docs.github.com/en/code-security/concepts/secret-security/about-alerts)

### 6. Coverage: code is blocked, prose is only alerted, logs are neither

**What push protection blocks (documented).**

> Push protection blocks secrets detected in:
> - Pushes from the command line
> - Commits made in the GitHub UI
> - File uploads to a repository on GitHub
> - Requests to the REST API
> - Interactions with the GitHub MCP server (public repositories only)
> — [Push protection](https://docs.github.com/en/code-security/concepts/secret-security/push-protection)

A push that is too large can skip the block: "If a push in a public repository is larger than 50 MB, push protection will skip it and won't scan it." ([Secret scanning detection scope](https://docs.github.com/en/code-security/reference/secret-security/secret-scanning-scope))

**What the REST block covers (documented).**

> The "Create a blob" and "Create or update file contents" endpoints in the REST API include push protection. … If you make a request with these endpoints whose content includes a supported secret, the REST API will return a 409 error, indicating that a secret has been detected.
> — [Push protection from the REST API](https://docs.github.com/en/code-security/concepts/secret-security/push-protection-from-the-rest-api)

> If the content of a PUT request to these endpoints includes a secret, the API will respond with a 409 error and provide a link for bypassing push protection, along with a placeholder_id. There is also a new API endpoint to bypass push protection programatically, Create a push protection bypass. … You need to be the individual or application that initially got blocked to be able to bypass the block successfully.
> — [GitHub Changelog, August 13, 2024](https://github.blog/changelog/2024-08-13-secret-scanning-push-protection-is-supported-for-content-upload-rest-api-endpoints)

That is content upload only. No page documents push protection for a PR or issue body, a comment or a discussion post; the enumerated block list above contains no prose surface.

**What secret scanning detects but does not block (documented).**

> GitHub also automatically scans:
> - Descriptions and comments in issues
> - Titles, descriptions, and comments, in open and closed historical issues
> - Titles, descriptions, and comments in pull requests
> - Titles, descriptions, and comments in GitHub Discussions
> - Wikis
> - Secret gists
> — [Secret scanning](https://docs.github.com/en/code-security/concepts/secret-security/secret-scanning)

The PR surface is stated at the same precision in the changelog:

> Users of secret scanning will now receive alerts for any new secrets exposed in a pull request's title, description, or comments (including reviews). Alerts can be viewed within the UI or the REST API.
> — [GitHub Changelog, December 12, 2023](https://github.blog/changelog/2023-12-12-secret-scanning-detects-secrets-in-github-pull-requests)

> GitHub secret scanning now detects and alerts you on secrets found in GitHub issues, wikis, discussions, and pull requests.
> — [GitHub Changelog, August 16, 2024](https://github.blog/changelog/2024-08-16-secret-scanning-for-non-code-github-surfaces-is-now-generally-available)

**Surface-by-surface result.**

| Surface | Blocked before it lands | Alert raised |
| --- | --- | --- |
| File content in a pushed commit (CLI/UI/upload) | Yes, repository push protection (Finding 5) | On bypass only |
| File content written via `Create a blob` / `Create or update file contents` | Yes, HTTP 409 | On bypass only |
| PR title, body, review and conversation comments | Not stated; no block in the documented block list | Yes, secret scanning alert |
| Issue title, body and comments | Not stated; no block in the documented block list | Yes, secret scanning alert |
| Discussion title, body and comments | Not stated; no block in the documented block list | Yes, secret scanning alert |
| Wiki pages | No block documented | Yes, secret scanning alert |
| Commit messages | Not stated | Not stated |
| PR/issue bodies created programmatically via API | No block documented for this path | The surface is documented as scanned; the API path is not called out separately |
| Actions log output | No block documented; logs are not in either documented scan/block list | Not documented as scanned; Actions log masking is a separate mechanism |

**Actions logs are masked, not scanned (documented).** A token echoed into a workflow log is not covered by either feature's documented surface list. GitHub Actions redacts values that are stored as Actions secrets, or that a workflow explicitly registers; it does not automatically redact arbitrary values:

> Mask all sensitive information that is not a GitHub secret by using ::add-mask::VALUE. This causes the value to be treated as a secret and redacted from logs.
> — [Using secrets in GitHub Actions](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)

> Be careful that your secrets do not get printed when your workflow runs. When using this workaround, GitHub does not redact secrets that are printed in logs.
> — [Using secrets in GitHub Actions](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)

So the log case depends on whether the value is already a registered secret or an `::add-mask::` value; an agent printing a fresh token into a log is neither blocked by push protection nor (on the documented scope) scanned by secret scanning.

The practical split the sources support: an agent pasting a token into a PR body or comment is **detected** (public repository, scanning on by default) but **not stopped**; an agent committing a token to a file is **stopped** by push protection on this repository under the documented default, unless it bypasses with a reason; an agent printing a token into a log is **not stopped** and is masked only if the value is already registered.

**Which alerts, and who sees them (documented).**

- Three alert types: user alerts, push protection alerts (bypass only), partner alerts, the last not shown in the repository UI ([About secret scanning alerts](https://docs.github.com/en/code-security/concepts/secret-security/about-alerts)).
- Alerts appear in the repository's "Security and quality" tab; push protection alerts require the `bypassed: true` filter ([About secret scanning alerts](https://docs.github.com/en/code-security/concepts/secret-security/about-alerts)).
- Visibility: write, maintain or admin, plus organization owners ([Managing security and analysis settings for your repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-security-and-analysis-settings-for-your-repository)). A write collaborator therefore sees them in the UI; the REST alert endpoints require admin (Finding 3).
- Bypass email goes to "personal account, organization, and enterprise owners, security managers, and repository administrators who are watching the repository" (quote in Finding 5).

## Live checks

All commands were run read-only with `gh` 2.98.0, authenticated as **Habit098** (observed `gh auth status`: token scopes `gist`, `read:org`, `repo`, `workflow`; no token value reproduced). Repository: `Habit130/agent-repo-governance`, public, default branch `main`, created `2026-10-20T01:48:27Z`, `pushed_at` `2026-10-22T09:44:10Z`.

| # | Command (GET only) | Observed result | Reading |
| --- | --- | --- | --- |
| 1 | `gh api repos/Habit130/agent-repo-governance` | `{"permissions":{"admin":false,"maintain":false,"pull":true,"push":true,"triage":true}, "private":false, "visibility":"public"}`; `jq '.security_and_analysis'` → `null`, and the response's key list contains **no** `security_and_analysis` key at all | Matches the documented rule that the block requires admin; the key is absent, not merely null-valued |
| 2 | `gh api repos/Habit130/agent-repo-governance/secret-scanning/alerts` | `HTTP/2.0 404 Not Found` + `{"message":"Not Found","documentation_url":"…/rest/secret-scanning/secret-scanning#list-secret-scanning-alerts-for-a-repository"}` | Matches "must be an administrator"; 404 is also what a disabled/absent feature would produce, so it does not distinguish the two |
| 3 | `gh api repos/Habit130/agent-repo-governance/secret-scanning/scan-history` | `HTTP 404` + `{"message":"Not Found"}` | Consistent with the GHAS requirement and admin requirement |
| 4 | `gh api repos/Habit130/agent-repo-governance/collaborators/Habit098/permission` | `{"permission":"write", …, "role_name":"write"}` with `permissions.admin=false` | Confirms the write-collaborator premise |
| 5 | `gh api user` | Keys contain no `plan`; `login` `Habit098`, `type` `User`, `public_repos` 8 | The agent cannot read its own plan from this token; no plan-based conclusion is drawn |
| 6 | `gh api users/Habit130` | Keys contain no `plan`; `type` `User`, `public_repos` 32 | The owner's plan is not readable by the agent either |
| 7 | `gh api repos/Habit130/agent-repo-governance/actions/secrets` | `HTTP 200` + `{"total_count":0,"secrets":[]}` | Listed for completeness on what a write collaborator can read; the repository currently has no Actions secrets. The endpoint returns secret names, not values |
| 8 | `gh repo edit --help`, `gh --help` | Security toggles exist only as `gh repo edit` flags; no top-level command for scanning/security | CLI enablement path is `gh repo edit` |

Interpretation, kept to what was observed: the agent account cannot observe `security_and_analysis`, cannot call the secret scanning alert API, and cannot call the scan-history API; it can read repository metadata, its own write role, and the (empty) Actions secrets name list. It cannot enable or disable either feature through documented means because doing so requires admin and the account is not admin. Whether secret scanning and push protection are actually enabled on this repository cannot be determined from Habit098's API responses; the documented default for a public repository created on 2026-10-20 is that both were enabled at creation.

## Availability summary

The table restates Findings 1–4 for habit's account shape. "Not available" means a cited page excludes the plan/account combination, not that a live attempt was made.

| Feature | Public repo, personal account (GitHub Free) | Private repo, personal account (GitHub Pro) | Evidence |
| --- | --- | --- | --- |
| Secret scanning (user alerts) | Yes, free, on by default for new public repos | Not available (user-owned repos need GHEC with EMU or GHES; Secret Protection not purchasable on a personal account) | [Secret scanning](https://docs.github.com/en/code-security/concepts/secret-security/secret-scanning), [About GitHub Advanced Security](https://docs.github.com/en/get-started/learning-about-github/about-github-advanced-security) |
| Repository push protection | Yes, free, on by default for new public repos | Not available (same reason) | [GitHub security features](https://docs.github.com/en/code-security/getting-started/github-security-features), [Changelog 2024-03-11](https://github.blog/changelog/2024-03-11-secret-scanning-and-push-protection-are-enabled-by-default-on-new-public-repositories) |
| Push protection for users | On by default, applies to pushes to public repositories | No effect on private repositories | [Push protection](https://docs.github.com/en/code-security/concepts/secret-security/push-protection) |
| Secret scanning alerts REST API | Admin-only | Admin-only, and feature unavailable | [REST API endpoints for secret scanning](https://docs.github.com/en/rest/secret-scanning/secret-scanning) |
| Custom patterns | No (requires Secret Protection) | No | [About GitHub Advanced Security](https://docs.github.com/en/get-started/learning-about-github/about-github-advanced-security) |
| Validity checks | Not stated in the availability table; documented under Secret Protection settings | Not stated; documented under Secret Protection settings | [Enabling validity checks](https://docs.github.com/en/code-security/how-tos/secure-your-secrets/customize-leak-detection/enable-validity-checks) |
| AI-detected secrets | No | No | [About GitHub Advanced Security](https://docs.github.com/en/get-started/learning-about-github/about-github-advanced-security) |
| Delegated bypass for push protection | No | No | [About GitHub Advanced Security](https://docs.github.com/en/get-started/learning-about-github/about-github-advanced-security) |
| Security overview | No (organization-scoped) | No | [Security overview](https://docs.github.com/en/code-security/concepts/security-at-scale/security-overview) |
| Bypass audit record | Organization/enterprise audit log only; personal accounts have a security log, which lists no secret scanning events | Same | [Audit log events](https://docs.github.com/en/organizations/keeping-your-organization-secure/managing-security-settings-for-your-organization/audit-log-events-for-your-organization), [Security log events](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/security-log-events) |

## Open gaps

1. **`GH013` for secret scanning.** Docs search finds `GH013` only on the migration troubleshooting page, attached to ruleset violations. No cited secret scanning page shows `GH013`, a `! [remote rejected]` line, or the full multi-line blocked-push message. A real blocked push would settle it, and was not performed.
2. **Default for public repositories created before 2024-03-11.** The March 2024 changelog says existing public repositories are "not affected" but does not state what their state is; the 2023 changelogs describe opt-in bulk enablement. No page gives one default for that cohort.
3. **Repository-level push protection on public repositories and Secret Protection.** The push protection concept page says this form "Requires GitHub Secret Protection to be enabled" and "Is disabled by default"; the availability table, the security-features page and the 2024 changelog say public repositories have it free and on by default. The pages do not reconcile the two.
4. **Education and GitHub Pro.** No page found states that GitHub Education grants GitHub Pro; the student benefits page lists Copilot and Codespaces only. The ticket's Pro premise could not be confirmed from primary docs, and no source states that any Education entitlement includes Secret Protection.
5. **Private-repository API response.** Whether `PATCH /repos/{owner}/{repo}` with `security_and_analysis.secret_scanning.status=enabled` succeeds, no-ops or errors on a user-owned private repository is not documented and was not tested.
6. **`security_and_analysis.secret_scanning_validity_checks`.** The validity-checks how-to says the REST API can enable validity checks for partner patterns, but the current `security_and_analysis` property list contains no validity-checks field. Which field is used is not stated.
7. **Push protection for a user setting via API.** No REST endpoint or `gh` command was found for reading or setting "Push protection for yourself"; the only documented control is the personal Settings page. Whether the setting participates in any API representation is not stated.
8. **Whether the UI exposes enablement state to a write collaborator.** Alerts are documented as visible to write access, but the enable/disable toggles live on the admin Settings page; no page states whether a non-admin can see the current on/off state anywhere in the UI.
9. **Commit messages.** Neither scanning nor blocking is documented for commit messages, although pushes and repository history are scanned for file content.
10. **Alerts for content created through the API.** Scanning is documented for PR/issue/discussion content, and blocking is documented only for file-upload endpoints; no page states whether a token pasted through the issues or pulls API is scanned differently from one pasted in the UI.
11. **Personal-account bypass record.** The only durable record documented for a personal account is the repository alert (and the email). No page states whether a bypass by a collaborator appears anywhere in the owner's personal security log; the security-log events page lists no secret scanning event.
12. **Scope of push protection for users.** Docs scope it to "public repositories", not to repositories with write access; it is not stated whether it applies to forks, or to pushes performed with an app or installation token rather than the user's own credentials.
13. **Actions logs.** Workflow logs are absent from secret scanning's documented surface list and from push protection's block list. No page states that a separate mechanism scans them, and the masking docs cover only registered secrets and `::add-mask::` values. Whether a token printed into a log is ever scanned is not stated.

## Sources

All sources are primary (`docs.github.com` or `github.blog/changelog`) or live read-only API responses. Accessed 2026-10-22.

### GitHub Docs

- Secret scanning (concepts) — https://docs.github.com/en/code-security/concepts/secret-security/secret-scanning
- Push protection (concepts) — https://docs.github.com/en/code-security/concepts/secret-security/push-protection
- Secret scanning alerts (concepts) — https://docs.github.com/en/code-security/concepts/secret-security/about-alerts
- Secret scanning detection scope — https://docs.github.com/en/code-security/reference/secret-security/secret-scanning-scope
- Push protection from the REST API — https://docs.github.com/en/code-security/concepts/secret-security/push-protection-from-the-rest-api
- Delegated bypass for push protection — https://docs.github.com/en/code-security/concepts/secret-security/delegated-bypass
- Bypass requests for push protection — https://docs.github.com/en/code-security/concepts/secret-security/bypass-requests
- Validity checks — https://docs.github.com/en/code-security/concepts/secret-security/validity-checks
- GitHub security features — https://docs.github.com/en/code-security/getting-started/github-security-features
- About GitHub Advanced Security — https://docs.github.com/en/get-started/learning-about-github/about-github-advanced-security
- Security overview — https://docs.github.com/en/code-security/concepts/security-at-scale/security-overview
- Enabling secret scanning — https://docs.github.com/en/code-security/how-tos/secure-your-secrets/detect-secret-leaks/enable-secret-scanning
- Enabling push protection — https://docs.github.com/en/code-security/how-tos/secure-your-secrets/prevent-future-leaks/enable-push-protection
- Managing push protection for users — https://docs.github.com/en/code-security/how-tos/secure-your-secrets/prevent-future-leaks/manage-user-push-protection
- Working with push protection from the command line — https://docs.github.com/en/code-security/how-tos/secure-your-secrets/work-with-leak-prevention/push-protection-on-the-command-line
- Working with push protection in the GitHub UI — https://docs.github.com/en/code-security/how-tos/secure-your-secrets/work-with-leak-prevention/push-protection-in-the-github-ui
- Enabling validity checks — https://docs.github.com/en/code-security/how-tos/secure-your-secrets/customize-leak-detection/enable-validity-checks
- Defining custom patterns for secret scanning — https://docs.github.com/en/code-security/how-tos/secure-your-secrets/customize-leak-detection/define-custom-patterns
- Managing security and analysis settings for your repository — https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-security-and-analysis-settings-for-your-repository
- Using secrets in GitHub Actions — https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets
- Permission levels for a personal account repository — https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/permission-levels-for-a-personal-account-repository
- REST API endpoints for repositories — https://docs.github.com/en/rest/repos/repos
- REST API endpoints for secret scanning — https://docs.github.com/en/rest/secret-scanning/secret-scanning
- REST API endpoints for users — https://docs.github.com/en/rest/users/users
- GitHub's plans — https://docs.github.com/en/get-started/learning-about-github/githubs-plans
- About GitHub Education for students — https://docs.github.com/en/education/about-github-education/github-education-for-students/about-github-education-for-students
- Reviewing your security log — https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/reviewing-your-security-log
- Security log events — https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/security-log-events
- Audit log events for your organization — https://docs.github.com/en/organizations/keeping-your-organization-secure/managing-security-settings-for-your-organization/audit-log-events-for-your-organization
- Troubleshooting your migration with GitHub Enterprise Importer — https://docs.github.com/en/migrations/troubleshooting/troubleshooting-your-migration-with-github-enterprise-importer

### GitHub Changelog

- Secret scanning is now available for free on public repositories (2022-12-15) — https://github.blog/changelog/2022-12-15-secret-scanning-is-now-available-for-free-on-public-repositories
- Secret scanning push protection bypasses are now shown in the audit log and API (2022-06-17) — https://github.blog/changelog/2022-06-17-secret-scanning-push-protection-bypasses-are-now-shown-in-the-audit-log-and-api
- Enable secret scanning alerts on all your public repositories (2023-02-28) — https://github.blog/changelog/2023-02-28-enable-secret-scanning-alerts-on-all-your-public-repositories
- Secret scanning's push protection is available on public repositories, for free (2023-05-09) — https://github.blog/changelog/2023-05-09-secret-scannings-push-protection-is-available-on-public-repositories-for-free
- Secret scanning detects secrets in GitHub pull requests (2023-12-12) — https://github.blog/changelog/2023-12-12-secret-scanning-detects-secrets-in-github-pull-requests
- Push protection is enabled for free users on GitHub (2024-02-29) — https://github.blog/changelog/2024-02-29-push-protection-is-enabled-for-free-users-on-github
- Secret scanning and push protection are enabled by default on new public repositories (2024-03-11) — https://github.blog/changelog/2024-03-11-secret-scanning-and-push-protection-are-enabled-by-default-on-new-public-repositories
- Secret scanning push protection is supported for content upload REST API endpoints (2024-08-13) — https://github.blog/changelog/2024-08-13-secret-scanning-push-protection-is-supported-for-content-upload-rest-api-endpoints
- Secret scanning for non-code GitHub surfaces is now generally available (2024-08-16) — https://github.blog/changelog/2024-08-16-secret-scanning-for-non-code-github-surfaces-is-now-generally-available

### Live API (read-only, observed 2026-10-22)

- `GET /repos/Habit130/agent-repo-governance`
- `GET /repos/Habit130/agent-repo-governance/secret-scanning/alerts`
- `GET /repos/Habit130/agent-repo-governance/secret-scanning/scan-history`
- `GET /repos/Habit130/agent-repo-governance/collaborators/Habit098/permission`
- `GET /repos/Habit130/agent-repo-governance/actions/secrets`
- `GET /user`
- `GET /users/Habit130`
