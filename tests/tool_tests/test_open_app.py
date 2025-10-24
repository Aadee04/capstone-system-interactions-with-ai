import unittest
from unittest.mock import patch, MagicMock
from app.tools.open_app import open_app, run_safe_os_command, ALLOWED_OS_ACTIONS


class TestOpenApp(unittest.TestCase):
    """Test suite for open_app tool"""
    
    def test_allowed_apps_defined(self):
        """Test that ALLOWED_OS_ACTIONS is properly configured"""
        self.assertIsInstance(ALLOWED_OS_ACTIONS, dict)
        self.assertIn("calculator", ALLOWED_OS_ACTIONS)
        self.assertIn("notepad", ALLOWED_OS_ACTIONS)
        print("✓ Allowed apps properly defined")
    
    @patch('os.startfile')
    def test_open_calculator(self, mock_startfile):
        """Test opening calculator (allowed app)"""
        result = open_app.invoke({"app_name": "calculator"})
        
        # Check that os.startfile was called
        mock_startfile.assert_called_once_with("calc.exe")
        self.assertIn("opened successfully", result)
        print("✓ Calculator opens successfully")
    
    @patch('os.startfile')
    def test_open_notepad(self, mock_startfile):
        """Test opening notepad (allowed app)"""
        result = open_app.invoke({"app_name": "notepad"})
        
        mock_startfile.assert_called_once_with("notepad.exe")
        self.assertIn("opened successfully", result)
        print("✓ Notepad opens successfully")
    
    @patch('os.startfile')
    def test_case_insensitive(self, mock_startfile):
        """Test that app names are case-insensitive"""
        result1 = open_app.invoke({"app_name": "CALCULATOR"})
        self.assertIn("opened successfully", result1)
        
        result2 = open_app.invoke({"app_name": "Calculator"})
        self.assertIn("opened successfully", result2)
        
        result3 = open_app.invoke({"app_name": "CaLcUlAtOr"})
        self.assertIn("opened successfully", result3)
        
        print("✓ Case-insensitive app names work")
    
    def test_disallowed_app(self):
        """Test that disallowed apps are rejected"""
        # Try to open a dangerous/non-whitelisted app
        result = open_app.invoke({"app_name": "cmd"})
        self.assertIn("not allowed", result)
        
        result2 = open_app.invoke({"app_name": "powershell"})
        self.assertIn("not allowed", result2)
        
        print("✓ Disallowed apps are properly blocked")
    
    def test_empty_app_name(self):
        """Test behavior with empty app name"""
        result = open_app.invoke({"app_name": ""})
        self.assertIn("not allowed", result)
        print("✓ Empty app name is rejected")
    
    @patch('os.startfile')
    def test_os_error_handling(self, mock_startfile):
        """Test that OS errors are handled gracefully"""
        # Simulate OS error
        mock_startfile.side_effect = OSError("File not found")
        
        result = open_app.invoke({"app_name": "calculator"})
        self.assertIn("Failed to open", result)
        self.assertIn("calculator", result.lower())
        print("✓ OS errors are handled gracefully")
    
    @patch('os.startfile')
    def test_multiple_paths(self, mock_startfile):
        """Test app with multiple possible paths (like Word)"""
        result = open_app.invoke({"app_name": "word"})
        
        # Should try to open the Word executable
        self.assertTrue(mock_startfile.called)
        # Check it was called with the correct path
        call_args = mock_startfile.call_args[0][0]
        self.assertIn("WINWORD.EXE", call_args)
        print("✓ Apps with multiple paths handled correctly")
    
    def test_tool_metadata(self):
        """Test that the tool has proper metadata"""
        # Check tool name
        self.assertEqual(open_app.name, "open_app")
        
        # Check description exists
        self.assertIsNotNone(open_app.description)
        self.assertIn("calculator", open_app.description.lower())
        
        print("✓ Tool metadata is correct")
    
    def test_run_safe_os_command_directly(self):
        """Test the underlying run_safe_os_command function"""
        # Test disallowed app
        result = run_safe_os_command("malicious_app")
        self.assertIn("not allowed", result)
        
        print("✓ Direct command function works")


class TestOpenAppIntegration(unittest.TestCase):
    """Integration tests (these may actually open apps if not mocked)"""
    
    @patch('os.startfile')
    def test_real_world_usage(self, mock_startfile):
        """Test realistic usage scenario"""
        # Simulate agent calling the tool
        apps_to_test = ["calculator", "notepad"]
        
        for app in apps_to_test:
            result = open_app.invoke({"app_name": app})
            self.assertIn("opened successfully", result)
        
        self.assertEqual(mock_startfile.call_count, len(apps_to_test))
        print(f"✓ Realistic agent usage works ({len(apps_to_test)} apps)")
    
    @patch('os.startfile')
    def test_security_bypass_attempts(self, mock_startfile):
        """Test that security bypass attempts are blocked"""
        malicious_attempts = [
            "cmd",
            "powershell",
            "regedit",
            "../../../windows/system32/cmd.exe",
            "calc.exe; rm -rf /",  # Command injection attempt
            "calculator & del *.*",
        ]
        
        for attempt in malicious_attempts:
            result = open_app.invoke({"app_name": attempt})
            self.assertIn("not allowed", result)
            # Ensure os.startfile was never called for malicious attempts
        
        mock_startfile.assert_not_called()
        print(f"✓ All {len(malicious_attempts)} security bypass attempts blocked")


def run_tests():
    """Helper function to run all tests"""
    print("\n=== Testing open_app Tool ===\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestOpenApp))
    suite.addTests(loader.loadTestsFromTestCase(TestOpenAppIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n=== Test Summary ===")
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)