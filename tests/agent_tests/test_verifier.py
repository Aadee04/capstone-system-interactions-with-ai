#!/usr/bin/env python3
"""
Test script for the verifier agent.
Tests the actual verifier_agent() function from agents/verifier_agent.py
"""

import sys
import os

from app.agents.verifier_agent import verifier_agent
from app.agents.agent_state import AgentState
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

def test_verifier_chatter_success():
    """Test verifier_agent() with successful chatter output"""
    print("=== Testing verifier_agent() function ===")
    
    print("\n1. Testing chatter success verification:")
    state = {
        "messages": [
            HumanMessage(content="Hi, how are you?"),
            AIMessage(content="Hello! I'm doing well, thank you for asking. How can I assist you today?")
        ],
        "current_subtask": "Respond to greeting and introduce yourself",
        "current_executor": "chatter_agent",
        "subtask_index": 0,
        "tooler_tries": 0,
        "coder_tries": 0,
        "user_context": ""
    }
    
    result = verifier_agent(state)
    print(f"Result: {result}")

def test_verifier_tooler_success():
    """Test verifier_agent() with successful tooler execution"""
    print("\n2. Testing tooler success verification:")
    state = {
        "messages": [
            HumanMessage(content="Open calculator"),
            AIMessage(content="I'll open the calculator for you.", tool_calls=[{"id": "call_1", "name": "open_app", "args": {"app_name": "calculator"}}]),
            ToolMessage(content="Calculator opened successfully", tool_call_id="call_1")
        ],
        "current_subtask": "Open calculator",
        "current_executor": "tooler_agent",
        "subtask_index": 0,
        "tooler_tries": 0,
        "coder_tries": 0,
        "user_context": ""
    }
    
    result = verifier_agent(state)
    print(f"Result: {result}")

def test_verifier_tooler_failure():
    """Test verifier_agent() with failed tooler execution"""
    print("\n3. Testing tooler failure verification:")
    state = {
        "messages": [
            HumanMessage(content="Open calculator"),
            AIMessage(content="I'll open the calculator for you.", tool_calls=[{"id": "call_1", "name": "open_app", "args": {"app_name": "calculator"}}]),
            ToolMessage(content="Error: Application not found", tool_call_id="call_1")
        ],
        "current_subtask": "Open calculator",
        "current_executor": "tooler_agent",
        "subtask_index": 0,
        "tooler_tries": 0,
        "coder_tries": 0,
        "user_context": ""
    }
    
    result = verifier_agent(state)
    print(f"Result: {result}")

def test_verifier_coder_success():
    """Test verifier_agent() with successful coder execution"""
    print("\n4. Testing coder success verification:")
    state = {
        "messages": [
            HumanMessage(content="Calculate 5*3"),
            AIMessage(content="I'll calculate that for you.", tool_calls=[{"id": "call_1", "name": "run_python", "args": {"code": "result = 5 * 3\nprint(result)"}}]),
            ToolMessage(content="15", tool_call_id="call_1")
        ],
        "current_subtask": "Calculate 5*3",
        "current_executor": "coder_agent",
        "subtask_index": 0,
        "tooler_tries": 0,
        "coder_tries": 0,
        "user_context": ""
    }
    
    result = verifier_agent(state)
    print(f"Result: {result}")

def test_verifier_escalation_scenario():
    """Test verifier_agent() escalation after multiple failures"""
    print("\n5. Testing escalation scenario:")
    state = {
        "messages": [
            HumanMessage(content="Calculate factorial"),
            AIMessage(content="I'll try to use a tool for this.", tool_calls=[{"id": "call_1", "name": "no_op", "args": {}}]),
            ToolMessage(content="No appropriate tool available", tool_call_id="call_1")
        ],
        "current_subtask": "Calculate factorial of 5",
        "current_executor": "tooler_agent",
        "subtask_index": 0,
        "tooler_tries": 2,  # Already tried twice
        "coder_tries": 0,
        "user_context": ""
    }
    
    result = verifier_agent(state)
    print(f"Result: {result}")

def test_verifier_with_user_context():
    """Test verifier_agent() with user context"""
    print("\n6. Testing with user context:")
    state = {
        "messages": [
            HumanMessage(content="Open Chrome"),
            AIMessage(content="I'll open Chrome browser for you.", tool_calls=[{"id": "call_1", "name": "open_browser", "args": {"url": "chrome"}}]),
            ToolMessage(content="Browser opened", tool_call_id="call_1")
        ],
        "current_subtask": "Open Chrome browser",
        "current_executor": "tooler_agent",
        "subtask_index": 0,
        "tooler_tries": 0,
        "coder_tries": 0,
        "user_context": "User wants to browse the internet"
    }
    
    result = verifier_agent(state)
    print(f"Result: {result}")

if __name__ == "__main__":
    try:
        test_verifier_chatter_success()
        test_verifier_tooler_success()
        test_verifier_tooler_failure()
        test_verifier_coder_success()
        test_verifier_escalation_scenario()
        test_verifier_with_user_context()
        print("\n=== verifier_agent() Tests Complete ===")
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()