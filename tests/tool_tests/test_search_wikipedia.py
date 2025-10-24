import unittest
from unittest.mock import patch, MagicMock
from app.tools.search_wikipedia import search_wikipedia
import sys


class TestSearchWikipedia(unittest.TestCase):
    """Tests for search_wikipedia tool"""

    @patch("app.tools.search_wikipedia.wikipedia")
    def test_valid_query(self, mock_wikipedia):
        """Test with a valid query"""
        mock_wikipedia.summary.return_value = "Python is a programming language."
        result = search_wikipedia.invoke({"query": "Python"})
        
        mock_wikipedia.summary.assert_called_once_with("Python", sentences=2)
        self.assertIn("Python is a programming language", result)
        print("✓ Valid query returns summary")

    @patch("app.tools.search_wikipedia.wikipedia")
    def test_wikipedia_not_installed(self, mock_wikipedia):
        """Test when wikipedia module is missing"""
        # Temporarily simulate wikipedia=None
        import app.tools.search_wikipedia as sw
        old_wiki = sw.wikipedia
        sw.wikipedia = None

        result = sw.search_wikipedia.invoke({"query": "Python"})
        self.assertIn("not installed", result)
        print("✓ Handles missing wikipedia module gracefully")

        # Restore
        sw.wikipedia = old_wiki

    @patch("app.tools.search_wikipedia.wikipedia")
    def test_exception_handling(self, mock_wikipedia):
        """Test when wikipedia.summary raises an exception"""
        mock_wikipedia.summary.side_effect = Exception("Page not found")
        result = search_wikipedia.invoke({"query": "asldkjasldkjasld"})
        
        self.assertIn("Wikipedia search error", result)
        print("✓ Exception handled correctly")

    def test_tool_name(self):
        """Test tool has correct name"""
        self.assertEqual(search_wikipedia.name, "search_wikipedia")
        print("✓ Tool name is correct")


if __name__ == "__main__":
    if "--manual" in sys.argv: 
        # Manual test mode 
        # Run using: python -m tests.tool_tests.test_search_wikipedia --manual <term> 
        print("\n=== Manual Test (searching wikipedia) ===") # Find the term argument (everything after --manual) 
        manual_idx = sys.argv.index("--manual") 
        if len(sys.argv) > manual_idx + 1: 
            term = sys.argv[manual_idx + 1] 
        else: 
            term = ""
        print(f"Searching: {term}") 
        result = search_wikipedia.invoke({"query": term}) 
        print(result) 
    else:
        print("\n=== Testing search_wikipedia ===\n")
        unittest.main(verbosity=2)
