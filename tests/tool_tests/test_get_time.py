import unittest
from app.tools.get_time import get_time
import datetime
import re
import sys

class TestGetTime(unittest.TestCase):
    """Tests for get_time tool"""

    def test_invoke_returns_string(self):
        """Ensure tool returns a string"""
        result = get_time.invoke({})
        self.assertIsInstance(result, str)
        print("✓ get_time returns a string")

    def test_output_format(self):
        """Ensure output includes expected prefix and valid datetime"""
        result = get_time.invoke({})
        prefix = "The current system time is (YYYY-mm-dd HH:MM:SS) "
        self.assertTrue(result.startswith(prefix))
        print("✓ Prefix is correct")

        # Extract timestamp part
        timestamp = result.replace(prefix, "")
        try:
            datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            valid_format = True
        except ValueError:
            valid_format = False

        self.assertTrue(valid_format, f"Timestamp format invalid: {timestamp}")
        print("✓ Timestamp format valid")

    def test_tool_name_and_desc(self):
        """Ensure tool name and description are correct"""
        self.assertEqual(get_time.name, "get_time")
        self.assertIn("Returns the current system time", get_time.description)
        print("✓ Tool metadata correct")


if __name__ == "__main__":
    if "--manual" in sys.argv:
        # Manual test mode
        # Run using: python -m tests.tool_tests.test_get_time --manual
        print("\n=== Manual Test (getting time) ===")
        
        # Find the URL argument (everything after --manual)
        manual_idx = sys.argv.index("--manual")
        result = get_time.invoke({})
        print(result)
    else:
        print("\n=== Testing get_time tool ===\n")
        unittest.main(verbosity=2)
