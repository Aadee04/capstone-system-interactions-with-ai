#!/usr/bin/env python3
"""
Session Manager Tool
Tool to save, restore, and manage work sessions
"""

from typing import Dict, List, Any, Optional
from modules.session.session_manager import get_session_manager
from langchain.tools import tool


def save_current_session(session_name: str) -> Dict[str, Any]:
    """
    Save the current work session
    
    Args:
        session_name (str): Name for the session
        
    Returns:
        Dict: Operation result with success status and details
    """
    try:
        session_manager = get_session_manager()
        success = session_manager.save_session(session_name)
        
        if success:
            return {
                "success": True,
                "session_name": session_name,
                "message": f"Session '{session_name}' saved successfully"
            }
        else:
            return {
                "success": False,
                "session_name": session_name,
                "error": f"Failed to save session '{session_name}'"
            }
            
    except Exception as e:
        return {
            "success": False,
            "session_name": session_name,
            "error": f"Error saving session: {str(e)}"
        }


def restore_session(session_name: str, selective: bool = False) -> Dict[str, Any]:
    """
    Restore a previously saved session
    
    Args:
        session_name (str): Name of the session to restore
        selective (bool): If True, only restore applications marked as restorable
        
    Returns:
        Dict: Operation result with success status and details
    """
    try:
        session_manager = get_session_manager()
        success = session_manager.restore_session(session_name, selective)
        
        if success:
            return {
                "success": True,
                "session_name": session_name,
                "selective": selective,
                "message": f"Session '{session_name}' restored successfully" +
                          (" (selective restore)" if selective else "")
            }
        else:
            return {
                "success": False,
                "session_name": session_name,
                "selective": selective,
                "error": f"Failed to restore session '{session_name}'. Session may not exist."
            }
            
    except Exception as e:
        return {
            "success": False,
            "session_name": session_name,
            "selective": selective,
            "error": f"Error restoring session: {str(e)}"
        }


def list_sessions() -> Dict[str, Any]:
    """
    List all available saved sessions
    
    Returns:
        Dict: List of available sessions with metadata
    """
    try:
        session_manager = get_session_manager()
        sessions = session_manager.list_sessions()
        
        # Format sessions for user display
        formatted_sessions = []
        for session in sessions:
            formatted_session = {
                'name': session['name'],
                'created': session['datetime'],
                'apps': session['app_count'],
                'files': session['file_count']
            }
            formatted_sessions.append(formatted_session)
        
        return {
            "success": True,
            "sessions": formatted_sessions,
            "count": len(formatted_sessions),
            "message": f"Found {len(formatted_sessions)} saved sessions"
        }
        
    except Exception as e:
        return {
            "success": False,
            "sessions": [],
            "count": 0,
            "error": f"Error listing sessions: {str(e)}"
        }


def delete_session(session_name: str) -> Dict[str, Any]:
    """
    Delete a saved session
    
    Args:
        session_name (str): Name of the session to delete
        
    Returns:
        Dict: Operation result with success status
    """
    try:
        session_manager = get_session_manager()
        success = session_manager.delete_session(session_name)
        
        if success:
            return {
                "success": True,
                "session_name": session_name,
                "message": f"Session '{session_name}' deleted successfully"
            }
        else:
            return {
                "success": False,
                "session_name": session_name,
                "error": f"Session '{session_name}' not found or could not be deleted"
            }
            
    except Exception as e:
        return {
            "success": False,
            "session_name": session_name,
            "error": f"Error deleting session: {str(e)}"
        }


def create_workspace_template(workspace_name: str, 
                           applications: List[str],
                           folders: List[str] = None,
                           files: List[str] = None) -> Dict[str, Any]:
    """
    Create a workspace template for quick setup
    
    Args:
        workspace_name (str): Name of the workspace
        applications (List[str]): List of applications to launch
        folders (List[str]): List of folders to open
        files (List[str]): List of files to open
        
    Returns:
        Dict: Operation result with success status
    """
    try:
        session_manager = get_session_manager()
        success = session_manager.create_workspace_template(
            workspace_name, applications, folders or [], files or []
        )
        
        if success:
            return {
                "success": True,
                "workspace_name": workspace_name,
                "applications": applications,
                "folders": folders or [],
                "files": files or [],
                "message": f"Workspace template '{workspace_name}' created successfully"
            }
        else:
            return {
                "success": False,
                "workspace_name": workspace_name,
                "error": f"Failed to create workspace template '{workspace_name}'"
            }
            
    except Exception as e:
        return {
            "success": False,
            "workspace_name": workspace_name,
            "error": f"Error creating workspace template: {str(e)}"
        }


def setup_workspace(workspace_name: str) -> Dict[str, Any]:
    """
    Set up a predefined workspace
    
    Args:
        workspace_name (str): Name of workspace to set up
        
    Returns:
        Dict: Operation result with success status
    """
    try:
        session_manager = get_session_manager()
        success = session_manager.setup_workspace(workspace_name)
        
        if success:
            return {
                "success": True,
                "workspace_name": workspace_name,
                "message": f"Workspace '{workspace_name}' setup completed"
            }
        else:
            return {
                "success": False,
                "workspace_name": workspace_name,
                "error": f"Workspace template '{workspace_name}' not found or setup failed"
            }
            
    except Exception as e:
        return {
            "success": False,
            "workspace_name": workspace_name,
            "error": f"Error setting up workspace: {str(e)}"
        }


if __name__ == "__main__":
    # Test the session management tools
    print("=== Session Manager Tool Test ===")
    
    # Test listing sessions
    result = list_sessions()
    print(f"\nCurrent sessions: {result}")
    
    # Test saving current session
    save_result = save_current_session("test_session")
    print(f"\nSave session result: {save_result}")
    
    # Test creating workspace template
    workspace_result = create_workspace_template(
        "test_workspace", 
        ["notepad.exe", "calc.exe"],
        ["C:\\Users\\Documents"],
        []
    )
    print(f"\nWorkspace template result: {workspace_result}")
    
    # Test listing sessions again
    result = list_sessions()
    print(f"\nSessions after save: {result}")