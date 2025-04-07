#!/usr/bin/env python3
import unittest
import sys


if __name__ == "__main__":
    loader = unittest.TestLoader()
    start_dir = 'ypy_sqlite/tests'
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    sys.exit(0 if result.wasSuccessful() else 1)