import unittest
from unittest.mock import patch
from app.tools.open_browser import open_browser_and_search
import sys


class TestOpenBrowser(unittest.TestCase):
    """Simple tests for open_browser_and_search tool"""
    
    @patch('webbrowser.open')
    def test_open_google(self, mock_browser):
        """Test opening Google"""
        result = open_browser_and_search.invoke({"url": "https://google.com"})
        
        mock_browser.assert_called_once_with("https://google.com")
        self.assertIn("Opened", result)
        self.assertIn("google.com", result)
        print("✓ Google opens successfully")
    
    @patch('webbrowser.open')
    def test_open_any_url(self, mock_browser):
        """Test opening any URL"""
        test_url = "https://github.com"
        result = open_browser_and_search.invoke({"url": test_url})
        
        mock_browser.assert_called_once_with(test_url)
        self.assertIn(test_url, result)
        print("✓ Any URL opens successfully")
    
    @patch('webbrowser.open')
    def test_empty_url(self, mock_browser):
        """Test with empty URL"""
        result = open_browser_and_search.invoke({"url": ""})
        
        mock_browser.assert_called_once_with("")
        self.assertIn("Opened", result)
        print("✓ Empty URL handled")
    
    def test_tool_name(self):
        """Test tool has correct name"""
        self.assertEqual(open_browser_and_search.name, "open_browser_and_search")
        print("✓ Tool name is correct")
    
    def test_return_direct(self):
        """Test tool has return_direct=True"""
        self.assertTrue(open_browser_and_search.return_direct)
        print("✓ return_direct is True")


if __name__ == "__main__":
    if "--manual" in sys.argv:
        # Manual test mode
        # Run using: python -m tests.tool_tests.test_open_browser --manual <url>
        print("\n=== Manual Test (opening browser) ===")
        
        # Find the URL argument (everything after --manual)
        manual_idx = sys.argv.index("--manual")
        if len(sys.argv) > manual_idx + 1:
            url = sys.argv[manual_idx + 1]
        else:
            url = "https://google.com"  # default
        
        print(f"Opening: {url}")
        result = open_browser_and_search.invoke({"url": url})
        print(result)
    else:
        # Run unit tests
        print("\n=== Testing open_browser_and_search ===\n")
        unittest.main(verbosity=2)