import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import auth  # noqa: E402


class Auth(unittest.TestCase):
    def test_a_matching_token_is_valid(self):
        self.assertTrue(auth.is_valid("sandbox-token", auth.digest("sandbox-token")))

    def test_another_token_is_not(self):
        self.assertFalse(auth.is_valid("other", auth.digest("sandbox-token")))

    def test_an_empty_token_is_not(self):
        self.assertFalse(auth.is_valid("", auth.digest("")))


if __name__ == "__main__":
    unittest.main()
