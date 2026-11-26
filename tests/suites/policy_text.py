"""Section-scoped witnesses for the consolidated policy in #309."""

from collections import namedtuple
import re


class Section(namedtuple("Section", "path heading", defaults=(None,))):
    """Read a rendered file or one Markdown heading and its descendants."""

    def read(self, text):
        if self.heading is None:
            return text
        lines = text.splitlines()
        starts = [index for index, line in enumerate(lines) if line == self.heading]
        if len(starts) != 1:
            raise AssertionError("%s has %d headings named %r" % (self.path, len(starts), self.heading))
        start = starts[0]
        depth = len(self.heading.split(" ", 1)[0])
        next_heading = re.compile(r"^#{1,%d} " % depth)
        end = next((i for i in range(start + 1, len(lines)) if next_heading.match(lines[i])), len(lines))
        return "\n".join(lines[start:end])


# A positive clause is literal (line wrapping ignored). A red clause is an
# operative regex and is narrower than the inventory's search where needed.
Clause = namedtuple("Clause", "section text")
PolicyRow = namedtuple("PolicyRow", "number home pointers red search branches", defaults=((),))
