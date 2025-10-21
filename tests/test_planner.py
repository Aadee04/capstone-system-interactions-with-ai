#!/usr/bin/env python3
"""
Test script for the planner agent.
Tests the actual planner_agent() function from agents/planner_agent.py
"""

import sys
import os

from app.agents.planner_agent import planner_agent
from app.agents.agent_state import AgentState
from langchain_core.messages import HumanMessage

def test_planner_conversational():
    """Test planner_agent() with conversational request"""
    print("=== Testing planner_agent() function ===")
    
    print("\n1. Testing conversational request:")
    state = {
        "messages": [HumanMessage(content="Hi, how are you?")],
        "subtask_index": 0,
        "tasks": [],
        "current_executor": "",
        "current_subtask": ""
    }
    
    result = planner_agent(state)
    print(f"Result: {result}")

def test_planner_action():
    """Test planner_agent() with action request"""
    print("\n2. Testing action request:")
    state = {
        "messages": [HumanMessage(content="Open Chrome and go to Google")],
        "subtask_index": 0,
        "tasks": [],
        "current_executor": "",
        "current_subtask": ""
    }
    
    result = planner_agent(state)
    print(f"\nResult: {result}")

def test_planner_coding():
    """Test planner_agent() with coding request"""
    print("\n3. Testing coding request:")
    state = {
        "messages": [HumanMessage(content="Calculate the factorial of 5")],
        "subtask_index": 0,
        "tasks": [],
        "current_executor": "",
        "current_subtask": ""
    }
    
    result = planner_agent(state)
    print(f"Result: {result}")

def test_planner_subtask_progression():
    """Test planner_agent() handling next subtask with new array format"""
    print("\n4. Testing subtask progression:")
    state = {
        "messages": [HumanMessage(content="Open Chrome and calculator")],
        "subtask_index": 1,
        "tasks": [
            {"task": "Open Chrome browser", "executor": "tooler_agent"},
            {"task": "Open calculator", "executor": "tooler_agent"}
        ],
        "current_executor": "tooler_agent",
        "current_subtask": "Open Chrome browser"
    }
    
    result = planner_agent(state)
    print(f"Result: {result}")

def test_planner_completion():
    """Test planner_agent() task completion detection"""
    print("\n5. Testing task completion:")
    state = {
        "messages": [HumanMessage(content="Open Chrome and calculator")],
        "subtask_index": 2,  # Index >= tasks length
        "tasks": [
            {"task": "Open Chrome browser", "executor": "tooler_agent"},
            {"task": "Open calculator", "executor": "tooler_agent"}
        ],
        "current_executor": "tooler_agent",
        "current_subtask": "Open calculator"
    }
    
    result = planner_agent(state)
    print(f"Result: {result}")

def test_json_parsing():
    """Test the safe_json_parse function with new array format"""
    print("\n6. Testing JSON parsing:")
    from app.agents.planner_agent import safe_json_parse
    
    # Test valid array format
    test1 = '[{"task": "Open Chrome", "executor": "tooler_agent"}]'
    result1 = safe_json_parse(test1)
    print(f"Valid array: {result1}")
    
    # Test with markdown fences
    test2 = '```json\n[{"task": "Calculate 5+3", "executor": "coder_agent"}]\n```'
    result2 = safe_json_parse(test2)
    print(f"With fences: {result2}")
    
    # Test invalid JSON (should return {})
    test3 = 'invalid json here'
    result3 = safe_json_parse(test3)
    print(f"Invalid JSON: {result3}")

def test_planner_decision():
    """Test planner_decision function"""
    print("\n7. Testing planner_decision:")
    from app.agents.planner_agent import planner_decision
    
    test_cases = [
        {"current_executor": "tooler_agent",
         "current_subtask": "test1", 
            "expected": "tooler_agent"},
            
        {"current_executor": "coder_agent", 
         "current_subtask": "test2",
            "expected": "coder_agent"}, 

        {"current_executor": "chatter_agent", 
         "current_subtask": "test3",
            "expected": "chatter_agent"},

        {"current_executor": "exit", 
         "current_subtask": "no_op",
            "expected": "exit"},

        {"current_executor": "exit", 
         "current_subtask": "done", 
            "expected": "exit"}
    ]
    
    for i, case in enumerate(test_cases, 1):
        state = case.copy()
        expected = state.pop("expected")
        result = planner_decision(state)
        status = "✓" if result == expected else "✗"
        print(f"  Test {i}: {status} {case} -> {result}")

if __name__ == "__main__":
    try:
        test_planner_conversational()
        test_planner_action()
        test_planner_coding()
        test_planner_subtask_progression()  # WORKS
        test_planner_completion()
        test_json_parsing()
        test_planner_decision()
        print("\n=== planner_agent() Tests Complete ===")
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
