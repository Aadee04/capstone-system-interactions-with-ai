import unittest
from app.tools.run_python import run_python

class TestRunPython(unittest.TestCase):
    """Tests for the run_python tool"""

    def test_simple_print(self):
        """Test simple print statement"""
        code = 'print("Hello World")'
        result = run_python.invoke({"code": code})
        self.assertIn("Hello World", result)
        print("✓ Simple print works")

    def test_variable_assignment(self):
        """Test variable assignment and arithmetic"""
        code = 'x = 5\ny = 10\nprint(x + y)'
        result = run_python.invoke({"code": code})
        self.assertIn("15", result)
        print("✓ Arithmetic works")

    def test_syntax_error(self):
        """Test code with syntax error"""
        code = 'print("Missing quote)'
        result = run_python.invoke({"code": code})
        self.assertIn("SyntaxError", result)
        print("✓ Syntax error caught")

    def test_runtime_error(self):
        """Test code with runtime error"""
        code = '1 / 0'
        result = run_python.invoke({"code": code})
        self.assertIn("ZeroDivisionError", result)
        print("✓ Runtime error caught")

    def test_empty_code(self):
        """Test empty input"""
        code = ''
        result = run_python.invoke({"code": code})
        self.assertEqual(result, '')
        print("✓ Empty code returns empty string")

    def test_multiple_lines(self):
        """Test multiple lines of code"""
        code = '''
for i in range(3):
    print(i)
'''
        result = run_python.invoke({"code": code})
        self.assertIn("0", result)
        self.assertIn("1", result)
        self.assertIn("2", result)
        print("✓ Multi-line code works")

    def test_tool_name_and_direct(self):
        """Check tool metadata"""
        self.assertEqual(run_python.name, "run_python")
        self.assertTrue(run_python.return_direct)
        print("✓ Tool metadata is correct")

if __name__ == "__main__":
    unittest.main(verbosity=2)
