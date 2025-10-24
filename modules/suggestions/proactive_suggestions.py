#!/usr/bin/env python3
"""
Proactive Suggestion Engine
Monitors system health and provides intelligent suggestions for optimization and maintenance
"""

import json
import time
import psutil
import shutil
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import winreg
import subprocess

from modules.context.system_state_tracker import get_state_tracker
from modules.session.session_manager import get_session_manager
from modules.shortcuts.smart_shortcuts import get_shortcuts_manager


@dataclass
class Suggestion:
    """Represents a proactive suggestion"""
    id: str
    type: str  # 'optimization', 'maintenance', 'workflow', 'security'
    priority: str  # 'high', 'medium', 'low'
    title: str
    description: str
    action_type: str  # 'automated', 'user_action', 'informational'
    action_command: Optional[str] = None  # Command to execute if automated
    estimated_impact: str = "medium"  # 'high', 'medium', 'low'
    created_timestamp: float = None
    dismissed: bool = False


class ProactiveSuggestionEngine:
    """Monitors system health and generates intelligent suggestions"""
    
    def __init__(self):
        """Initialize proactive suggestion engine"""
        self.state_tracker = get_state_tracker()
        self.session_manager = get_session_manager()
        self.shortcuts_manager = get_shortcuts_manager()
        
        # Suggestion storage
        self.suggestions_dir = Path("data/suggestions")
        self.suggestions_dir.mkdir(parents=True, exist_ok=True)
        
        # System thresholds
        self.disk_warning_threshold = 85  # Warn when disk usage > 85%
        self.memory_warning_threshold = 80  # Warn when memory usage > 80%
        self.cpu_warning_threshold = 80  # Warn when CPU usage > 80%
        self.startup_time_threshold = 60  # Warn if startup takes > 60 seconds
        
        # Tracking
        self.last_check_timestamp = 0
        self.check_interval = 300  # Check every 5 minutes
        self.suggestions_cache = []
        
        print("[Proactive Suggestions] Initialized")
    
    def run_health_check(self) -> List[Suggestion]:
        """
        Run comprehensive system health check and generate suggestions
        
        Returns:
            List[Suggestion]: List of new suggestions
        """
        current_time = time.time()
        
        # Skip if checked recently
        if current_time - self.last_check_timestamp < self.check_interval:
            return self.suggestions_cache
        
        print("[Proactive Suggestions] Running system health check...")
        
        suggestions = []
        
        # System resource checks
        suggestions.extend(self._check_disk_usage())
        suggestions.extend(self._check_memory_usage())
        suggestions.extend(self._check_cpu_usage())
        
        # System maintenance checks
        suggestions.extend(self._check_startup_programs())
        suggestions.extend(self._check_temp_files())
        suggestions.extend(self._check_old_downloads())
        
        # Workflow optimization checks
        suggestions.extend(self._check_repetitive_patterns())
        suggestions.extend(self._check_unused_shortcuts())
        suggestions.extend(self._check_session_opportunities())
        
        # Security and privacy checks
        suggestions.extend(self._check_browser_cache())
        suggestions.extend(self._check_system_updates())
        
        # Performance optimization checks
        suggestions.extend(self._check_fragmentation())
        suggestions.extend(self._check_visual_effects())
        
        # Update cache
        self.suggestions_cache = suggestions
        self.last_check_timestamp = current_time
        
        # Save suggestions
        if suggestions:
            self._save_suggestions(suggestions)
        
        print(f"[Proactive Suggestions] Generated {len(suggestions)} suggestions")
        return suggestions
    
    def _check_disk_usage(self) -> List[Suggestion]:
        """Check disk usage and suggest cleanup"""
        suggestions = []
        
        try:
            # Check all drives
            partitions = psutil.disk_partitions()
            
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    usage_percent = (usage.used / usage.total) * 100
                    
                    if usage_percent > self.disk_warning_threshold:
                        free_gb = usage.free / (1024**3)
                        
                        suggestion = Suggestion(
                            id=f"disk_cleanup_{partition.device.replace(':', '')}",
                            type="maintenance",
                            priority="high" if usage_percent > 95 else "medium",
                            title=f"Disk Space Low on {partition.device}",
                            description=f"Drive {partition.device} is {usage_percent:.1f}% full. "
                                      f"Only {free_gb:.1f} GB remaining. Consider cleaning up files.",
                            action_type="user_action",
                            estimated_impact="high",
                            created_timestamp=time.time()
                        )
                        
                        suggestions.append(suggestion)
                        
                except (OSError, PermissionError):
                    continue
                    
        except Exception as e:
            print(f"[Proactive Suggestions] Error checking disk usage: {e}")
        
        return suggestions
    
    def _check_memory_usage(self) -> List[Suggestion]:
        """Check memory usage and suggest optimization"""
        suggestions = []
        
        try:
            memory = psutil.virtual_memory()
            usage_percent = memory.percent
            
            if usage_percent > self.memory_warning_threshold:
                available_gb = memory.available / (1024**3)
                
                suggestion = Suggestion(
                    id="memory_optimization",
                    type="optimization",
                    priority="medium" if usage_percent < 90 else "high",
                    title="High Memory Usage",
                    description=f"Memory usage is {usage_percent:.1f}%. "
                              f"Only {available_gb:.1f} GB available. Consider closing unused applications.",
                    action_type="informational",
                    estimated_impact="medium",
                    created_timestamp=time.time()
                )
                
                suggestions.append(suggestion)
                
        except Exception as e:
            print(f"[Proactive Suggestions] Error checking memory usage: {e}")
        
        return suggestions
    
    def _check_cpu_usage(self) -> List[Suggestion]:
        """Check CPU usage patterns"""
        suggestions = []
        
        try:
            # Sample CPU usage over a few seconds
            cpu_percent = psutil.cpu_percent(interval=1)
            
            if cpu_percent > self.cpu_warning_threshold:
                suggestion = Suggestion(
                    id="cpu_optimization",
                    type="optimization",
                    priority="medium",
                    title="High CPU Usage",
                    description=f"CPU usage is {cpu_percent:.1f}%. "
                              f"Check for resource-intensive applications.",
                    action_type="informational",
                    estimated_impact="medium",
                    created_timestamp=time.time()
                )
                
                suggestions.append(suggestion)
                
        except Exception as e:
            print(f"[Proactive Suggestions] Error checking CPU usage: {e}")
        
        return suggestions
    
    def _check_startup_programs(self) -> List[Suggestion]:
        """Check startup programs and suggest optimization"""
        suggestions = []
        
        try:
            # Count startup programs from registry
            startup_count = 0
            
            # Check common startup locations
            startup_keys = [
                (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
            ]
            
            for hive, subkey in startup_keys:
                try:
                    with winreg.OpenKey(hive, subkey) as key:
                        startup_count += winreg.QueryInfoKey(key)[1]  # Number of values
                except FileNotFoundError:
                    continue
            
            if startup_count > 10:
                suggestion = Suggestion(
                    id="startup_optimization",
                    type="optimization",
                    priority="medium",
                    title="Too Many Startup Programs",
                    description=f"You have {startup_count} programs starting with Windows. "
                              f"Consider disabling unnecessary startup programs to improve boot time.",
                    action_type="user_action",
                    estimated_impact="high",
                    created_timestamp=time.time()
                )
                
                suggestions.append(suggestion)
                
        except Exception as e:
            print(f"[Proactive Suggestions] Error checking startup programs: {e}")
        
        return suggestions
    
    def _check_temp_files(self) -> List[Suggestion]:
        """Check for temporary files that can be cleaned"""
        suggestions = []
        
        try:
            temp_dirs = [
                Path(os.environ.get('TEMP', '')),
                Path(os.environ.get('TMP', '')),
                Path.home() / 'AppData' / 'Local' / 'Temp',
                Path('C:/Windows/Temp')
            ]
            
            total_temp_size = 0
            
            for temp_dir in temp_dirs:
                if temp_dir.exists():
                    try:
                        for file_path in temp_dir.rglob('*'):
                            if file_path.is_file():
                                total_temp_size += file_path.stat().st_size
                    except (OSError, PermissionError):
                        continue
            
            temp_size_mb = total_temp_size / (1024**2)
            
            if temp_size_mb > 500:  # More than 500 MB of temp files
                suggestion = Suggestion(
                    id="temp_cleanup",
                    type="maintenance",
                    priority="medium",
                    title="Clean Temporary Files",
                    description=f"Found {temp_size_mb:.1f} MB of temporary files. "
                              f"Cleaning them can free up disk space.",
                    action_type="automated",
                    action_command="cleanmgr.exe /sagerun:1",
                    estimated_impact="medium",
                    created_timestamp=time.time()
                )
                
                suggestions.append(suggestion)
                
        except Exception as e:
            print(f"[Proactive Suggestions] Error checking temp files: {e}")
        
        return suggestions
    
    def _check_old_downloads(self) -> List[Suggestion]:
        """Check for old files in Downloads folder"""
        suggestions = []
        
        try:
            downloads_path = Path.home() / 'Downloads'
            
            if downloads_path.exists():
                old_files = []
                cutoff_date = datetime.now() - timedelta(days=30)
                
                for file_path in downloads_path.iterdir():
                    if file_path.is_file():
                        modified_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if modified_time < cutoff_date:
                            old_files.append(file_path)
                
                if len(old_files) > 10:
                    total_size = sum(f.stat().st_size for f in old_files) / (1024**2)
                    
                    suggestion = Suggestion(
                        id="downloads_cleanup",
                        type="maintenance",
                        priority="low",
                        title="Clean Old Downloads",
                        description=f"Found {len(old_files)} files older than 30 days in Downloads "
                                  f"({total_size:.1f} MB). Consider organizing or deleting them.",
                        action_type="user_action",
                        estimated_impact="low",
                        created_timestamp=time.time()
                    )
                    
                    suggestions.append(suggestion)
                    
        except Exception as e:
            print(f"[Proactive Suggestions] Error checking downloads: {e}")
        
        return suggestions
    
    def _check_repetitive_patterns(self) -> List[Suggestion]:
        """Analyze user patterns and suggest workflow improvements"""
        suggestions = []
        
        try:
            # Get recent file access patterns
            recent_files = self.state_tracker.get_recent_files(50)
            
            # Look for repetitive patterns
            app_usage = {}
            file_patterns = {}
            
            for file_info in recent_files:
                app = file_info.get('app', 'unknown')
                extension = file_info.get('extension', '')
                
                app_usage[app] = app_usage.get(app, 0) + 1
                file_patterns[extension] = file_patterns.get(extension, 0) + 1
            
            # Suggest shortcuts for frequently used apps
            for app, count in app_usage.items():
                if count >= 5 and app != 'unknown':
                    # Check if user already has a shortcut for this pattern
                    existing_shortcuts = self.shortcuts_manager.list_shortcuts()
                    has_shortcut = any(app.lower() in s['name'].lower() or 
                                     app.lower() in s['description'].lower() 
                                     for s in existing_shortcuts)
                    
                    if not has_shortcut:
                        suggestion = Suggestion(
                            id=f"workflow_shortcut_{app.lower().replace('.exe', '')}",
                            type="workflow",
                            priority="low",
                            title=f"Create Shortcut for {app}",
                            description=f"You've used {app} {count} times recently. "
                                      f"Consider creating a workflow shortcut.",
                            action_type="user_action",
                            estimated_impact="low",
                            created_timestamp=time.time()
                        )
                        
                        suggestions.append(suggestion)
                        
        except Exception as e:
            print(f"[Proactive Suggestions] Error checking patterns: {e}")
        
        return suggestions
    
    def _check_unused_shortcuts(self) -> List[Suggestion]:
        """Check for shortcuts that haven't been used"""
        suggestions = []
        
        try:
            shortcuts = self.shortcuts_manager.list_shortcuts()
            
            # Simple heuristic: if we have more than 5 shortcuts, suggest reviewing them
            if len(shortcuts) > 5:
                old_shortcuts = [s for s in shortcuts if 
                               time.time() - s.get('timestamp', 0) > 30*24*3600]  # 30 days
                
                if old_shortcuts:
                    suggestion = Suggestion(
                        id="review_shortcuts",
                        type="workflow",
                        priority="low",
                        title="Review Old Shortcuts",
                        description=f"You have {len(old_shortcuts)} shortcuts that haven't been "
                                  f"used recently. Consider removing unused ones.",
                        action_type="user_action",
                        estimated_impact="low",
                        created_timestamp=time.time()
                    )
                    
                    suggestions.append(suggestion)
                    
        except Exception as e:
            print(f"[Proactive Suggestions] Error checking shortcuts: {e}")
        
        return suggestions
    
    def _check_session_opportunities(self) -> List[Suggestion]:
        """Suggest session management opportunities"""
        suggestions = []
        
        try:
            sessions = self.session_manager.list_sessions()
            
            # If user doesn't have many sessions but works with multiple apps
            if len(sessions) < 2:
                recent_files = self.state_tracker.get_recent_files(20)
                unique_apps = set(f.get('app', '') for f in recent_files if f.get('app'))
                
                if len(unique_apps) >= 3:
                    suggestion = Suggestion(
                        id="create_work_session",
                        type="workflow",
                        priority="low",
                        title="Consider Creating Work Sessions",
                        description=f"You work with {len(unique_apps)} different applications. "
                                  f"Creating work sessions can help you quickly restore your workspace.",
                        action_type="user_action",
                        estimated_impact="medium",
                        created_timestamp=time.time()
                    )
                    
                    suggestions.append(suggestion)
                    
        except Exception as e:
            print(f"[Proactive Suggestions] Error checking sessions: {e}")
        
        return suggestions
    
    def _check_browser_cache(self) -> List[Suggestion]:
        """Check browser cache sizes"""
        suggestions = []
        
        try:
            # Common browser cache locations
            cache_paths = [
                Path.home() / 'AppData' / 'Local' / 'Google' / 'Chrome' / 'User Data' / 'Default' / 'Cache',
                Path.home() / 'AppData' / 'Local' / 'Microsoft' / 'Edge' / 'User Data' / 'Default' / 'Cache',
                Path.home() / 'AppData' / 'Local' / 'Mozilla' / 'Firefox' / 'Profiles'
            ]
            
            total_cache_size = 0
            
            for cache_path in cache_paths:
                if cache_path.exists():
                    try:
                        for file_path in cache_path.rglob('*'):
                            if file_path.is_file():
                                total_cache_size += file_path.stat().st_size
                    except (OSError, PermissionError):
                        continue
            
            cache_size_mb = total_cache_size / (1024**2)
            
            if cache_size_mb > 1000:  # More than 1 GB
                suggestion = Suggestion(
                    id="browser_cache_cleanup",
                    type="maintenance",
                    priority="low",
                    title="Clear Browser Cache",
                    description=f"Browser cache is {cache_size_mb:.1f} MB. "
                              f"Clearing it can free up space and improve performance.",
                    action_type="user_action",
                    estimated_impact="low",
                    created_timestamp=time.time()
                )
                
                suggestions.append(suggestion)
                
        except Exception as e:
            print(f"[Proactive Suggestions] Error checking browser cache: {e}")
        
        return suggestions
    
    def _check_system_updates(self) -> List[Suggestion]:
        """Check if system updates are available"""
        suggestions = []
        
        try:
            # Simple check for Windows updates (requires admin privileges)
            # This is a basic implementation - in practice would use Windows Update APIs
            
            # Check last update time from registry (simplified)
            last_update_check = time.time() - (7 * 24 * 3600)  # Assume weekly checks
            
            if time.time() - last_update_check > 14 * 24 * 3600:  # 2 weeks
                suggestion = Suggestion(
                    id="system_updates",
                    type="security",
                    priority="medium",
                    title="Check for System Updates",
                    description="It's been a while since the last update check. "
                              "Consider checking for Windows updates for security and performance improvements.",
                    action_type="user_action",
                    estimated_impact="high",
                    created_timestamp=time.time()
                )
                
                suggestions.append(suggestion)
                
        except Exception as e:
            print(f"[Proactive Suggestions] Error checking updates: {e}")
        
        return suggestions
    
    def _check_fragmentation(self) -> List[Suggestion]:
        """Check disk fragmentation (simplified)"""
        suggestions = []
        
        try:
            # This is a simplified check - real fragmentation analysis requires more complex tools
            # For now, suggest periodic defragmentation based on disk usage patterns
            
            partitions = psutil.disk_partitions()
            for partition in partitions:
                if 'NTFS' in partition.fstype or 'ntfs' in partition.fstype:
                    suggestion = Suggestion(
                        id=f"defrag_{partition.device.replace(':', '')}",
                        type="maintenance",
                        priority="low",
                        title=f"Consider Defragmenting {partition.device}",
                        description=f"NTFS drive {partition.device} may benefit from defragmentation. "
                                  f"This can improve file access performance.",
                        action_type="user_action",
                        estimated_impact="medium",
                        created_timestamp=time.time()
                    )
                    
                    suggestions.append(suggestion)
                    break  # Only suggest once
                    
        except Exception as e:
            print(f"[Proactive Suggestions] Error checking fragmentation: {e}")
        
        return suggestions
    
    def _check_visual_effects(self) -> List[Suggestion]:
        """Suggest visual effects optimization for performance"""
        suggestions = []
        
        try:
            # Simple memory-based heuristic
            memory = psutil.virtual_memory()
            
            if memory.total < 8 * (1024**3):  # Less than 8 GB RAM
                suggestion = Suggestion(
                    id="visual_effects_performance",
                    type="optimization",
                    priority="low",
                    title="Optimize Visual Effects",
                    description=f"With {memory.total/(1024**3):.1f} GB RAM, you might benefit "
                              f"from reducing visual effects for better performance.",
                    action_type="user_action",
                    estimated_impact="medium",
                    created_timestamp=time.time()
                )
                
                suggestions.append(suggestion)
                
        except Exception as e:
            print(f"[Proactive Suggestions] Error checking visual effects: {e}")
        
        return suggestions
    
    def _save_suggestions(self, suggestions: List[Suggestion]):
        """Save suggestions to disk"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            suggestions_file = self.suggestions_dir / f"suggestions_{timestamp}.json"
            
            suggestions_data = {
                'timestamp': time.time(),
                'datetime': datetime.now().isoformat(),
                'suggestions': [asdict(suggestion) for suggestion in suggestions]
            }
            
            with open(suggestions_file, 'w') as f:
                json.dump(suggestions_data, f, indent=2, default=str)
                
        except Exception as e:
            print(f"[Proactive Suggestions] Error saving suggestions: {e}")
    
    def get_active_suggestions(self, include_dismissed: bool = False) -> List[Suggestion]:
        """
        Get currently active suggestions
        
        Args:
            include_dismissed (bool): Whether to include dismissed suggestions
            
        Returns:
            List[Suggestion]: Active suggestions
        """
        if include_dismissed:
            return self.suggestions_cache
        else:
            return [s for s in self.suggestions_cache if not s.dismissed]
    
    def dismiss_suggestion(self, suggestion_id: str) -> bool:
        """
        Dismiss a suggestion
        
        Args:
            suggestion_id (str): ID of suggestion to dismiss
            
        Returns:
            bool: Success status
        """
        for suggestion in self.suggestions_cache:
            if suggestion.id == suggestion_id:
                suggestion.dismissed = True
                print(f"[Proactive Suggestions] Dismissed suggestion: {suggestion_id}")
                return True
        
        print(f"[Proactive Suggestions] Suggestion not found: {suggestion_id}")
        return False
    
    def execute_automated_suggestion(self, suggestion_id: str) -> bool:
        """
        Execute an automated suggestion
        
        Args:
            suggestion_id (str): ID of suggestion to execute
            
        Returns:
            bool: Success status
        """
        for suggestion in self.suggestions_cache:
            if suggestion.id == suggestion_id and suggestion.action_type == "automated":
                if suggestion.action_command:
                    try:
                        print(f"[Proactive Suggestions] Executing: {suggestion.action_command}")
                        subprocess.run(suggestion.action_command, shell=True)
                        suggestion.dismissed = True
                        return True
                    except Exception as e:
                        print(f"[Proactive Suggestions] Error executing suggestion: {e}")
                        return False
        
        print(f"[Proactive Suggestions] Cannot execute suggestion: {suggestion_id}")
        return False
    
    def get_suggestions_summary(self) -> Dict[str, Any]:
        """Get summary of suggestions system"""
        active_suggestions = self.get_active_suggestions()
        
        priority_counts = {'high': 0, 'medium': 0, 'low': 0}
        type_counts = {'optimization': 0, 'maintenance': 0, 'workflow': 0, 'security': 0}
        
        for suggestion in active_suggestions:
            priority_counts[suggestion.priority] = priority_counts.get(suggestion.priority, 0) + 1
            type_counts[suggestion.type] = type_counts.get(suggestion.type, 0) + 1
        
        return {
            'total_suggestions': len(active_suggestions),
            'priority_breakdown': priority_counts,
            'type_breakdown': type_counts,
            'last_check': datetime.fromtimestamp(self.last_check_timestamp).isoformat() if self.last_check_timestamp else None,
            'check_interval_minutes': self.check_interval / 60
        }


# Global suggestion engine instance
_suggestion_engine = None

def get_suggestion_engine():
    """Get the global suggestion engine instance"""
    global _suggestion_engine
    if _suggestion_engine is None:
        _suggestion_engine = ProactiveSuggestionEngine()
    return _suggestion_engine

def run_health_check():
    """Convenience function to run health check"""
    engine = get_suggestion_engine()
    return engine.run_health_check()

def get_active_suggestions():
    """Convenience function to get active suggestions"""
    engine = get_suggestion_engine()
    return engine.get_active_suggestions()

# Test functionality
if __name__ == "__main__":
    print("=== Proactive Suggestions Test ===")
    
    engine = ProactiveSuggestionEngine()
    
    # Run health check
    print("\n1. Running health check:")
    suggestions = engine.run_health_check()
    print(f"Generated {len(suggestions)} suggestions")
    
    # Display suggestions by priority
    print("\n2. Suggestions by priority:")
    for priority in ['high', 'medium', 'low']:
        priority_suggestions = [s for s in suggestions if s.priority == priority]
        if priority_suggestions:
            print(f"\n{priority.upper()} Priority ({len(priority_suggestions)}):")
            for suggestion in priority_suggestions:
                print(f"  - {suggestion.title}")
                print(f"    {suggestion.description}")
                if suggestion.action_type == 'automated':
                    print(f"    Action: {suggestion.action_command}")
    
    # Test dismissing a suggestion
    print("\n3. Testing dismiss functionality:")
    if suggestions:
        first_suggestion = suggestions[0]
        success = engine.dismiss_suggestion(first_suggestion.id)
        print(f"Dismissed '{first_suggestion.title}': {success}")
    
    # Get system summary
    print("\n4. System summary:")
    summary = engine.get_suggestions_summary()
    print(f"Summary: {summary}")
    
    print("\n=== Test Complete ===")