from langchain.tools import tool
import sys
import os

try:
    from modules.session.session_manager import get_session_manager
    SESSION_AVAILABLE = True
except ImportError:
    SESSION_AVAILABLE = False


@tool
def save_current_session(session_name: str) -> str:
    """Save the current work session including open applications, windows, and files. Requires session_name as input."""
    if not SESSION_AVAILABLE:
        return "Session management not available. Module not found."
        
    try:
        manager = get_session_manager()
        success = manager.save_session(session_name)
        
        if success:
            return f"Session '{session_name}' saved successfully with current applications and windows."
        else:
            return f"Failed to save session '{session_name}'. Please try again."
            
    except Exception as e:
        return f"Error saving session: {str(e)}"


@tool
def restore_session(session_name: str) -> str:
    """Restore a previously saved work session by name. This will launch applications and restore windows."""
    if not SESSION_AVAILABLE:
        return "Session management not available. Module not found."
        
    try:
        manager = get_session_manager()
        success = manager.restore_session(session_name)
        
        if success:
            return f"Session '{session_name}' restored successfully. Applications and windows are being restored."
        else:
            return f"Failed to restore session '{session_name}'. Session may not exist or applications may not be available."
            
    except Exception as e:
        return f"Error restoring session: {str(e)}"


@tool
def list_available_sessions() -> str:
    """List all available saved sessions with their details. No input required."""
    if not SESSION_AVAILABLE:
        return "Session management not available. Module not found."
        
    try:
        manager = get_session_manager()
        sessions = manager.list_sessions()
        
        if not sessions:
            return "No saved sessions found. Use save_current_session to create one."
        
        result = "Available sessions:\n"
        for session in sessions:
            result += f"- {session['name']}: {session['app_count']} apps, saved on {session['datetime'][:10]}\n"
        
        return result
        
    except Exception as e:
        return f"Error listing sessions: {str(e)}"


@tool
def setup_workspace(workspace_name: str) -> str:
    """Set up a predefined workspace template. Available: coding_workspace, meeting_workspace, daily_workspace."""
    if not SESSION_AVAILABLE:
        return "Session management not available. Module not found."
        
    try:
        manager = get_session_manager()
        
        # First try to set up existing workspace
        success = manager.setup_workspace(workspace_name)
        
        if success:
            return f"Workspace '{workspace_name}' set up successfully."
        else:
            available_templates = ["coding_workspace", "meeting_workspace", "daily_workspace"]
            return f"Workspace '{workspace_name}' not found. Available workspaces: {', '.join(available_templates)}."
            
    except Exception as e:
        return f"Error setting up workspace: {str(e)}"