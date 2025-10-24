#!/usr/bin/env python3
"""
Session Manager
Provides functionality to save and restore work sessions including open files, apps, and window positions
"""

import json
import time
import psutil
import win32gui
import win32process
import win32con
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import subprocess
import os

from ..context.system_state_tracker import get_state_tracker

class SessionManager:
    """Manages work sessions - saving and restoring application states"""
    
    def __init__(self):
        """Initialize session manager"""
        self.state_tracker = get_state_tracker()
        
        # Session storage
        self.sessions_dir = Path("data/sessions")
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        # Current session tracking
        self.current_session = None
        self.auto_save_enabled = True
        self.auto_save_interval = 300  # 5 minutes
        
        print("[Session Manager] Initialized")
    
    def capture_current_session(self) -> Dict[str, Any]:
        """
        Capture the current state of the system as a session
        
        Returns:
            Dict: Current session state
        """
        session = {
            'timestamp': time.time(),
            'datetime': datetime.now().isoformat(),
            'applications': self._get_running_applications(),
            'windows': self._get_window_information(),
            'recent_files': self.state_tracker.get_recent_files(10),
            'working_directory': os.getcwd(),
            'environment_vars': self._get_relevant_env_vars(),
            'system_info': {
                'platform': os.name,
                'username': os.getenv('USERNAME', ''),
                'computername': os.getenv('COMPUTERNAME', '')
            }
        }
        
        # Add file-specific information for better restoration
        session['file_associations'] = self._detect_file_app_associations(session['recent_files'])
        
        print(f"[Session Manager] Captured session with {len(session['applications'])} apps, "
              f"{len(session['windows'])} windows, {len(session['recent_files'])} recent files")
        
        return session
    
    def _get_running_applications(self) -> List[Dict[str, Any]]:
        """Get information about currently running applications"""
        applications = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline', 'create_time']):
                try:
                    pinfo = proc.info
                    
                    # Filter out system processes and focus on user applications
                    if (pinfo['exe'] and 
                        pinfo['name'] and
                        not pinfo['name'].startswith('svchost') and
                        not pinfo['name'].startswith('System')):
                        
                        app_info = {
                            'name': pinfo['name'],
                            'exe_path': pinfo['exe'],
                            'pid': pinfo['pid'],
                            'command_line': pinfo['cmdline'],
                            'start_time': pinfo['create_time'],
                            'restorable': self._is_restorable_app(pinfo['name'], pinfo['exe'])
                        }
                        
                        applications.append(app_info)
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                    
        except Exception as e:
            print(f"[Session Manager] Error getting applications: {e}")
        
        return applications
    
    def _get_window_information(self) -> List[Dict[str, Any]]:
        """Get information about current windows and their positions"""
        windows = []
        
        def enum_windows_callback(hwnd, window_list):
            try:
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title and len(title.strip()) > 0:
                        # Get window position and size
                        rect = win32gui.GetWindowRect(hwnd)
                        
                        # Get process info
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        try:
                            process = psutil.Process(pid)
                            process_name = process.name()
                            exe_path = process.exe()
                        except:
                            process_name = "unknown"
                            exe_path = ""
                        
                        window_info = {
                            'hwnd': hwnd,
                            'title': title,
                            'process_name': process_name,
                            'exe_path': exe_path,
                            'pid': pid,
                            'position': {
                                'left': rect[0],
                                'top': rect[1], 
                                'right': rect[2],
                                'bottom': rect[3],
                                'width': rect[2] - rect[0],
                                'height': rect[3] - rect[1]
                            },
                            'is_maximized': win32gui.IsZoomed(hwnd),
                            'is_minimized': win32gui.IsIconic(hwnd)
                        }
                        
                        window_list.append(window_info)
                        
            except Exception as e:
                pass  # Skip problematic windows
            
            return True
        
        try:
            win32gui.EnumWindows(enum_windows_callback, windows)
        except Exception as e:
            print(f"[Session Manager] Error getting windows: {e}")
        
        return windows
    
    def _get_relevant_env_vars(self) -> Dict[str, str]:
        """Get relevant environment variables"""
        relevant_vars = [
            'PATH', 'PYTHONPATH', 'JAVA_HOME', 'NODE_PATH', 
            'USERPROFILE', 'APPDATA', 'LOCALAPPDATA'
        ]
        
        env_vars = {}
        for var in relevant_vars:
            value = os.getenv(var)
            if value:
                env_vars[var] = value
        
        return env_vars
    
    def _detect_file_app_associations(self, recent_files: List[Dict]) -> Dict[str, str]:
        """Detect which applications were used to open specific file types"""
        associations = {}
        
        for file_info in recent_files:
            if 'extension' in file_info and 'app' in file_info:
                extension = file_info['extension'].lower()
                app = file_info['app']
                if extension and app:
                    associations[extension] = app
        
        return associations
    
    def _is_restorable_app(self, app_name: str, exe_path: str) -> bool:
        """Determine if an application can be reliably restored"""
        # List of applications that are typically restorable
        restorable_apps = [
            'notepad.exe', 'notepad++.exe', 'code.exe', 'chrome.exe', 
            'firefox.exe', 'msedge.exe', 'explorer.exe', 'calc.exe',
            'cmd.exe', 'powershell.exe', 'winword.exe', 'excel.exe',
            'powerpoint.exe', 'sublime_text.exe', 'atom.exe'
        ]
        
        # Check if it's in our list of known restorable apps
        app_name_lower = app_name.lower()
        for restorable in restorable_apps:
            if restorable in app_name_lower:
                return True
        
        # Check if it's a user-installed application (not system)
        if exe_path:
            exe_path_lower = exe_path.lower()
            user_app_paths = ['program files', 'program files (x86)', 'appdata\\local']
            for path in user_app_paths:
                if path in exe_path_lower:
                    return True
        
        return False
    
    def save_session(self, session_name: str, session_data: Optional[Dict] = None) -> bool:
        """
        Save a session to disk
        
        Args:
            session_name (str): Name for the session
            session_data (Dict): Session data (if None, captures current session)
            
        Returns:
            bool: Success status
        """
        try:
            if session_data is None:
                session_data = self.capture_current_session()
            
            # Add metadata
            session_data['name'] = session_name
            session_data['saved_timestamp'] = time.time()
            session_data['version'] = '1.0'
            
            # Save to file
            session_file = self.sessions_dir / f"{session_name}.json"
            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=2, default=str)
            
            print(f"[Session Manager] Session '{session_name}' saved to {session_file}")
            return True
            
        except Exception as e:
            print(f"[Session Manager] Error saving session '{session_name}': {e}")
            return False
    
    def load_session(self, session_name: str) -> Optional[Dict[str, Any]]:
        """
        Load a session from disk
        
        Args:
            session_name (str): Name of the session to load
            
        Returns:
            Dict: Session data or None if not found
        """
        try:
            session_file = self.sessions_dir / f"{session_name}.json"
            
            if not session_file.exists():
                print(f"[Session Manager] Session '{session_name}' not found")
                return None
            
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            print(f"[Session Manager] Session '{session_name}' loaded")
            return session_data
            
        except Exception as e:
            print(f"[Session Manager] Error loading session '{session_name}': {e}")
            return None
    
    def restore_session(self, session_name: str, selective: bool = False) -> bool:
        """
        Restore a saved session
        
        Args:
            session_name (str): Name of the session to restore
            selective (bool): If True, only restore restorable applications
            
        Returns:
            bool: Success status
        """
        session_data = self.load_session(session_name)
        if not session_data:
            return False
        
        print(f"[Session Manager] Restoring session '{session_name}'...")
        
        success_count = 0
        total_attempts = 0
        
        # Restore applications
        applications = session_data.get('applications', [])
        for app_info in applications:
            if not selective or app_info.get('restorable', False):
                if self._restore_application(app_info):
                    success_count += 1
                total_attempts += 1
        
        # Restore working directory
        if 'working_directory' in session_data:
            try:
                os.chdir(session_data['working_directory'])
                print(f"[Session Manager] Restored working directory: {session_data['working_directory']}")
            except Exception as e:
                print(f"[Session Manager] Could not restore working directory: {e}")
        
        # Note: Window positions are restored after applications start
        # This would typically require a delayed restoration process
        
        print(f"[Session Manager] Session restoration complete: {success_count}/{total_attempts} apps restored")
        
        return success_count > 0
    
    def _restore_application(self, app_info: Dict[str, Any]) -> bool:
        """
        Restore a single application
        
        Args:
            app_info (Dict): Application information from session
            
        Returns:
            bool: Success status
        """
        try:
            exe_path = app_info.get('exe_path')
            if not exe_path or not os.path.exists(exe_path):
                print(f"[Session Manager] Application not found: {exe_path}")
                return False
            
            # Launch the application
            command_line = app_info.get('command_line', [])
            if command_line and len(command_line) > 1:
                # Use original command line if available
                subprocess.Popen(command_line, shell=False)
            else:
                # Just launch the executable
                subprocess.Popen([exe_path], shell=False)
            
            print(f"[Session Manager] Restored application: {app_info['name']}")
            return True
            
        except Exception as e:
            print(f"[Session Manager] Error restoring {app_info['name']}: {e}")
            return False
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        List all available sessions
        
        Returns:
            List: Session information
        """
        sessions = []
        
        try:
            for session_file in self.sessions_dir.glob("*.json"):
                try:
                    with open(session_file, 'r') as f:
                        session_data = json.load(f)
                    
                    sessions.append({
                        'name': session_data.get('name', session_file.stem),
                        'file': str(session_file),
                        'timestamp': session_data.get('saved_timestamp', 0),
                        'datetime': session_data.get('datetime', 'Unknown'),
                        'app_count': len(session_data.get('applications', [])),
                        'file_count': len(session_data.get('recent_files', []))
                    })
                    
                except Exception as e:
                    print(f"[Session Manager] Error reading session {session_file}: {e}")
                    
        except Exception as e:
            print(f"[Session Manager] Error listing sessions: {e}")
        
        # Sort by timestamp (newest first)
        sessions.sort(key=lambda x: x['timestamp'], reverse=True)
        return sessions
    
    def delete_session(self, session_name: str) -> bool:
        """
        Delete a saved session
        
        Args:
            session_name (str): Name of session to delete
            
        Returns:
            bool: Success status
        """
        try:
            session_file = self.sessions_dir / f"{session_name}.json"
            
            if session_file.exists():
                session_file.unlink()
                print(f"[Session Manager] Deleted session: {session_name}")
                return True
            else:
                print(f"[Session Manager] Session not found: {session_name}")
                return False
                
        except Exception as e:
            print(f"[Session Manager] Error deleting session '{session_name}': {e}")
            return False
    
    def create_workspace_template(self, workspace_name: str, 
                                applications: List[str],
                                folders: List[str] = None,
                                files: List[str] = None) -> bool:
        """
        Create a workspace template for quick setup
        
        Args:
            workspace_name (str): Name of the workspace
            applications (List[str]): List of applications to launch
            folders (List[str]): List of folders to open
            files (List[str]): List of files to open
            
        Returns:
            bool: Success status
        """
        workspace_template = {
            'name': workspace_name,
            'type': 'workspace_template',
            'created_timestamp': time.time(),
            'created_datetime': datetime.now().isoformat(),
            'applications': applications or [],
            'folders': folders or [],
            'files': files or [],
            'version': '1.0'
        }
        
        try:
            template_file = self.sessions_dir / f"workspace_{workspace_name}.json"
            with open(template_file, 'w') as f:
                json.dump(workspace_template, f, indent=2)
            
            print(f"[Session Manager] Workspace template '{workspace_name}' created")
            return True
            
        except Exception as e:
            print(f"[Session Manager] Error creating workspace template: {e}")
            return False
    
    def setup_workspace(self, workspace_name: str) -> bool:
        """
        Set up a predefined workspace
        
        Args:
            workspace_name (str): Name of workspace to set up
            
        Returns:
            bool: Success status
        """
        try:
            template_file = self.sessions_dir / f"workspace_{workspace_name}.json"
            
            if not template_file.exists():
                print(f"[Session Manager] Workspace template '{workspace_name}' not found")
                return False
            
            with open(template_file, 'r') as f:
                workspace = json.load(f)
            
            print(f"[Session Manager] Setting up workspace: {workspace_name}")
            
            # Launch applications
            for app in workspace.get('applications', []):
                try:
                    subprocess.Popen([app], shell=True)
                    print(f"[Session Manager] Launched: {app}")
                    time.sleep(1)  # Small delay between launches
                except Exception as e:
                    print(f"[Session Manager] Failed to launch {app}: {e}")
            
            # Open folders
            for folder in workspace.get('folders', []):
                try:
                    subprocess.Popen(['explorer', folder], shell=False)
                    print(f"[Session Manager] Opened folder: {folder}")
                except Exception as e:
                    print(f"[Session Manager] Failed to open folder {folder}: {e}")
            
            # Open files
            for file_path in workspace.get('files', []):
                try:
                    subprocess.Popen(['start', '', file_path], shell=True)
                    print(f"[Session Manager] Opened file: {file_path}")
                except Exception as e:
                    print(f"[Session Manager] Failed to open file {file_path}: {e}")
            
            print(f"[Session Manager] Workspace '{workspace_name}' setup complete")
            return True
            
        except Exception as e:
            print(f"[Session Manager] Error setting up workspace: {e}")
            return False
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of session management system"""
        sessions = self.list_sessions()
        
        return {
            'total_sessions': len(sessions),
            'sessions_directory': str(self.sessions_dir),
            'recent_sessions': sessions[:5],  # Last 5 sessions
            'auto_save_enabled': self.auto_save_enabled,
            'auto_save_interval': self.auto_save_interval
        }


# Global session manager instance
_session_manager = None

def get_session_manager():
    """Get the global session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager

def save_current_session(session_name):
    """Convenience function to save current session"""
    manager = get_session_manager()
    return manager.save_session(session_name)

def restore_session(session_name):
    """Convenience function to restore session"""
    manager = get_session_manager()
    return manager.restore_session(session_name)

def list_available_sessions():
    """Convenience function to list sessions"""
    manager = get_session_manager()
    return manager.list_sessions()

def setup_workspace(workspace_name):
    """Convenience function to setup workspace"""
    manager = get_session_manager()
    return manager.setup_workspace(workspace_name)

# Test functionality
if __name__ == "__main__":
    print("=== Session Manager Test ===")
    
    manager = SessionManager()
    
    # Test session capture
    print("\\n1. Testing session capture:")
    current_session = manager.capture_current_session()
    print(f"Captured session with {len(current_session['applications'])} apps")
    
    # Test session save/load
    print("\\n2. Testing save/load:")
    if manager.save_session("test_session", current_session):
        loaded_session = manager.load_session("test_session")
        if loaded_session:
            print(f"Successfully saved and loaded session")
    
    # Test session listing
    print("\\n3. Testing session listing:")
    sessions = manager.list_sessions()
    print(f"Found {len(sessions)} saved sessions:")
    for session in sessions[:3]:  # Show first 3
        print(f"  - {session['name']}: {session['app_count']} apps, {session['datetime']}")
    
    # Test workspace template creation
    print("\\n4. Testing workspace template:")
    success = manager.create_workspace_template(
        "coding_workspace",
        applications=["code.exe", "chrome.exe"],
        folders=["C:\\\\Users\\\\Documents\\\\Projects"]
    )
    print(f"Workspace template created: {success}")
    
    # Test system summary
    print("\\n5. Testing system summary:")
    summary = manager.get_session_summary()
    print(f"Summary: {summary}")
    
    print("\\n=== Test Complete ===")