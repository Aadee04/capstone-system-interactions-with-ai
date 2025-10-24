#!/usr/bin/env python3
"""
System Suggestions Tool
Tool to access proactive system suggestions and health monitoring
"""

from typing import Dict, List, Any, Optional
from modules.suggestions.proactive_suggestions import get_suggestion_engine
from langchain.tools import tool


def get_system_suggestions(priority_filter: Optional[str] = None) -> Dict[str, Any]:
    """
    Get current system suggestions
    
    Args:
        priority_filter (str): Optional filter by priority ('high', 'medium', 'low')
        
    Returns:
        Dict: System suggestions with metadata
    """
    try:
        suggestion_engine = get_suggestion_engine()
        
        # Run health check first to get latest suggestions
        suggestions = suggestion_engine.run_health_check()
        
        # Filter by priority if specified
        if priority_filter:
            suggestions = [s for s in suggestions if s.priority == priority_filter.lower()]
        
        # Format suggestions for user display
        formatted_suggestions = []
        for suggestion in suggestions:
            if not suggestion.dismissed:
                formatted_suggestion = {
                    'id': suggestion.id,
                    'type': suggestion.type,
                    'priority': suggestion.priority,
                    'title': suggestion.title,
                    'description': suggestion.description,
                    'action_type': suggestion.action_type,
                    'estimated_impact': suggestion.estimated_impact,
                    'can_execute': suggestion.action_type == 'automated' and suggestion.action_command is not None
                }
                formatted_suggestions.append(formatted_suggestion)
        
        return {
            "success": True,
            "suggestions": formatted_suggestions,
            "count": len(formatted_suggestions),
            "priority_filter": priority_filter,
            "message": f"Found {len(formatted_suggestions)} active suggestions" + 
                      (f" with {priority_filter} priority" if priority_filter else "")
        }
        
    except Exception as e:
        return {
            "success": False,
            "suggestions": [],
            "count": 0,
            "priority_filter": priority_filter,
            "error": f"Error getting system suggestions: {str(e)}"
        }


def dismiss_suggestion(suggestion_id: str) -> Dict[str, Any]:
    """
    Dismiss a system suggestion
    
    Args:
        suggestion_id (str): ID of the suggestion to dismiss
        
    Returns:
        Dict: Operation result with success status
    """
    try:
        suggestion_engine = get_suggestion_engine()
        success = suggestion_engine.dismiss_suggestion(suggestion_id)
        
        if success:
            return {
                "success": True,
                "suggestion_id": suggestion_id,
                "message": f"Suggestion '{suggestion_id}' dismissed successfully"
            }
        else:
            return {
                "success": False,
                "suggestion_id": suggestion_id,
                "error": f"Suggestion '{suggestion_id}' not found or already dismissed"
            }
            
    except Exception as e:
        return {
            "success": False,
            "suggestion_id": suggestion_id,
            "error": f"Error dismissing suggestion: {str(e)}"
        }


def execute_automated_suggestion(suggestion_id: str) -> Dict[str, Any]:
    """
    Execute an automated suggestion
    
    Args:
        suggestion_id (str): ID of the automated suggestion to execute
        
    Returns:
        Dict: Execution result with success status
    """
    try:
        suggestion_engine = get_suggestion_engine()
        success = suggestion_engine.execute_automated_suggestion(suggestion_id)
        
        if success:
            return {
                "success": True,
                "suggestion_id": suggestion_id,
                "message": f"Automated suggestion '{suggestion_id}' executed successfully"
            }
        else:
            return {
                "success": False,
                "suggestion_id": suggestion_id,
                "error": f"Cannot execute suggestion '{suggestion_id}'. It may not be automated or may not exist."
            }
            
    except Exception as e:
        return {
            "success": False,
            "suggestion_id": suggestion_id,
            "error": f"Error executing automated suggestion: {str(e)}"
        }


def run_health_check() -> Dict[str, Any]:
    """
    Run a comprehensive system health check
    
    Returns:
        Dict: Health check results and new suggestions
    """
    try:
        suggestion_engine = get_suggestion_engine()
        suggestions = suggestion_engine.run_health_check()
        
        # Categorize suggestions by type and priority
        by_priority = {'high': 0, 'medium': 0, 'low': 0}
        by_type = {'optimization': 0, 'maintenance': 0, 'workflow': 0, 'security': 0}
        
        for suggestion in suggestions:
            if not suggestion.dismissed:
                by_priority[suggestion.priority] = by_priority.get(suggestion.priority, 0) + 1
                by_type[suggestion.type] = by_type.get(suggestion.type, 0) + 1
        
        total_active = sum(by_priority.values())
        
        return {
            "success": True,
            "total_suggestions": total_active,
            "by_priority": by_priority,
            "by_type": by_type,
            "high_priority_count": by_priority['high'],
            "automated_available": len([s for s in suggestions if s.action_type == 'automated' and not s.dismissed]),
            "message": f"Health check complete: {total_active} suggestions found"
        }
        
    except Exception as e:
        return {
            "success": False,
            "total_suggestions": 0,
            "by_priority": {'high': 0, 'medium': 0, 'low': 0},
            "by_type": {'optimization': 0, 'maintenance': 0, 'workflow': 0, 'security': 0},
            "high_priority_count": 0,
            "automated_available": 0,
            "error": f"Error running health check: {str(e)}"
        }


def get_suggestions_summary() -> Dict[str, Any]:
    """
    Get a summary of the suggestions system status
    
    Returns:
        Dict: System summary with statistics
    """
    try:
        suggestion_engine = get_suggestion_engine()
        summary = suggestion_engine.get_suggestions_summary()
        
        return {
            "success": True,
            "summary": summary,
            "message": "Retrieved suggestions system summary successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "summary": {},
            "error": f"Error getting suggestions summary: {str(e)}"
        }


def get_suggestions_by_type(suggestion_type: str) -> Dict[str, Any]:
    """
    Get suggestions filtered by type
    
    Args:
        suggestion_type (str): Type of suggestions ('optimization', 'maintenance', 'workflow', 'security')
        
    Returns:
        Dict: Filtered suggestions by type
    """
    try:
        suggestion_engine = get_suggestion_engine()
        suggestions = suggestion_engine.run_health_check()
        
        # Filter by type
        filtered_suggestions = [s for s in suggestions if s.type == suggestion_type.lower() and not s.dismissed]
        
        # Format for display
        formatted_suggestions = []
        for suggestion in filtered_suggestions:
            formatted_suggestion = {
                'id': suggestion.id,
                'priority': suggestion.priority,
                'title': suggestion.title,
                'description': suggestion.description,
                'action_type': suggestion.action_type,
                'estimated_impact': suggestion.estimated_impact
            }
            formatted_suggestions.append(formatted_suggestion)
        
        return {
            "success": True,
            "type": suggestion_type,
            "suggestions": formatted_suggestions,
            "count": len(formatted_suggestions),
            "message": f"Found {len(formatted_suggestions)} {suggestion_type} suggestions"
        }
        
    except Exception as e:
        return {
            "success": False,
            "type": suggestion_type,
            "suggestions": [],
            "count": 0,
            "error": f"Error getting {suggestion_type} suggestions: {str(e)}"
        }


def get_actionable_suggestions() -> Dict[str, Any]:
    """
    Get suggestions that can be automatically executed
    
    Returns:
        Dict: Automated suggestions that can be executed
    """
    try:
        suggestion_engine = get_suggestion_engine()
        suggestions = suggestion_engine.run_health_check()
        
        # Filter for automated suggestions
        actionable_suggestions = [s for s in suggestions if s.action_type == 'automated' and not s.dismissed]
        
        # Format for display
        formatted_suggestions = []
        for suggestion in actionable_suggestions:
            formatted_suggestion = {
                'id': suggestion.id,
                'type': suggestion.type,
                'priority': suggestion.priority,
                'title': suggestion.title,
                'description': suggestion.description,
                'estimated_impact': suggestion.estimated_impact,
                'action_command': suggestion.action_command
            }
            formatted_suggestions.append(formatted_suggestion)
        
        return {
            "success": True,
            "suggestions": formatted_suggestions,
            "count": len(formatted_suggestions),
            "message": f"Found {len(formatted_suggestions)} actionable suggestions"
        }
        
    except Exception as e:
        return {
            "success": False,
            "suggestions": [],
            "count": 0,
            "error": f"Error getting actionable suggestions: {str(e)}"
        }


if __name__ == "__main__":
    # Test the system suggestions tools
    print("=== System Suggestions Tool Test ===")
    
    # Test running health check
    health_result = run_health_check()
    print(f"\nHealth check result: {health_result}")
    
    # Test getting all suggestions
    all_suggestions = get_system_suggestions()
    print(f"\nAll suggestions: {all_suggestions}")
    
    # Test getting high priority suggestions
    high_priority = get_system_suggestions("high")
    print(f"\nHigh priority suggestions: {high_priority}")
    
    # Test getting suggestions by type
    maintenance_suggestions = get_suggestions_by_type("maintenance")
    print(f"\nMaintenance suggestions: {maintenance_suggestions}")
    
    # Test getting actionable suggestions
    actionable = get_actionable_suggestions()
    print(f"\nActionable suggestions: {actionable}")
    
    # Test system summary
    summary = get_suggestions_summary()
    print(f"\nSystem summary: {summary}")
    
    # Test dismissing a suggestion (if any exist)
    if all_suggestions['success'] and all_suggestions['count'] > 0:
        first_suggestion_id = all_suggestions['suggestions'][0]['id']
        dismiss_result = dismiss_suggestion(first_suggestion_id)
        print(f"\nDismiss result: {dismiss_result}")