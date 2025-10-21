#!/usr/bin/env python3
"""
Test script for the chatter agent.
Tests the actual chat_agent() function from agents/chatter_agent.py
"""

import sys
import os

from app.agents.chatter_agent import chat_agent
from app.agents.agent_state import AgentState
from langchain_core.messages import HumanMessage

def test_chatter_with_subtask():
    """Test chat_agent() with a specific subtask"""
    print("=== Testing chat_agent() function ===")
    
    print("\n1. Testing with greeting subtask:")
    state = {
        "messages": [HumanMessage(content="Hello")],
        "current_subtask": "Respond to greeting and introduce yourself"
    }
    
    result = chat_agent(state)
    print(f"Result: {result}")

def test_chatter_explanation_subtask():
    """Test chat_agent() with explanation subtask"""
    print("\n2. Testing with explanation subtask:")
    state = {
        "messages": [HumanMessage(content="What is recursion?")],
        "current_subtask": "Explain what recursion is in programming"
    }
    
    result = chat_agent(state)
    print(f"Result: {result}")

def test_chatter_no_subtask():
    """Test chat_agent() with no subtask (fallback)"""
    print("\n3. Testing with no subtask (fallback):")
    state = {
        "messages": [HumanMessage(content="Hi there")],
        "current_subtask": ""
    }
    
    result = chat_agent(state)
    print(f"Result: {result}")

def test_chatter_morning_greeting():
    """Test chat_agent() with morning greeting subtask"""
    print("\n4. Testing morning greeting subtask:")
    state = {
        "messages": [HumanMessage(content="Good morning")],
        "current_subtask": "Respond to morning greeting"
    }
    
    result = chat_agent(state)
    print(f"Result: {result}")

if __name__ == "__main__":
    try:
        test_chatter_with_subtask()
        test_chatter_explanation_subtask()
        test_chatter_no_subtask()
        test_chatter_morning_greeting()
        print("\n=== chat_agent() Tests Complete ===")
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()