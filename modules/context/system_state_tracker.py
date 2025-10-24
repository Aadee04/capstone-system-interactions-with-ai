#!/usr/bin/env python3
"""
System State Tracker
Tracks files, applications, windows, and user actions to provide context-aware functionality
"""

import time
import json
import psutil
import win32gui
import win32process
import win32con
from collections import deque
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import threading
import os

class SystemStateTracker:
    """Tracks system state for context-aware operations"""
    
    def __init__(self, max_history=100):
        """
        Initialize state tracker
        
        Args:
            max_history (int): Maximum number of items to keep in history
        """
        self.max_history = max_history
        
        # State tracking collections
        self.recent_files = deque(maxlen=max_history)
        self.recent_apps = deque(maxlen=max_history // 2)
        self.window_history = deque(maxlen=max_history // 2)
        self.user_actions = deque(maxlen=max_history * 2)
        
        # Current state
        self.current_windows = {}
        self.active_processes = {}
        self.file_system_cache = {}
        
        # Monitoring flags
        self.monitoring = False
        self.monitor_thread = None
        
        # State file for persistence
        self.state_file = Path("data/system_state.json")
        self.state_file.parent.mkdir(exist_ok=True)
        
        # Load previous state
        self.load_state()
        
        print("[System State Tracker] Initialized")
    
    def start_monitoring(self):
        """Start background monitoring of system state"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        print("[System State Tracker] Background monitoring started")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        self.save_state()
        print("[System State Tracker] Monitoring stopped")
    
    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.monitoring:
            try:
                self._update_current_state()
                time.sleep(2)  # Check every 2 seconds
            except Exception as e:
                print(f"[System State Tracker] Monitoring error: {e}")
                time.sleep(5)  # Wait longer on error
    
    def _update_current_state(self):
        """Update current system state"""
        # Update process list
        self._update_processes()
        
        # Update window information
        self._update_windows()
        
        # Clean old entries
        self._cleanup_old_entries()
    
    def _update_processes(self):
        """Update current process information"""
        current_processes = {}
        
        for proc in psutil.process_iter(['pid', 'name', 'exe', 'create_time']):
            try:
                pinfo = proc.info
                current_processes[pinfo['pid']] = {
                    'name': pinfo['name'],
                    'exe': pinfo['exe'],
                    'create_time': pinfo['create_time'],
                    'timestamp': time.time()
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Track newly started processes
        new_pids = set(current_processes.keys()) - set(self.active_processes.keys())
        for pid in new_pids:
            if current_processes[pid]['name']:
                self.track_app_opened(
                    current_processes[pid]['name'],
                    current_processes[pid]['exe']
                )
        
        self.active_processes = current_processes
    
    def _update_windows(self):
        """Update current window information"""
        current_windows = {}
        
        def enum_windows_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                try:
                    title = win32gui.GetWindowText(hwnd)
                    if title:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        try:
                            process_name = psutil.Process(pid).name()
                        except:
                            process_name = "unknown"
                        
                        windows[hwnd] = {
                            'title': title,
                            'pid': pid,
                            'process': process_name,
                            'timestamp': time.time()
                        }
                except:
                    pass
            return True
        
        win32gui.EnumWindows(enum_windows_callback, current_windows)
        
        # Track window changes
        old_titles = {info['title'] for info in self.current_windows.values()}
        new_titles = {info['title'] for info in current_windows.values()}
        
        # New windows
        for title in new_titles - old_titles:
            if title and title not in ["", " "]:
                self.track_window_opened(title)
        
        self.current_windows = current_windows
    
    def _cleanup_old_entries(self):
        """Remove old entries to prevent memory growth"""
        cutoff_time = time.time() - (24 * 60 * 60)  # 24 hours ago
        
        # Clean file system cache
        old_paths = [path for path, info in self.file_system_cache.items() 
                    if info.get('timestamp', 0) < cutoff_time]
        for path in old_paths:
            del self.file_system_cache[path]
    
    def track_file_accessed(self, file_path: str, action: str = "opened", app_name: str = None):
        """
        Track file access
        
        Args:
            file_path (str): Path to the file
            action (str): Action performed (opened, saved, closed)
            app_name (str): Application that accessed the file
        """
        file_info = {
            'path': file_path,
            'name': Path(file_path).name,
            'directory': str(Path(file_path).parent),
            'extension': Path(file_path).suffix.lower(),
            'action': action,
            'app': app_name,
            'timestamp': time.time(),
            'datetime': datetime.now().isoformat()
        }
        
        self.recent_files.appendleft(file_info)
        self.user_actions.appendleft({
            'type': 'file_access',
            'details': file_info,
            'timestamp': time.time()
        })
        
        print(f"[State Tracker] File {action}: {Path(file_path).name}")
    
    def track_app_opened(self, app_name: str, app_path: str = None):
        """
        Track application opening
        
        Args:
            app_name (str): Name of the application
            app_path (str): Full path to application executable
        """
        app_info = {
            'name': app_name,
            'path': app_path,
            'timestamp': time.time(),
            'datetime': datetime.now().isoformat()
        }
        
        self.recent_apps.appendleft(app_info)
        self.user_actions.appendleft({
            'type': 'app_opened',
            'details': app_info,
            'timestamp': time.time()
        })
        
        print(f"[State Tracker] App opened: {app_name}")
    
    def track_window_opened(self, window_title: str):
        """
        Track window opening
        
        Args:
            window_title (str): Title of the window
        """
        window_info = {
            'title': window_title,
            'timestamp': time.time(),
            'datetime': datetime.now().isoformat()
        }
        
        self.window_history.appendleft(window_info)
        self.user_actions.appendleft({
            'type': 'window_opened',
            'details': window_info,
            'timestamp': time.time()
        })
    
    def get_recent_files(self, count: int = 10, file_type: str = None, 
                        days_ago: int = None) -> List[Dict]:
        """
        Get recently accessed files
        
        Args:
            count (int): Maximum number of files to return
            file_type (str): Filter by file extension (e.g., 'pdf', 'docx')
            days_ago (int): Filter files from specific days ago
            
        Returns:
            List[Dict]: List of recent file information
        """
        files = list(self.recent_files)
        
        # Filter by file type
        if file_type:
            files = [f for f in files if f['extension'].lstrip('.').lower() == file_type.lower()]
        
        # Filter by date
        if days_ago is not None:
            cutoff = time.time() - (days_ago * 24 * 60 * 60)
            start_time = cutoff - (24 * 60 * 60)  # 24 hour window
            files = [f for f in files if start_time <= f['timestamp'] <= cutoff]
        
        return files[:count]
    
    def get_recent_apps(self, count: int = 10) -> List[Dict]:
        """Get recently opened applications"""
        return list(self.recent_apps)[:count]
    
    def get_last_modified_file(self, directory: str = None) -> Optional[str]:
        """
        Get the most recently modified file
        
        Args:
            directory (str): Specific directory to search, or None for recent files
            
        Returns:
            str: Path to most recently modified file
        """
        if directory:
            # Search specific directory
            try:
                files = Path(directory).glob('*')
                files = [f for f in files if f.is_file()]
                if files:
                    latest_file = max(files, key=lambda x: x.stat().st_mtime)
                    return str(latest_file)
            except Exception as e:
                print(f"[State Tracker] Error accessing directory {directory}: {e}")
                return None
        else:
            # Use recent files cache
            if self.recent_files:
                return self.recent_files[0]['path']
        
        return None
    
    def get_currently_open_files(self) -> List[str]:
        """Get list of files that are currently open in applications"""
        open_files = []
        
        # This is a simplified version - in practice you'd need to query
        # specific applications for their open files
        for window in self.current_windows.values():
            title = window['title']
            # Look for file paths or names in window titles
            if '\\' in title or '/' in title:
                # Likely contains a file path
                open_files.append(title)
        
        return open_files
    
    def find_files_by_pattern(self, pattern: str, limit: int = 10) -> List[str]:
        """
        Find files matching a pattern in recent files
        
        Args:
            pattern (str): Pattern to match (e.g., "presentation", "report")
            limit (int): Maximum results
            
        Returns:
            List[str]: Matching file paths
        """
        matches = []
        pattern_lower = pattern.lower()
        
        for file_info in self.recent_files:
            if (pattern_lower in file_info['name'].lower() or 
                pattern_lower in file_info['path'].lower()):
                matches.append(file_info['path'])
                if len(matches) >= limit:
                    break
        
        return matches
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get current system statistics"""
        return {
            'recent_files_count': len(self.recent_files),
            'recent_apps_count': len(self.recent_apps),
            'active_windows': len(self.current_windows),
            'active_processes': len(self.active_processes),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:').percent,
            'uptime': time.time() - psutil.boot_time()
        }
    
    def save_state(self):
        """Save current state to file"""
        try:
            state_data = {
                'recent_files': list(self.recent_files)[-50:],  # Save last 50
                'recent_apps': list(self.recent_apps)[-20:],    # Save last 20
                'window_history': list(self.window_history)[-20:],
                'saved_timestamp': time.time()
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state_data, f, indent=2)
                
            print(f"[State Tracker] State saved to {self.state_file}")
        except Exception as e:
            print(f"[State Tracker] Error saving state: {e}")
    
    def load_state(self):
        """Load previous state from file"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    state_data = json.load(f)
                
                # Restore state (only recent items to avoid staleness)
                cutoff_time = time.time() - (2 * 60 * 60)  # 2 hours ago
                
                for file_info in state_data.get('recent_files', []):
                    if file_info.get('timestamp', 0) > cutoff_time:
                        self.recent_files.append(file_info)
                
                for app_info in state_data.get('recent_apps', []):
                    if app_info.get('timestamp', 0) > cutoff_time:
                        self.recent_apps.append(app_info)
                
                print(f"[State Tracker] State loaded from {self.state_file}")
        except Exception as e:
            print(f"[State Tracker] Error loading state: {e}")


# Global state tracker instance
_state_tracker = None

def get_state_tracker():
    """Get the global state tracker instance"""
    global _state_tracker
    if _state_tracker is None:
        _state_tracker = SystemStateTracker()
        _state_tracker.start_monitoring()
    return _state_tracker

def track_file_access(file_path, action="opened", app_name=None):
    """Convenience function to track file access"""
    tracker = get_state_tracker()
    tracker.track_file_accessed(file_path, action, app_name)

def track_app_launch(app_name, app_path=None):
    """Convenience function to track app launch"""
    tracker = get_state_tracker()
    tracker.track_app_opened(app_name, app_path)

def get_recent_files(count=10, **kwargs):
    """Convenience function to get recent files"""
    tracker = get_state_tracker()
    return tracker.get_recent_files(count, **kwargs)

def get_recent_apps(count=10):
    """Convenience function to get recent apps"""
    tracker = get_state_tracker()
    return tracker.get_recent_apps(count)

def shutdown_state_tracker():
    """Shutdown the state tracker"""
    global _state_tracker
    if _state_tracker:
        _state_tracker.stop_monitoring()
        _state_tracker = None

# Test functionality
if __name__ == "__main__":
    print("=== System State Tracker Test ===")
    
    tracker = SystemStateTracker()
    
    # Test file tracking
    tracker.track_file_accessed("C:/Users/test/document.pdf", "opened", "Adobe Reader")
    tracker.track_file_accessed("C:/Users/test/presentation.pptx", "opened", "PowerPoint")
    
    # Test app tracking
    tracker.track_app_opened("notepad.exe", "C:/Windows/System32/notepad.exe")
    tracker.track_app_opened("chrome.exe", "C:/Program Files/Google/Chrome/Application/chrome.exe")
    
    # Test queries
    recent_files = tracker.get_recent_files(5)
    print(f"\\nRecent files: {len(recent_files)}")
    for file_info in recent_files:
        print(f"  {file_info['name']} ({file_info['action']})")
    
    recent_apps = tracker.get_recent_apps(3)
    print(f"\\nRecent apps: {len(recent_apps)}")
    for app_info in recent_apps:
        print(f"  {app_info['name']}")
    
    # Test pattern matching
    matches = tracker.find_files_by_pattern("document")
    print(f"\\nFiles matching 'document': {matches}")
    
    # Test system stats
    stats = tracker.get_system_stats()
    print(f"\\nSystem stats: {stats}")
    
    print("\\n=== Test Complete ===")