#!/usr/bin/env python3
"""Reproducible supplemental inputs for Ruby's FNM_PATHNAME oracle (#84).

`pairs` prints JSON [pattern, string] pairs without Ruby or the owner matcher.
`record` prints the whole fixture, asking /usr/bin/ruby for every verdict.
"""

import argparse
import json
import random
import subprocess


SEEDS = (84, 20261029)
SAMPLES_PER_SEED = 256
# Each token has candidate text for composing plausible strings, not expected answers.
# Ruby alone decides whether any complete pair matches.
FAMILIES = {
    "literal": (("a", "a"), ("m", "m"), ("main", "main"), (".", ".")),
    "star": (("*", ""), ("*", "ab")),
    "question": (("?", "m"),),
    "double-star": (("**", "a/b"), ("**/", ""), ("**/", "a/b/"),
                    ("**//", "a//"), ("***", "ab")),
    "slash": (("/", "/"), ("//", "//")),
    "escape": (("\\*", "*"), ("\\?", "?"), ("\\a", "a"), ("\\", "")),
    "set": (("[am]", "m"), ("[!a]", "m"), ("[^a]", "m"),
            ("[-am]", "-"), ("[am-]", "-"), ("[]a]", "]")),
    "range": (("[a-z]", "m"), ("[!-z]", "m"), ("[a-m-z]", "z")),
    "reversed-range": (("[m-a]", "m"), ("[m-a]", "a"), ("[!z-a]", "m")),
    "malformed-set": (("[", "["), ("[]", ""), ("[!", "!"), ("[a-", "a")),
}
STRINGS = ("", "a", "m", "z", "-", "/", "a/b", "a//", "main", "a/main",
           "a/b/main", "a//main", ".main", "a/.main", "*", "?", "[", "]")

RUBY_RECORDER = r'''
require 'json'
pairs = JSON.parse(STDIN.read)
puts JSON.generate({
  'oracle' => {
    'expression' => 'File.fnmatch(pattern, string, File::FNM_PATHNAME)',
    'ruby_version' => RUBY_VERSION,
    'ruby_description' => RUBY_DESCRIPTION
  },
  'cases' => pairs.map { |pattern, string|
    [pattern, string, File.fnmatch(pattern, string, File::FNM_PATHNAME)]
  }
})
'''


def generate_pairs():
    """Bounded, sorted unique pairs from token cross-products and seeded compositions."""
    pairs = set()
    tokens = [token for family in FAMILIES.values() for token in family]
    for prefix in ("", "refs/heads/"):
        for token, candidate in tokens:
            for suffix in ("", "ain", "main"):
                for string in STRINGS + (candidate + suffix,):
                    pairs.add((prefix + token + suffix, prefix + string))
    for seed in SEEDS:
        rng = random.Random(seed)
        for _ in range(SAMPLES_PER_SEED):
            selected = [rng.choice(tokens) for _ in range(rng.randint(1, 5))]
            prefix = rng.choice(("", "refs/heads/"))
            pattern = prefix + "".join(token for token, _ in selected)
            candidate = prefix + "".join(text for _, text in selected)
            for string in (candidate, candidate + "/main", candidate.replace("/", "//"),
                           prefix + rng.choice(STRINGS)):
                pairs.add((pattern, string))
    return [list(pair) for pair in sorted(pairs)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("pairs", "record"))
    args = parser.parse_args()
    pairs = generate_pairs()
    if args.command == "pairs":
        print(json.dumps(pairs, ensure_ascii=True))
        return
    result = subprocess.run(
        ["/usr/bin/ruby", "-e", RUBY_RECORDER], input=json.dumps(pairs),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
        check=True, timeout=60,
    )
    fixture = json.loads(result.stdout)
    fixture["description"] = "Supplemental generated Ruby oracle; preserves the separate historical ref-patterns.json."
    fixture["seeds"] = list(SEEDS)
    fixture["samples_per_seed"] = SAMPLES_PER_SEED
    fixture["token_families"] = list(FAMILIES)
    # One case per line keeps reviews of the recorded corpus readable.
    cases = fixture.pop("cases")
    header = json.dumps(fixture, indent=2)
    print(header[:-2] + ',\n  "cases": [\n'
          + ",\n".join("    " + json.dumps(row) for row in cases) + "\n  ]\n}")


if __name__ == "__main__":
    main()
