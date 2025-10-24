#!/usr/bin/env python3
"""
Integration Test for Context-Aware Agent System
Tests the integration of all context-aware modules with the agent system
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch

class TestContextIntegration(unittest.TestCase):
    """Test integration of context-aware features with agent system"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_state = {
            "messages": [],
            "subtask_index": 0,
            "tasks": [],
            "current_executor": "",
            "current_subtask": "",
            "user_context": "",
            "tooler_tries": 0,
            "coder_tries": 0,
            "verifier_decision": "",
            "tool_calls": []
        }
    
    def test_context_modules_import(self):
        """Test that all context modules can be imported"""
        try:
            from modules.context.system_state_tracker import get_state_tracker
            from modules.context.context_manager import get_context_manager
            from modules.context.smart_query_resolver import get_smart_resolver
            from modules.session.session_manager import get_session_manager
            from modules.shortcuts.smart_shortcuts import get_shortcuts_manager
            from modules.suggestions.proactive_suggestions import get_suggestion_engine
            from modules.visual.visual_verifier import get_visual_verifier
            
            print("✓ All context modules imported successfully")
            return True
            
        except ImportError as e:
            print(f"✗ Module import failed: {e}")
            return False
    
    def test_planner_context_awareness(self):
        """Test enhanced planner with context-aware features"""
        try:
            from app.agents.planner_agent import pre_process_query_with_context, get_proactive_suggestions_context
            
            # Test context detection
            context_queries = [
                "open my work folder",
                "save my current session",
                "run coding setup", 
                "show recent files",
                "check system health"
            ]
            
            for query in context_queries:
                result = pre_process_query_with_context(query)
                print(f"Query: '{query}' -> Enhanced: {result['enhanced']}")
            
            # Test suggestions context
            suggestions_context = get_proactive_suggestions_context()
            print(f"Suggestions context: {len(suggestions_context)} chars")
            
            print("✓ Enhanced planner context features working")
            return True
            
        except Exception as e:
            print(f"✗ Planner context test failed: {e}")
            return False
    
    def test_tools_availability(self):
        """Test that context-aware tools are discoverable"""
        try:
            from app.agents.discover_app import discover_tools, discover_tools_descriptions
            
            tools = discover_tools()
            tool_descriptions = discover_tools_descriptions()
            
            # Check for context-aware tools
            context_tool_names = [
                'save_current_session', 'restore_session', 'list_available_sessions',
                'execute_shortcut', 'list_shortcuts', 'create_shortcut_from_template',
                'resolve_context_query', 'get_recent_files_context',
                'get_system_suggestions', 'run_health_check'
            ]
            
            discovered_names = [tool.name for tool in tools]
            available_context_tools = [name for name in context_tool_names if name in discovered_names]
            
            print(f"✓ Discovered {len(tools)} total tools")
            print(f"✓ Available context tools: {len(available_context_tools)}/{len(context_tool_names)}")
            
            if len(available_context_tools) > 0:
                print("Context-aware tools found:")
                for tool_name in available_context_tools:
                    print(f"  - {tool_name}")
            
            return len(available_context_tools) > 0
            
        except Exception as e:
            print(f"✗ Tools availability test failed: {e}")
            return False

    def test_agent_graph_structure(self):
        """Test that the agent graph is properly configured"""
        try:
            from app.agent import graph  # import the compiled graph
            
            expected_nodes = [
                'planner_agent', 
                'chatter_agent', 
                'tooler_agent', 
                'coder_agent', 
                'verifier_agent'
            ]
            
            # LangGraph stores nodes in graph.nodes (dict-like)
            # After compilation, it's in the compiled graph object
            actual_nodes = []
            
            # Check if it's a compiled graph
            if hasattr(graph, 'get_graph'):
                # Get the graph representation
                graph_repr = graph.get_graph()
                actual_nodes = list(graph_repr.nodes.keys())
            elif hasattr(graph, 'nodes'):
                actual_nodes = list(graph.nodes.keys())
            
            # Filter out special nodes like __start__ and __end__
            actual_nodes = [n for n in actual_nodes if not n.startswith('__')]
            
            found_nodes = [node for node in expected_nodes if node in actual_nodes]
            missing_nodes = [node for node in expected_nodes if node not in actual_nodes]
            
            print(f"✓ Agent graph nodes: {len(found_nodes)}/{len(expected_nodes)} found")
            print(f"  Found nodes: {found_nodes}")
            if missing_nodes:
                print(f"  Missing nodes: {missing_nodes}")
            
            # Check edges
            edges_ok = True
            if hasattr(graph, 'get_graph'):
                graph_repr = graph.get_graph()
                edges = graph_repr.edges
                
                for node in expected_nodes:
                    if node not in actual_nodes:
                        continue
                        
                    # Find outgoing edges from this node
                    outgoing = [e for e in edges if e.source == node]
                    
                    if node != "verifier_agent" and not outgoing:
                        print(f"✗ Node '{node}' has no outgoing edges")
                        edges_ok = False
                    else:
                        print(f"  {node} → {[e.target for e in outgoing]}")
            
            # Return True only if all expected nodes found and edges are fine
            result = len(found_nodes) == len(expected_nodes) and edges_ok
            
            if not result:
                print("✗ Agent graph structure test failed")
            else:
                print("✓ Agent graph structure test passed")
                
            return result
            
        except Exception as e:
            print(f"✗ Agent graph structure test failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False


    def test_context_tool_execution(self):
        """Test basic execution of context-aware tools"""
        test_results = []
        
        # Test session tools
        try:
            from app.tools.context_sessions import list_available_sessions
            result = list_available_sessions()
            print(f"✓ Session tool test: {result[:50]}...")
            test_results.append(True)
        except Exception as e:
            print(f"✗ Session tool test failed: {e}")
            test_results.append(False)
        
        # Test shortcut tools
        try:
            from app.tools.context_shortcuts import get_shortcut_templates
            result = get_shortcut_templates()
            print(f"✓ Shortcut tool test: {result[:50]}...")
            test_results.append(True)
        except Exception as e:
            print(f"✗ Shortcut tool test failed: {e}")
            test_results.append(False)
        
        # Test recent files tool
        try:
            from app.tools.get_recent_files import get_recent_files
            result = get_recent_files(count=3)
            print(f"✓ Recent files tool test: {result.get('count', 0)} files")
            test_results.append(True)
        except Exception as e:
            print(f"✗ Recent files tool test failed: {e}")
            test_results.append(False)
        
        return any(test_results)
    
    def run_integration_tests(self):
        """Run all integration tests"""
        print("=" * 60)
        print("Context-Aware Agent System Integration Test")
        print("=" * 60)
        
        tests = [
            ("Context Modules Import", self.test_context_modules_import),
            ("Planner Context Awareness", self.test_planner_context_awareness),
            ("Tools Availability", self.test_tools_availability),
            ("Agent Graph Structure", self.test_agent_graph_structure),
            ("Context Tool Execution", self.test_context_tool_execution)
        ]
        
        results = []
        for test_name, test_func in tests:
            print(f"\n--- {test_name} ---")
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"✗ {test_name} failed with exception: {e}")
                results.append((test_name, False))
        
        # Summary
        print("\n" + "=" * 60)
        print("Integration Test Summary")
        print("=" * 60)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{status:<8} {test_name}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed >= total * 0.8:  # 80% pass rate
            print("🎉 Integration test PASSED - System is ready!")
            return True
        else:
            print("⚠️  Integration test FAILED - Some components need attention")
            return False


def run_integration_test():
    """Run the integration test"""
    tester = TestContextIntegration()
    return tester.run_integration_tests()


if __name__ == "__main__":
    success = run_integration_test()
    sys.exit(0 if success else 1)