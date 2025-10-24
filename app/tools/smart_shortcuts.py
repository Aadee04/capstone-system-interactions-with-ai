#!/usr/bin/env python3
"""
Smart Shortcuts Tool
Tool to create, execute, and manage workflow shortcuts
"""

from typing import Dict, List, Any, Optional
from modules.shortcuts.smart_shortcuts import get_shortcuts_manager
from langchain.tools import tool


def execute_shortcut(shortcut_name: str, dry_run: bool = False) -> Dict[str, Any]:
    """
    Execute a saved shortcut workflow
    
    Args:
        shortcut_name (str): Name of the shortcut to execute
        dry_run (bool): If True, only show what would be executed
        
    Returns:
        Dict: Execution result with success status
    """
    try:
        shortcuts_manager = get_shortcuts_manager()
        success = shortcuts_manager.execute_shortcut(shortcut_name, dry_run)
        
        if success:
            return {
                "success": True,
                "shortcut_name": shortcut_name,
                "dry_run": dry_run,
                "message": f"Shortcut '{shortcut_name}' {'previewed' if dry_run else 'executed'} successfully"
            }
        else:
            return {
                "success": False,
                "shortcut_name": shortcut_name,
                "dry_run": dry_run,
                "error": f"Failed to {'preview' if dry_run else 'execute'} shortcut '{shortcut_name}'. It may not exist."
            }
            
    except Exception as e:
        return {
            "success": False,
            "shortcut_name": shortcut_name,
            "dry_run": dry_run,
            "error": f"Error {'previewing' if dry_run else 'executing'} shortcut: {str(e)}"
        }


def list_shortcuts() -> Dict[str, Any]:
    """
    List all available shortcuts
    
    Returns:
        Dict: List of shortcuts with metadata
    """
    try:
        shortcuts_manager = get_shortcuts_manager()
        shortcuts = shortcuts_manager.list_shortcuts()
        
        # Format shortcuts for user display
        formatted_shortcuts = []
        for shortcut in shortcuts:
            formatted_shortcut = {
                'name': shortcut['name'],
                'description': shortcut['description'],
                'actions': shortcut['action_count'],
                'created': shortcut['datetime'],
                'type': shortcut.get('template_type', 'custom')
            }
            formatted_shortcuts.append(formatted_shortcut)
        
        return {
            "success": True,
            "shortcuts": formatted_shortcuts,
            "count": len(formatted_shortcuts),
            "message": f"Found {len(formatted_shortcuts)} available shortcuts"
        }
        
    except Exception as e:
        return {
            "success": False,
            "shortcuts": [],
            "count": 0,
            "error": f"Error listing shortcuts: {str(e)}"
        }


def create_shortcut_from_template(shortcut_name: str, template_type: str) -> Dict[str, Any]:
    """
    Create a shortcut from a predefined template
    
    Args:
        shortcut_name (str): Name for the new shortcut
        template_type (str): Type of template ('coding_setup', 'meeting_prep', 'daily_startup')
        
    Returns:
        Dict: Creation result with success status
    """
    try:
        shortcuts_manager = get_shortcuts_manager()
        success = shortcuts_manager.create_shortcut_from_template(shortcut_name, template_type)
        
        if success:
            return {
                "success": True,
                "shortcut_name": shortcut_name,
                "template_type": template_type,
                "message": f"Shortcut '{shortcut_name}' created from template '{template_type}'"
            }
        else:
            return {
                "success": False,
                "shortcut_name": shortcut_name,
                "template_type": template_type,
                "error": f"Failed to create shortcut from template '{template_type}'. Template may not exist."
            }
            
    except Exception as e:
        return {
            "success": False,
            "shortcut_name": shortcut_name,
            "template_type": template_type,
            "error": f"Error creating shortcut from template: {str(e)}"
        }


def start_recording_shortcut(shortcut_name: str, description: str = "") -> Dict[str, Any]:
    """
    Start recording a new shortcut
    
    Args:
        shortcut_name (str): Name for the shortcut being recorded
        description (str): Description of what the shortcut does
        
    Returns:
        Dict: Recording start result with success status
    """
    try:
        shortcuts_manager = get_shortcuts_manager()
        success = shortcuts_manager.start_recording(shortcut_name, description)
        
        if success:
            return {
                "success": True,
                "shortcut_name": shortcut_name,
                "description": description,
                "message": f"Started recording shortcut '{shortcut_name}'. Use record_action to add steps."
            }
        else:
            return {
                "success": False,
                "shortcut_name": shortcut_name,
                "description": description,
                "error": f"Failed to start recording. Another recording may be in progress."
            }
            
    except Exception as e:
        return {
            "success": False,
            "shortcut_name": shortcut_name,
            "description": description,
            "error": f"Error starting shortcut recording: {str(e)}"
        }


def record_action(action_type: str, target: str, delay_after: float = 1.0) -> Dict[str, Any]:
    """
    Record an action in the current shortcut recording
    
    Args:
        action_type (str): Type of action ('open_app', 'open_file', 'open_folder', 'run_command', 'wait')
        target (str): Target of the action (app name, file path, command, etc.)
        delay_after (float): Delay after this action in seconds
        
    Returns:
        Dict: Action recording result with success status
    """
    try:
        shortcuts_manager = get_shortcuts_manager()
        success = shortcuts_manager.record_action(action_type, target, delay_after=delay_after)
        
        if success:
            return {
                "success": True,
                "action_type": action_type,
                "target": target,
                "delay_after": delay_after,
                "message": f"Recorded action: {action_type} -> {target}"
            }
        else:
            return {
                "success": False,
                "action_type": action_type,
                "target": target,
                "delay_after": delay_after,
                "error": f"Failed to record action. No recording in progress or unknown action type."
            }
            
    except Exception as e:
        return {
            "success": False,
            "action_type": action_type,
            "target": target,
            "delay_after": delay_after,
            "error": f"Error recording action: {str(e)}"
        }


def stop_recording_shortcut() -> Dict[str, Any]:
    """
    Stop recording and save the current shortcut
    
    Returns:
        Dict: Recording stop result with success status
    """
    try:
        shortcuts_manager = get_shortcuts_manager()
        success = shortcuts_manager.stop_recording()
        
        if success:
            return {
                "success": True,
                "message": "Shortcut recording stopped and saved successfully"
            }
        else:
            return {
                "success": False,
                "error": "Failed to stop recording. No recording in progress or no actions recorded."
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Error stopping shortcut recording: {str(e)}"
        }


def delete_shortcut(shortcut_name: str) -> Dict[str, Any]:
    """
    Delete a shortcut
    
    Args:
        shortcut_name (str): Name of the shortcut to delete
        
    Returns:
        Dict: Deletion result with success status
    """
    try:
        shortcuts_manager = get_shortcuts_manager()
        success = shortcuts_manager.delete_shortcut(shortcut_name)
        
        if success:
            return {
                "success": True,
                "shortcut_name": shortcut_name,
                "message": f"Shortcut '{shortcut_name}' deleted successfully"
            }
        else:
            return {
                "success": False,
                "shortcut_name": shortcut_name,
                "error": f"Shortcut '{shortcut_name}' not found or could not be deleted"
            }
            
    except Exception as e:
        return {
            "success": False,
            "shortcut_name": shortcut_name,
            "error": f"Error deleting shortcut: {str(e)}"
        }


def get_available_templates() -> Dict[str, Any]:
    """
    Get list of available shortcut templates
    
    Returns:
        Dict: Available templates
    """
    try:
        shortcuts_manager = get_shortcuts_manager()
        summary = shortcuts_manager.get_shortcuts_summary()
        
        templates = {
            'coding_setup': {
                'name': 'Coding Setup',
                'description': 'Set up development environment with code editor, browser, and project folder'
            },
            'meeting_prep': {
                'name': 'Meeting Preparation',
                'description': 'Launch Teams, note-taking app, and meeting documents folder'
            },
            'daily_startup': {
                'name': 'Daily Startup',
                'description': 'Launch email, browser, and communication apps for daily work'
            }
        }
        
        return {
            "success": True,
            "templates": templates,
            "count": len(templates),
            "message": f"Found {len(templates)} available templates"
        }
        
    except Exception as e:
        return {
            "success": False,
            "templates": {},
            "count": 0,
            "error": f"Error getting templates: {str(e)}"
        }


if __name__ == "__main__":
    # Test the shortcuts tools
    print("=== Smart Shortcuts Tool Test ===")
    
    # Test listing shortcuts
    result = list_shortcuts()
    print(f"\nCurrent shortcuts: {result}")
    
    # Test getting templates
    templates = get_available_templates()
    print(f"\nAvailable templates: {templates}")
    
    # Test creating shortcut from template
    create_result = create_shortcut_from_template("my_coding_setup", "coding_setup")
    print(f"\nCreate from template result: {create_result}")
    
    # Test dry run execution
    if result['success'] and result['count'] > 0:
        first_shortcut = result['shortcuts'][0]['name']
        dry_run_result = execute_shortcut(first_shortcut, dry_run=True)
        print(f"\nDry run result: {dry_run_result}")
    
    # Test recording workflow
    record_start = start_recording_shortcut("test_shortcut", "Test recording workflow")
    print(f"\nStart recording: {record_start}")
    
    if record_start['success']:
        action1 = record_action("open_app", "notepad.exe")
        print(f"Record action 1: {action1}")
        
        action2 = record_action("wait", "2", 2.0)
        print(f"Record action 2: {action2}")
        
        stop_result = stop_recording_shortcut()
        print(f"Stop recording: {stop_result}")