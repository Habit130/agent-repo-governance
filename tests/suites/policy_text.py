"""Section-scoped witnesses for the consolidated policy in #309."""

from collections import namedtuple
import re


def markdown_headings(lines):
    fence = None
    for index, line in enumerate(lines):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence is None and marker:
            fence = marker.group(1)
        elif fence is not None and marker and marker.group(1).startswith(fence) and not marker.group(2).strip():
            fence = None
        elif fence is None and re.match(r"^#{1,6} ", line):
            yield index


class Section(namedtuple("Section", "path heading", defaults=(None,))):
    """Read a rendered file or one Markdown heading and its descendants."""

    def read(self, text):
        if self.heading is None:
            return text
        lines = text.splitlines()
        headings = list(markdown_headings(lines))
        starts = [index for index in headings if lines[index] == self.heading]
        if len(starts) != 1:
            raise AssertionError("%s has %d headings named %r" % (self.path, len(starts), self.heading))
        start = starts[0]
        depth = len(self.heading.split(" ", 1)[0])
        next_heading = re.compile(r"^#{1,%d} " % depth)
        end = next((index for index in headings if index > start and next_heading.match(lines[index])), len(lines))
        return "\n".join(lines[start:end])


# A positive clause is literal (line wrapping ignored). A red clause is an
# operative regex and is narrower than the inventory's search where needed.
Clause = namedtuple("Clause", "section text")
PolicyRow = namedtuple("PolicyRow", "number home pointers red search branches", defaults=((),))
