#!/usr/bin/env python3
"""
Context Resolver Tool
Tool for smart query resolution and context-aware commands
"""

from typing import Dict, List, Any, Optional
from modules.context.smart_query_resolver import get_smart_resolver
from modules.context.context_manager import get_context_manager
from langchain.tools import tool


def resolve_query(query: str) -> Dict[str, Any]:
    """
    Resolve a natural language query into actionable commands
    
    Args:
        query (str): Natural language query (e.g., "open my school folder", "close that app")
        
    Returns:
        Dict: Resolved command with details and confidence score
    """
    try:
        query_resolver = get_smart_resolver()
        result = query_resolver.resolve_query(query)
        
        if result['success']:
            return {
                "success": True,
                "query": query,
                "command": result['command'],
                "confidence": result['confidence'],
                "context_used": result.get('context_used', []),
                "message": f"Resolved query to: {result['command']['action']}"
            }
        else:
            return {
                "success": False,
                "query": query,
                "command": None,
                "confidence": 0.0,
                "context_used": [],
                "error": result.get('error', 'Failed to resolve query')
            }
            
    except Exception as e:
        return {
            "success": False,
            "query": query,
            "command": None,
            "confidence": 0.0,
            "context_used": [],
            "error": f"Error resolving query: {str(e)}"
        }


def add_context_shortcut(alias: str, target_path: str, description: str = "") -> Dict[str, Any]:
    """
    Add a custom context shortcut
    
    Args:
        alias (str): Shortcut alias (e.g., "school folder", "work docs")
        target_path (str): Full path to the target
        description (str): Optional description
        
    Returns:
        Dict: Operation result with success status
    """
    try:
        context_manager = get_context_manager()
        success = context_manager.add_shortcut(alias, target_path, description)
        
        if success:
            return {
                "success": True,
                "alias": alias,
                "target_path": target_path,
                "description": description,
                "message": f"Context shortcut '{alias}' added for '{target_path}'"
            }
        else:
            return {
                "success": False,
                "alias": alias,
                "target_path": target_path,
                "description": description,
                "error": f"Failed to add context shortcut '{alias}'"
            }
            
    except Exception as e:
        return {
            "success": False,
            "alias": alias,
            "target_path": target_path,
            "description": description,
            "error": f"Error adding context shortcut: {str(e)}"
        }


def list_context_shortcuts() -> Dict[str, Any]:
    """
    List all available context shortcuts
    
    Returns:
        Dict: List of context shortcuts
    """
    try:
        context_manager = get_context_manager()
        shortcuts = context_manager.get_shortcuts()
        
        # Format shortcuts for display
        formatted_shortcuts = []
        for alias, shortcut_data in shortcuts.items():
            formatted_shortcut = {
                'alias': alias,
                'path': shortcut_data['path'],
                'description': shortcut_data.get('description', ''),
                'usage_count': shortcut_data.get('usage_count', 0),
                'last_used': shortcut_data.get('last_used', 'Never')
            }
            formatted_shortcuts.append(formatted_shortcut)
        
        return {
            "success": True,
            "shortcuts": formatted_shortcuts,
            "count": len(formatted_shortcuts),
            "message": f"Found {len(formatted_shortcuts)} context shortcuts"
        }
        
    except Exception as e:
        return {
            "success": False,
            "shortcuts": [],
            "count": 0,
            "error": f"Error listing context shortcuts: {str(e)}"
        }


def remove_context_shortcut(alias: str) -> Dict[str, Any]:
    """
    Remove a context shortcut
    
    Args:
        alias (str): Shortcut alias to remove
        
    Returns:
        Dict: Operation result with success status
    """
    try:
        context_manager = get_context_manager()
        success = context_manager.remove_shortcut(alias)
        
        if success:
            return {
                "success": True,
                "alias": alias,
                "message": f"Context shortcut '{alias}' removed successfully"
            }
        else:
            return {
                "success": False,
                "alias": alias,
                "error": f"Context shortcut '{alias}' not found"
            }
            
    except Exception as e:
        return {
            "success": False,
            "alias": alias,
            "error": f"Error removing context shortcut: {str(e)}"
        }


def get_user_preferences() -> Dict[str, Any]:
    """
    Get current user preferences and learned patterns
    
    Returns:
        Dict: User preferences and patterns
    """
    try:
        context_manager = get_context_manager()
        preferences = context_manager.get_preferences()
        
        return {
            "success": True,
            "preferences": preferences,
            "message": "Retrieved user preferences successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "preferences": {},
            "error": f"Error getting user preferences: {str(e)}"
        }


def update_user_preference(key: str, value: Any) -> Dict[str, Any]:
    """
    Update a user preference
    
    Args:
        key (str): Preference key
        value (Any): Preference value
        
    Returns:
        Dict: Operation result with success status
    """
    try:
        context_manager = get_context_manager()
        success = context_manager.update_preference(key, value)
        
        if success:
            return {
                "success": True,
                "key": key,
                "value": value,
                "message": f"Preference '{key}' updated successfully"
            }
        else:
            return {
                "success": False,
                "key": key,
                "value": value,
                "error": f"Failed to update preference '{key}'"
            }
            
    except Exception as e:
        return {
            "success": False,
            "key": key,
            "value": value,
            "error": f"Error updating preference: {str(e)}"
        }


def get_context_suggestions(query: str) -> Dict[str, Any]:
    """
    Get context-based suggestions for a query
    
    Args:
        query (str): Partial or complete query
        
    Returns:
        Dict: Suggested completions and related actions
    """
    try:
        context_manager = get_context_manager()
        query_resolver = get_smart_resolver()
        
        # Get shortcuts that match the query
        shortcuts = context_manager.get_shortcuts()
        suggestions = []
        
        query_lower = query.lower()
        
        # Find matching shortcuts
        for alias, shortcut_data in shortcuts.items():
            if query_lower in alias.lower() or any(word in alias.lower() for word in query_lower.split()):
                suggestions.append({
                    'type': 'shortcut',
                    'alias': alias,
                    'path': shortcut_data['path'],
                    'description': shortcut_data.get('description', ''),
                    'suggested_query': f"open {alias}"
                })
        
        # Add common command suggestions based on query patterns
        command_suggestions = []
        if any(word in query_lower for word in ['open', 'launch', 'start']):
            command_suggestions.extend([
                {'type': 'action', 'action': 'open_file', 'description': 'Open a specific file'},
                {'type': 'action', 'action': 'open_folder', 'description': 'Open a folder location'},
                {'type': 'action', 'action': 'open_app', 'description': 'Launch an application'}
            ])
        elif any(word in query_lower for word in ['close', 'quit', 'exit']):
            command_suggestions.extend([
                {'type': 'action', 'action': 'close_app', 'description': 'Close an application'},
                {'type': 'action', 'action': 'close_window', 'description': 'Close a window'}
            ])
        
        return {
            "success": True,
            "query": query,
            "shortcut_suggestions": suggestions,
            "command_suggestions": command_suggestions,
            "total_suggestions": len(suggestions) + len(command_suggestions),
            "message": f"Found {len(suggestions) + len(command_suggestions)} suggestions for '{query}'"
        }
        
    except Exception as e:
        return {
            "success": False,
            "query": query,
            "shortcut_suggestions": [],
            "command_suggestions": [],
            "total_suggestions": 0,
            "error": f"Error getting context suggestions: {str(e)}"
        }


def learn_from_interaction(query: str, selected_action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Learn from user interaction to improve future suggestions
    
    Args:
        query (str): Original user query
        selected_action (Dict): Action that was selected/executed
        
    Returns:
        Dict: Learning result with success status
    """
    try:
        context_manager = get_context_manager()
        success = context_manager.learn_from_interaction(query, selected_action)
        
        if success:
            return {
                "success": True,
                "query": query,
                "action": selected_action,
                "message": "Successfully learned from interaction"
            }
        else:
            return {
                "success": False,
                "query": query,
                "action": selected_action,
                "error": "Failed to learn from interaction"
            }
            
    except Exception as e:
        return {
            "success": False,
            "query": query,
            "action": selected_action,
            "error": f"Error learning from interaction: {str(e)}"
        }


if __name__ == "__main__":
    # Test the context resolver tools
    print("=== Context Resolver Tool Test ===")
    
    # Test adding context shortcut
    add_result = add_context_shortcut("test folder", "C:\\Users\\Documents\\Test", "Test folder for documents")
    print(f"\nAdd shortcut result: {add_result}")
    
    # Test listing shortcuts
    shortcuts_result = list_context_shortcuts()
    print(f"\nContext shortcuts: {shortcuts_result}")
    
    # Test query resolution
    resolve_result = resolve_query("open test folder")
    print(f"\nQuery resolution: {resolve_result}")
    
    # Test getting suggestions
    suggestions_result = get_context_suggestions("open")
    print(f"\nContext suggestions: {suggestions_result}")
    
    # Test preferences
    preferences_result = get_user_preferences()
    print(f"\nUser preferences: {preferences_result}")
    
    # Clean up test shortcut
    remove_result = remove_context_shortcut("test folder")
    print(f"\nRemove shortcut result: {remove_result}")