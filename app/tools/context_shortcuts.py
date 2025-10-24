from langchain.tools import tool
import sys
import os

try:
    from modules.shortcuts.smart_shortcuts import get_shortcuts_manager
    SHORTCUTS_AVAILABLE = True
except ImportError:
    SHORTCUTS_AVAILABLE = False


@tool
def execute_shortcut(shortcut_name: str) -> str:
    """Execute a saved workflow shortcut by name. This will run all actions in the shortcut sequence."""
    if not SHORTCUTS_AVAILABLE:
        return "Smart shortcuts not available. Module not found."
        
    try:
        manager = get_shortcuts_manager()
        success = manager.execute_shortcut(shortcut_name)
        
        if success:
            return f"Shortcut '{shortcut_name}' executed successfully. All actions completed."
        else:
            return f"Failed to execute shortcut '{shortcut_name}'. Shortcut may not exist or some actions failed."
            
    except Exception as e:
        return f"Error executing shortcut: {str(e)}"


@tool
def list_shortcuts() -> str:
    """List all available workflow shortcuts with their descriptions. No input required."""
    if not SHORTCUTS_AVAILABLE:
        return "Smart shortcuts not available. Module not found."
        
    try:
        manager = get_shortcuts_manager()
        shortcuts = manager.list_shortcuts()
        
        if not shortcuts:
            return "No shortcuts found. Use create_shortcut_from_template to create one."
        
        result = "Available shortcuts:\n"
        for shortcut in shortcuts:
            result += f"- {shortcut['name']}: {shortcut['description']} ({shortcut['action_count']} actions)\n"
        
        return result
        
    except Exception as e:
        return f"Error listing shortcuts: {str(e)}"


@tool
def create_shortcut_from_template(shortcut_name: str, template_type: str) -> str:
    """Create a new shortcut from a template. Available templates: coding_setup, meeting_prep, daily_startup."""
    if not SHORTCUTS_AVAILABLE:
        return "Smart shortcuts not available. Module not found."
        
    try:
        manager = get_shortcuts_manager()
        success = manager.create_shortcut_from_template(shortcut_name, template_type)
        
        if success:
            return f"Shortcut '{shortcut_name}' created successfully from template '{template_type}'."
        else:
            available_templates = ["coding_setup", "meeting_prep", "daily_startup"]
            return f"Failed to create shortcut. Available templates: {', '.join(available_templates)}"
            
    except Exception as e:
        return f"Error creating shortcut: {str(e)}"


@tool
def get_shortcut_templates() -> str:
    """Get available shortcut templates that can be used to create new shortcuts. No input required."""
    try:
        templates = {
            "coding_setup": "Set up coding environment (VS Code, Chrome, Projects folder)",
            "meeting_prep": "Prepare for meetings (Teams, Notepad, Meetings folder)", 
            "daily_startup": "Daily work startup routine (Outlook, Chrome, Slack)"
        }
        
        result = "Available shortcut templates:\n"
        for template, description in templates.items():
            result += f"- {template}: {description}\n"
        
        return result
        
    except Exception as e:
        return f"Error getting templates: {str(e)}"