# Verification depends on what a PR changes, not on its tier

Once the generator v1 spec's deliveries set it up, a PR in this repository needs checks chosen by what it touches, whatever its risk tier. These checks come on top of the reviews its tier requires:

- A PR that touches the generator runs its scenarios.
- A PR that touches what GitHub runs, or what habit runs against GitHub, gets a live check in the sandbox repository.

A reader would expect tiers to drive everything. Here a low PR that touches the generator still runs scenarios, and a high PR that touches only role files runs no live check.

Decided in [How the generator and the install are verified before a version ships](https://github.com/Habit130/agent-repo-governance/issues/40).
