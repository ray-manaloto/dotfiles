import unittest

from dotfiles2_py import greet


class GreetTest(unittest.TestCase):
    def test_greet(self) -> None:
        self.assertEqual(greet("python"), "hello python")


if __name__ == "__main__":
    unittest.main()
