#!/usr/bin/env python3
"""Build error excerpts must not depend on the checkout path's length."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run import build_diagnostic


class BuildDiagnostics(unittest.TestCase):
    def test_normalizes_before_bounding(self):
        short = "/tmp/lib"
        long = "/home/runner/" + "long-workspace/" * 12 + "lib"
        message = "{root}/C/header.h:42: candidate function\n" * 100
        a = build_diagnostic(message.format(root=short), short, "<library>")
        b = build_diagnostic(message.format(root=long), long, "<library>")
        self.assertEqual(a, b)
        self.assertEqual(len(a), 3000)
        self.assertTrue(a.startswith("<library>/C/header.h:42:"))

    def test_retains_other_diagnostics(self):
        self.assertEqual(build_diagnostic("prog.cpp:1: error\n", "/tmp/lib", "<library>"),
                         "prog.cpp:1: error\n")
        self.assertEqual(build_diagnostic("x" * 4000, "/tmp/lib", "<library>"), "x" * 3000)


if __name__ == "__main__":
    unittest.main()
