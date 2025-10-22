#!/usr/bin/env python3
"""
Test script for the tooler agent.
Tests the actual tooler_agent() function from agents/tooler_agent.py
"""

import sys
import os

from app.agents.tooler_agent import tooler_agent
from app.agents.agent_state import AgentState
from langchain_core.messages import HumanMessage

# ANSI color codes for terminal
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def format_result(state: AgentState):
    print(f"\nmessages list = {state.get('messages')}")
    print(f"\ntool_calls = {state.get('tool_calls')}")
    

def test_tooler_open_app():
    """Test tooler_agent() with app opening subtask"""
    print("=== Testing tooler_agent() function ===")
    
    print(f"\n{Colors.CYAN}{Colors.BOLD}1.{Colors.RESET} Testing open app subtask:")
    state = {
        "messages": [HumanMessage(content="Open calculator")],
        "current_subtask": "Open calculator",
        "user_context": ""
    }
    
    result = tooler_agent(state)
    print(f"Complete Result: {result}")
    print("\nFormatted Results:")
    format_result(result)

def test_tooler_open_browser():
    """Test tooler_agent() with browser opening subtask"""
    print(f"\n{Colors.GREEN}{Colors.BOLD}2.{Colors.RESET} Testing open browser subtask:")
    state = {
        "messages": [HumanMessage(content="Open Chrome and go to Google")],
        "current_subtask": "Open Chrome browser and go to https://www.google.com",
        "user_context": ""
    }
    
    result = tooler_agent(state)
    print(f"Complete Result: {result}")
    print("\nFormatted Results:")
    format_result(result)

def test_tooler_get_time():
    """Test tooler_agent() with get time subtask"""
    print(f"\n{Colors.YELLOW}{Colors.BOLD}3.{Colors.RESET} Testing get time subtask:")
    state = {
        "messages": [HumanMessage(content="What time is it?")],
        "current_subtask": "Get current system time",
        "user_context": ""
    }
    
    result = tooler_agent(state)
    print(f"Complete Result: {result}")
    print("\nFormatted Results:")
    format_result(result)

def test_tooler_file_operation():
    """Test tooler_agent() with file operation subtask"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}4.{Colors.RESET} Testing file operation subtask:")
    state = {
        "messages": [HumanMessage(content="Open Downloads folder")],
        "current_subtask": "Open Downloads folder",
        "user_context": ""
    }
    
    result = tooler_agent(state)
    print(f"Complete Result: {result}")
    print("\nFormatted Results:")
    format_result(result)

def test_tooler_with_context():
    """Test tooler_agent() with user context"""
    print(f"\n{Colors.MAGENTA}{Colors.BOLD}5.{Colors.RESET} Testing with user context:")
    state = {
        "messages": [HumanMessage(content="Open Chrome")],
        "current_subtask": "Open calc",
        "user_context": "I meant calculator on google"
    }
    
    result = tooler_agent(state)
    print(f"Complete Result: {result}")
    print("\nFormatted Results:")
    format_result(result)

def test_tooler_with_empty_subtask():
    """Test tooler_agent() with empty subtask"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}6.{Colors.RESET} Testing with empty subtask:")
    state = {
        "messages": [HumanMessage(content="")],
        "current_subtask": "",
        "user_context": ""
    }
    
    result = tooler_agent(state)
    print(f"Complete Result: {result}")
    print("\nFormatted Results:")
    format_result(result)

if __name__ == "__main__":
    try:
        test_tooler_open_app()
        test_tooler_open_browser()
        test_tooler_get_time()
        test_tooler_file_operation()
        test_tooler_with_context()
        test_tooler_with_empty_subtask()
        print("\n=== tooler_agent() Tests Complete ===")
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()