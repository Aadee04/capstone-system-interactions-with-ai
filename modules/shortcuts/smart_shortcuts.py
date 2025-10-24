#!/usr/bin/env python3
"""
Smart Shortcuts System
Allows users to create and execute custom workflows and automation sequences
"""

import json
import time
import subprocess
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from dataclasses import dataclass, asdict

from modules.context.system_state_tracker import get_state_tracker
from modules.session.session_manager import get_session_manager
from modules.visual.visual_verifier import get_visual_verifier


@dataclass
class ShortcutAction:
    """Represents a single action in a shortcut workflow"""
    action_type: str  # 'open_app', 'open_file', 'open_folder', 'run_command', 'wait', 'session_restore'
    target: str       # App name, file path, command, etc.
    parameters: Dict[str, Any] = None  # Additional parameters
    delay_after: float = 1.0  # Delay after this action in seconds
    verify: bool = True  # Whether to verify the action succeeded


class SmartShortcuts:
    """Manages smart shortcuts and workflow automation"""
    
    def __init__(self):
        """Initialize smart shortcuts manager"""
        self.state_tracker = get_state_tracker()
        self.session_manager = get_session_manager()
        self.visual_verifier = get_visual_verifier()
        
        # Shortcut storage
        self.shortcuts_dir = Path("data/shortcuts")
        self.shortcuts_dir.mkdir(parents=True, exist_ok=True)
        
        # Recording state
        self.is_recording = False
        self.current_recording = None
        self.recorded_actions = []
        
        # Action handlers
        self.action_handlers = {
            'open_app': self._handle_open_app,
            'open_file': self._handle_open_file,
            'open_folder': self._handle_open_folder,
            'run_command': self._handle_run_command,
            'wait': self._handle_wait,
            'session_restore': self._handle_session_restore,
            'minimize_all': self._handle_minimize_all,
            'arrange_windows': self._handle_arrange_windows
        }
        
        print("[Smart Shortcuts] Initialized")
    
    def start_recording(self, shortcut_name: str, description: str = "") -> bool:
        """
        Start recording a new shortcut
        
        Args:
            shortcut_name (str): Name for the shortcut
            description (str): Description of what the shortcut does
            
        Returns:
            bool: Success status
        """
        if self.is_recording:
            print(f"[Smart Shortcuts] Already recording '{self.current_recording['name']}'")
            return False
        
        self.is_recording = True
        self.current_recording = {
            'name': shortcut_name,
            'description': description,
            'created_timestamp': time.time(),
            'created_datetime': datetime.now().isoformat(),
            'version': '1.0'
        }
        self.recorded_actions = []
        
        print(f"[Smart Shortcuts] Started recording shortcut '{shortcut_name}'")
        print("Use record_action() to add actions, then stop_recording() to save")
        return True
    
    def record_action(self, action_type: str, target: str, 
                     parameters: Dict[str, Any] = None, 
                     delay_after: float = 1.0,
                     verify: bool = True) -> bool:
        """
        Record an action during shortcut recording
        
        Args:
            action_type (str): Type of action
            target (str): Target of the action
            parameters (Dict): Additional parameters
            delay_after (float): Delay after action
            verify (bool): Whether to verify success
            
        Returns:
            bool: Success status
        """
        if not self.is_recording:
            print("[Smart Shortcuts] Not currently recording. Use start_recording() first.")
            return False
        
        if action_type not in self.action_handlers:
            print(f"[Smart Shortcuts] Unknown action type: {action_type}")
            return False
        
        action = ShortcutAction(
            action_type=action_type,
            target=target,
            parameters=parameters or {},
            delay_after=delay_after,
            verify=verify
        )
        
        self.recorded_actions.append(action)
        print(f"[Smart Shortcuts] Recorded action: {action_type} -> {target}")
        return True
    
    def stop_recording(self) -> bool:
        """
        Stop recording and save the shortcut
        
        Returns:
            bool: Success status
        """
        if not self.is_recording:
            print("[Smart Shortcuts] Not currently recording")
            return False
        
        if not self.recorded_actions:
            print("[Smart Shortcuts] No actions recorded")
            return False
        
        # Build shortcut data
        shortcut_data = self.current_recording.copy()
        shortcut_data['actions'] = [asdict(action) for action in self.recorded_actions]
        shortcut_data['action_count'] = len(self.recorded_actions)
        
        # Save to file
        try:
            shortcut_file = self.shortcuts_dir / f"{shortcut_data['name']}.json"
            with open(shortcut_file, 'w') as f:
                json.dump(shortcut_data, f, indent=2, default=str)
            
            print(f"[Smart Shortcuts] Shortcut '{shortcut_data['name']}' saved with {len(self.recorded_actions)} actions")
            
            # Reset recording state
            self.is_recording = False
            self.current_recording = None
            self.recorded_actions = []
            
            return True
            
        except Exception as e:
            print(f"[Smart Shortcuts] Error saving shortcut: {e}")
            return False
    
    def create_shortcut_from_template(self, shortcut_name: str, template_type: str) -> bool:
        """
        Create a shortcut from a predefined template
        
        Args:
            shortcut_name (str): Name for the shortcut
            template_type (str): Type of template ('coding_setup', 'meeting_prep', etc.)
            
        Returns:
            bool: Success status
        """
        templates = {
            'coding_setup': {
                'description': 'Set up coding environment',
                'actions': [
                    ShortcutAction('open_app', 'code.exe', {'wait_for_load': True}, 2.0),
                    ShortcutAction('open_app', 'chrome.exe', {}, 1.0),
                    ShortcutAction('open_folder', 'C:\\Users\\Documents\\Projects', {}, 1.0),
                    ShortcutAction('arrange_windows', 'side_by_side', {}, 0.5)
                ]
            },
            'meeting_prep': {
                'description': 'Prepare for meetings',
                'actions': [
                    ShortcutAction('open_app', 'Teams.exe', {}, 2.0),
                    ShortcutAction('open_app', 'notepad.exe', {}, 1.0),
                    ShortcutAction('open_folder', 'C:\\Users\\Documents\\Meetings', {}, 1.0),
                    ShortcutAction('minimize_all', '', {}, 0.5)
                ]
            },
            'daily_startup': {
                'description': 'Daily work startup routine',
                'actions': [
                    ShortcutAction('open_app', 'outlook.exe', {}, 2.0),
                    ShortcutAction('open_app', 'chrome.exe', {}, 1.0),
                    ShortcutAction('open_app', 'slack.exe', {}, 1.0),
                    ShortcutAction('wait', '3', {'reason': 'Let apps load'}, 3.0)
                ]
            }
        }
        
        if template_type not in templates:
            print(f"[Smart Shortcuts] Unknown template type: {template_type}")
            print(f"Available templates: {list(templates.keys())}")
            return False
        
        template = templates[template_type]
        
        shortcut_data = {
            'name': shortcut_name,
            'description': template['description'],
            'created_timestamp': time.time(),
            'created_datetime': datetime.now().isoformat(),
            'template_type': template_type,
            'version': '1.0',
            'actions': [asdict(action) for action in template['actions']],
            'action_count': len(template['actions'])
        }
        
        try:
            shortcut_file = self.shortcuts_dir / f"{shortcut_name}.json"
            with open(shortcut_file, 'w') as f:
                json.dump(shortcut_data, f, indent=2, default=str)
            
            print(f"[Smart Shortcuts] Created shortcut '{shortcut_name}' from template '{template_type}'")
            return True
            
        except Exception as e:
            print(f"[Smart Shortcuts] Error creating shortcut from template: {e}")
            return False
    
    def execute_shortcut(self, shortcut_name: str, 
                        dry_run: bool = False,
                        skip_verification: bool = False) -> bool:
        """
        Execute a saved shortcut
        
        Args:
            shortcut_name (str): Name of shortcut to execute
            dry_run (bool): If True, only show what would be done
            skip_verification (bool): Skip visual verification
            
        Returns:
            bool: Success status
        """
        shortcut_data = self.load_shortcut(shortcut_name)
        if not shortcut_data:
            return False
        
        if dry_run:
            print(f"[Smart Shortcuts] DRY RUN for '{shortcut_name}':")
            for i, action_data in enumerate(shortcut_data.get('actions', [])):
                print(f"  {i+1}. {action_data['action_type']} -> {action_data['target']}")
            return True
        
        print(f"[Smart Shortcuts] Executing shortcut '{shortcut_name}'...")
        
        success_count = 0
        total_actions = len(shortcut_data.get('actions', []))
        
        for i, action_data in enumerate(shortcut_data.get('actions', [])):
            try:
                action = ShortcutAction(**action_data)
                print(f"[Smart Shortcuts] [{i+1}/{total_actions}] {action.action_type} -> {action.target}")
                
                # Execute the action
                handler = self.action_handlers.get(action.action_type)
                if handler:
                    if handler(action):
                        success_count += 1
                        
                        # Visual verification if enabled
                        if action.verify and not skip_verification:
                            time.sleep(0.5)  # Brief pause before verification
                            self._verify_action_success(action)
                        
                        # Delay after action
                        if action.delay_after > 0:
                            time.sleep(action.delay_after)
                    else:
                        print(f"[Smart Shortcuts] Action failed: {action.action_type}")
                else:
                    print(f"[Smart Shortcuts] Unknown action type: {action.action_type}")
                    
            except Exception as e:
                print(f"[Smart Shortcuts] Error executing action {i+1}: {e}")
        
        print(f"[Smart Shortcuts] Shortcut execution complete: {success_count}/{total_actions} actions succeeded")
        return success_count > 0
    
    def load_shortcut(self, shortcut_name: str) -> Optional[Dict[str, Any]]:
        """
        Load a shortcut from disk
        
        Args:
            shortcut_name (str): Name of shortcut to load
            
        Returns:
            Dict: Shortcut data or None if not found
        """
        try:
            shortcut_file = self.shortcuts_dir / f"{shortcut_name}.json"
            
            if not shortcut_file.exists():
                print(f"[Smart Shortcuts] Shortcut '{shortcut_name}' not found")
                return None
            
            with open(shortcut_file, 'r') as f:
                shortcut_data = json.load(f)
            
            return shortcut_data
            
        except Exception as e:
            print(f"[Smart Shortcuts] Error loading shortcut '{shortcut_name}': {e}")
            return None
    
    def list_shortcuts(self) -> List[Dict[str, Any]]:
        """
        List all available shortcuts
        
        Returns:
            List: Shortcut information
        """
        shortcuts = []
        
        try:
            for shortcut_file in self.shortcuts_dir.glob("*.json"):
                try:
                    with open(shortcut_file, 'r') as f:
                        shortcut_data = json.load(f)
                    
                    shortcuts.append({
                        'name': shortcut_data.get('name', shortcut_file.stem),
                        'description': shortcut_data.get('description', ''),
                        'file': str(shortcut_file),
                        'timestamp': shortcut_data.get('created_timestamp', 0),
                        'datetime': shortcut_data.get('created_datetime', 'Unknown'),
                        'action_count': shortcut_data.get('action_count', 0),
                        'template_type': shortcut_data.get('template_type', 'custom')
                    })
                    
                except Exception as e:
                    print(f"[Smart Shortcuts] Error reading shortcut {shortcut_file}: {e}")
                    
        except Exception as e:
            print(f"[Smart Shortcuts] Error listing shortcuts: {e}")
        
        # Sort by timestamp (newest first)
        shortcuts.sort(key=lambda x: x['timestamp'], reverse=True)
        return shortcuts
    
    def delete_shortcut(self, shortcut_name: str) -> bool:
        """
        Delete a shortcut
        
        Args:
            shortcut_name (str): Name of shortcut to delete
            
        Returns:
            bool: Success status
        """
        try:
            shortcut_file = self.shortcuts_dir / f"{shortcut_name}.json"
            
            if shortcut_file.exists():
                shortcut_file.unlink()
                print(f"[Smart Shortcuts] Deleted shortcut: {shortcut_name}")
                return True
            else:
                print(f"[Smart Shortcuts] Shortcut not found: {shortcut_name}")
                return False
                
        except Exception as e:
            print(f"[Smart Shortcuts] Error deleting shortcut '{shortcut_name}': {e}")
            return False
    
    # Action handlers
    def _handle_open_app(self, action: ShortcutAction) -> bool:
        """Handle opening an application"""
        try:
            # Try different ways to launch the app
            app_name = action.target
            
            # Method 1: Direct executable launch
            if app_name.endswith('.exe'):
                subprocess.Popen([app_name], shell=False)
            else:
                # Method 2: Shell launch (for apps in PATH)
                subprocess.Popen([app_name], shell=True)
            
            print(f"[Smart Shortcuts] Launched application: {app_name}")
            
            # Wait for app to load if specified
            if action.parameters.get('wait_for_load', False):
                time.sleep(2)
            
            return True
            
        except Exception as e:
            print(f"[Smart Shortcuts] Error launching app '{action.target}': {e}")
            return False
    
    def _handle_open_file(self, action: ShortcutAction) -> bool:
        """Handle opening a file"""
        try:
            file_path = action.target
            
            if not os.path.exists(file_path):
                print(f"[Smart Shortcuts] File not found: {file_path}")
                return False
            
            # Use Windows start command to open with default app
            subprocess.Popen(['start', '', file_path], shell=True)
            print(f"[Smart Shortcuts] Opened file: {file_path}")
            return True
            
        except Exception as e:
            print(f"[Smart Shortcuts] Error opening file '{action.target}': {e}")
            return False
    
    def _handle_open_folder(self, action: ShortcutAction) -> bool:
        """Handle opening a folder"""
        try:
            folder_path = action.target
            
            if not os.path.exists(folder_path):
                print(f"[Smart Shortcuts] Folder not found: {folder_path}")
                return False
            
            subprocess.Popen(['explorer', folder_path], shell=False)
            print(f"[Smart Shortcuts] Opened folder: {folder_path}")
            return True
            
        except Exception as e:
            print(f"[Smart Shortcuts] Error opening folder '{action.target}': {e}")
            return False
    
    def _handle_run_command(self, action: ShortcutAction) -> bool:
        """Handle running a command"""
        try:
            command = action.target
            
            # Run command
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"[Smart Shortcuts] Command executed successfully: {command}")
                if result.stdout:
                    print(f"Output: {result.stdout.strip()}")
                return True
            else:
                print(f"[Smart Shortcuts] Command failed: {command}")
                if result.stderr:
                    print(f"Error: {result.stderr.strip()}")
                return False
                
        except Exception as e:
            print(f"[Smart Shortcuts] Error running command '{action.target}': {e}")
            return False
    
    def _handle_wait(self, action: ShortcutAction) -> bool:
        """Handle waiting"""
        try:
            wait_time = float(action.target)
            reason = action.parameters.get('reason', 'Waiting')
            
            print(f"[Smart Shortcuts] {reason} ({wait_time}s)...")
            time.sleep(wait_time)
            return True
            
        except Exception as e:
            print(f"[Smart Shortcuts] Error in wait action: {e}")
            return False
    
    def _handle_session_restore(self, action: ShortcutAction) -> bool:
        """Handle session restoration"""
        try:
            session_name = action.target
            success = self.session_manager.restore_session(session_name)
            
            if success:
                print(f"[Smart Shortcuts] Restored session: {session_name}")
            else:
                print(f"[Smart Shortcuts] Failed to restore session: {session_name}")
            
            return success
            
        except Exception as e:
            print(f"[Smart Shortcuts] Error restoring session '{action.target}': {e}")
            return False
    
    def _handle_minimize_all(self, action: ShortcutAction) -> bool:
        """Handle minimizing all windows"""
        try:
            # Use Windows hotkey to minimize all
            import win32api
            import win32con
            
            # Send Win+M to minimize all windows
            win32api.keybd_event(win32con.VK_LWIN, 0, 0, 0)
            win32api.keybd_event(0x4D, 0, 0, 0)  # M key
            win32api.keybd_event(0x4D, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_LWIN, 0, win32con.KEYEVENTF_KEYUP, 0)
            
            print("[Smart Shortcuts] Minimized all windows")
            return True
            
        except Exception as e:
            print(f"[Smart Shortcuts] Error minimizing all windows: {e}")
            return False
    
    def _handle_arrange_windows(self, action: ShortcutAction) -> bool:
        """Handle window arrangement"""
        try:
            arrangement = action.target
            
            if arrangement == 'side_by_side':
                # Use Windows hotkey for side-by-side arrangement
                import win32api
                import win32con
                
                # Send Win+Left then Win+Right
                win32api.keybd_event(win32con.VK_LWIN, 0, 0, 0)
                win32api.keybd_event(win32con.VK_LEFT, 0, 0, 0)
                win32api.keybd_event(win32con.VK_LEFT, 0, win32con.KEYEVENTF_KEYUP, 0)
                win32api.keybd_event(win32con.VK_LWIN, 0, win32con.KEYEVENTF_KEYUP, 0)
                
                time.sleep(0.5)
                
                win32api.keybd_event(win32con.VK_LWIN, 0, 0, 0)
                win32api.keybd_event(win32con.VK_RIGHT, 0, 0, 0)
                win32api.keybd_event(win32con.VK_RIGHT, 0, win32con.KEYEVENTF_KEYUP, 0)
                win32api.keybd_event(win32con.VK_LWIN, 0, win32con.KEYEVENTF_KEYUP, 0)
                
                print("[Smart Shortcuts] Arranged windows side by side")
                return True
                
            print(f"[Smart Shortcuts] Unknown arrangement: {arrangement}")
            return False
            
        except Exception as e:
            print(f"[Smart Shortcuts] Error arranging windows: {e}")
            return False
    
    def _verify_action_success(self, action: ShortcutAction) -> bool:
        """Verify that an action was successful using visual verification"""
        try:
            if action.action_type == 'open_app':
                app_name = action.target.replace('.exe', '')
                return self.visual_verifier.verify_application_opened(app_name)
            elif action.action_type == 'open_file':
                filename = os.path.basename(action.target)
                return self.visual_verifier.verify_file_opened(filename)
            elif action.action_type == 'open_folder':
                folder_name = os.path.basename(action.target)
                return self.visual_verifier.verify_folder_opened(folder_name)
            
            # For other action types, assume success if no errors
            return True
            
        except Exception as e:
            print(f"[Smart Shortcuts] Verification error: {e}")
            return False
    
    def get_shortcuts_summary(self) -> Dict[str, Any]:
        """Get summary of shortcuts system"""
        shortcuts = self.list_shortcuts()
        
        return {
            'total_shortcuts': len(shortcuts),
            'shortcuts_directory': str(self.shortcuts_dir),
            'recent_shortcuts': shortcuts[:5],  # Last 5 shortcuts
            'is_recording': self.is_recording,
            'current_recording': self.current_recording,
            'available_templates': ['coding_setup', 'meeting_prep', 'daily_startup']
        }


# Global shortcuts manager instance
_shortcuts_manager = None

def get_shortcuts_manager():
    """Get the global shortcuts manager instance"""
    global _shortcuts_manager
    if _shortcuts_manager is None:
        _shortcuts_manager = SmartShortcuts()
    return _shortcuts_manager

def execute_shortcut(shortcut_name):
    """Convenience function to execute shortcut"""
    manager = get_shortcuts_manager()
    return manager.execute_shortcut(shortcut_name)

def create_shortcut_from_template(shortcut_name, template_type):
    """Convenience function to create shortcut from template"""
    manager = get_shortcuts_manager()
    return manager.create_shortcut_from_template(shortcut_name, template_type)

def list_available_shortcuts():
    """Convenience function to list shortcuts"""
    manager = get_shortcuts_manager()
    return manager.list_shortcuts()

# Test functionality
if __name__ == "__main__":
    print("=== Smart Shortcuts Test ===")
    
    manager = SmartShortcuts()
    
    # Test template creation
    print("\n1. Testing template creation:")
    success = manager.create_shortcut_from_template("test_coding", "coding_setup")
    print(f"Template shortcut created: {success}")
    
    # Test shortcut listing
    print("\n2. Testing shortcut listing:")
    shortcuts = manager.list_shortcuts()
    print(f"Found {len(shortcuts)} shortcuts:")
    for shortcut in shortcuts:
        print(f"  - {shortcut['name']}: {shortcut['description']} ({shortcut['action_count']} actions)")
    
    # Test recording workflow
    print("\n3. Testing recording workflow:")
    manager.start_recording("test_manual", "Manual test shortcut")
    manager.record_action("open_app", "notepad.exe")
    manager.record_action("wait", "2", {"reason": "Let notepad load"})
    manager.record_action("open_folder", "C:\\Users\\Documents")
    success = manager.stop_recording()
    print(f"Manual shortcut recorded: {success}")
    
    # Test dry run
    print("\n4. Testing dry run:")
    if shortcuts:
        shortcut_name = shortcuts[0]['name']
        print(f"Dry run for '{shortcut_name}':")
        manager.execute_shortcut(shortcut_name, dry_run=True)
    
    # Test system summary
    print("\n5. Testing system summary:")
    summary = manager.get_shortcuts_summary()
    print(f"Summary: {summary}")
    
    print("\n=== Test Complete ===")