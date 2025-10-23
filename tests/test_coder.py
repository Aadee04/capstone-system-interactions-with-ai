#!/usr/bin/env python3
"""
Test script for the coder agent.
Tests the actual coder_agent() function from agents/coder_agent.py
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from app.agents.coder_agent import coder_agent
from app.agents.agent_state import AgentState
from langchain_core.messages import HumanMessage

# ANSI color codes for terminal
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def format_result(state: AgentState):
    print(f"\nmessages list = {state.get('messages')}")
    print(f"\ntool_calls = {state.get('tool_calls')}")
    
    # Safe access with checks
    tool_calls = state.get('tool_calls')
    if tool_calls and len(tool_calls) > 0:
        code = tool_calls[0].get('args', {}).get('code')
        if code:
            print(f"\nRaw Code:\n{code}")
        else:
            print("\nNo code found in tool_calls")
    else:
        print("\nNo tool_calls available")

def test_coder_factorial():
    """Test coder_agent() with factorial calculation"""
    print("=== Testing coder_agent() function ===")
    
    print(f"\n{Colors.CYAN}{Colors.BOLD}1.{Colors.RESET} Testing factorial calculation:")
    state = {
        "messages": [HumanMessage(content="Calculate factorial of 5")],
        "current_subtask": "Calculate factorial of 5",
        "user_context": ""
    }
    
    result = coder_agent(state)
    print(f"Complete Result: {result}")
    print("\nFormatted Results:")
    format_result(result)

def test_coder_fibonacci():
    """Test coder_agent() with Fibonacci sequence"""
    print(f"\n{Colors.GREEN}{Colors.BOLD}2.{Colors.RESET} Testing Fibonacci sequence:")
    state = {
        "messages": [HumanMessage(content="Generate first 10 Fibonacci numbers")],
        "current_subtask": "Generate the first 10 Fibonacci numbers",
        "user_context": ""
    }
    
    result = coder_agent(state)
    print(f"Complete Result: {result}")
    print("\nFormatted Results:")
    format_result(result)

def test_coder_simple_math():
    """Test coder_agent() with simple math"""
    print(f"\n{Colors.YELLOW}{Colors.BOLD}3.{Colors.RESET} Testing simple math calculation:")
    state = {
        "messages": [HumanMessage(content="Calculate 15*23")],
        "current_subtask": "Calculate 15*23",
        "user_context": ""
    }
    
    result = coder_agent(state)
    print(f"Complete Result: {result}")
    print("\nFormatted Results:")
    format_result(result)

def test_coder_date_time():
    """Test coder_agent() with date/time operations"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}4.{Colors.RESET} Testing date/time operations:")
    state = {
        "messages": [HumanMessage(content="Get today's date")],
        "current_subtask": "Get today's date in YYYY-MM-DD format",
        "user_context": ""
    }
    
    result = coder_agent(state)
    print(f"Complete Result: {result}")
    print("\nFormatted Results:")
    format_result(result)

def test_coder_list_operations():
    """Test coder_agent() with list operations"""
    print(f"\n{Colors.MAGENTA}{Colors.BOLD}5.{Colors.RESET} Testing list operations:")
    state = {
        "messages": [HumanMessage(content="Find average of numbers")],
        "current_subtask": "Calculate the average of [23, 45, 67, 89]",
        "user_context": ""
    }
    
    result = coder_agent(state)
    print(f"Complete Result: {result}")
    print("\nFormatted Results:")
    format_result(result)

def test_coder_with_context():
    """Test coder_agent() with user context"""
    print(f"\n{Colors.RED}{Colors.BOLD}6.{Colors.RESET} Testing with user context:")
    state = {
        "messages": [HumanMessage(content="Sort a list")],
        "current_subtask": "Write Python function to sort a list in ascending order",
        "user_context": "The list is dynamically generated at run time, after taking an input"
    }
    
    result = coder_agent(state)
    print(f"Complete Result: {result}")
    print("\nFormatted Results:")
    format_result(result)

if __name__ == "__main__":
    try:
        test_coder_factorial()
        test_coder_fibonacci()
        test_coder_simple_math()
        test_coder_date_time()
        test_coder_list_operations()
        test_coder_with_context()
        print("\n=== coder_agent() Tests Complete ===")
        print("\n\n=== Go Through the cases to see output ===")
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()