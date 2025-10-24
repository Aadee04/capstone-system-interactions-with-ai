#!/usr/bin/env python3
"""
Smart Query Resolver
Converts context-aware user queries into specific actionable commands
"""

import re
import time
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from modules.context.system_state_tracker import get_state_tracker
from modules.context.context_manager import get_context_manager

class SmartQueryResolver:
    """Resolves context-aware queries into specific actionable commands"""
    
    def __init__(self):
        """Initialize the smart query resolver"""
        self.state_tracker = get_state_tracker()
        self.context_manager = get_context_manager()
        
        # Query patterns for different types of requests
        self.query_patterns = {
            'file_operations': [
                # Recent file patterns
                (r"open (?:the )?last (?:modified )?file", "get_last_file"),
                (r"open (?:the )?recent(?:ly opened)? file", "get_recent_file"),
                (r"open that file", "get_recent_file"),
                (r"open (?:the )?file I was (?:working on|editing)", "get_recent_file"),
                
                # File by pattern
                (r"open (?:the )?(.+?) file", "find_file_by_pattern"),
                (r"find (?:my )?(.+?) file", "find_file_by_pattern"),
                (r"show me (?:my )?(.+?) files", "find_files_by_pattern"),
                
                # File by type/date
                (r"open (?:a )?(.+?) from yesterday", "get_file_by_date"),
                (r"show (?:me )?(?:my )?recent (.+?) files", "get_files_by_type"),
            ],
            
            'app_operations': [
                # Recent app patterns
                (r"open (?:the )?last (?:used )?app(?:lication)?", "get_recent_app"),
                (r"switch to (?:the )?last app", "get_recent_app"),
                (r"go back to that app", "get_recent_app"),
                
                # Close operations
                (r"close (?:the )?last (?:opened )?app", "close_recent_app"),
                (r"close (?:all )?recent apps", "close_recent_apps"),
                (r"close that app", "close_recent_app"),
                
                # App by name/pattern
                (r"open (?:my )?(.+?) app", "open_app_by_pattern"),
                (r"launch (.+)", "open_app_by_pattern"),
            ],
            
            'folder_operations': [
                # Context-aware folder operations
                (r"open (?:my )?(.+?) folder", "resolve_folder_context"),
                (r"go to (?:my )?(.+?) (?:folder|directory)", "resolve_folder_context"),
                (r"show me (?:my )?(.+?) (?:folder|directory)", "resolve_folder_context"),
                
                # Recent folder operations
                (r"open (?:the )?last (?:used )?folder", "get_recent_folder"),
                (r"go to (?:the )?recent folder", "get_recent_folder"),
            ],
            
            'session_operations': [
                # Session management
                (r"save (?:my )?(?:current )?session", "save_session"),
                (r"restore (?:my )?(.+?) session", "restore_session"),
                (r"load (?:my )?(.+?) setup", "restore_session"),
                
                # Workspace operations
                (r"setup for (.+)", "setup_workspace"),
                (r"prepare (?:my )?(.+?) workspace", "setup_workspace"),
            ],
            
            'system_operations': [
                # System queries
                (r"what(?:'s| is) running", "list_running_apps"),
                (r"what apps (?:are|do I have) open", "list_running_apps"),
                (r"show (?:me )?(?:my )?recent activity", "show_recent_activity"),
                (r"what did I (?:work on|do) (?:today|yesterday|recently)", "show_recent_activity"),
            ]
        }
        
        print("[Smart Query Resolver] Initialized")
    
    def resolve_query(self, user_query: str) -> Dict[str, Any]:
        """
        Resolve a user query into actionable commands
        
        Args:
            user_query (str): The user's natural language query
            
        Returns:
            Dict[str, Any]: Resolution result with command and parameters
        """
        query_lower = user_query.lower().strip()
        
        # Try to match against known patterns
        for category, patterns in self.query_patterns.items():
            for pattern, handler_name in patterns:
                match = re.search(pattern, query_lower)
                if match:
                    # Get handler method
                    handler = getattr(self, f"_handle_{handler_name}", None)
                    if handler:
                        try:
                            result = handler(user_query, match, category)
                            if result:
                                result['original_query'] = user_query
                                result['matched_pattern'] = pattern
                                result['category'] = category
                                return result
                        except Exception as e:
                            print(f"[Smart Query Resolver] Error in {handler_name}: {e}")
                            continue
        
        # Fallback: try context resolution
        context_result = self._try_context_resolution(user_query)
        if context_result:
            return context_result
        
        # No resolution found
        return {
            'resolved': False,
            'original_query': user_query,
            'error': 'Could not resolve query',
            'suggestions': self._get_query_suggestions(user_query)
        }
    
    def _handle_get_last_file(self, query: str, match: re.Match, category: str) -> Dict[str, Any]:
        """Handle requests for the last/most recent file"""
        last_file = self.state_tracker.get_last_modified_file()
        
        if last_file:
            return {
                'resolved': True,
                'command': 'open_file',
                'parameters': {'file_path': last_file},
                'description': f"Open most recent file: {Path(last_file).name}",
                'confidence': 0.9
            }
        
        return None
    
    def _handle_get_recent_file(self, query: str, match: re.Match, category: str) -> Dict[str, Any]:
        """Handle requests for recent files"""
        recent_files = self.state_tracker.get_recent_files(5)
        
        if recent_files:
            # Return the most recent
            most_recent = recent_files[0]
            return {
                'resolved': True,
                'command': 'open_file',
                'parameters': {'file_path': most_recent['path']},
                'description': f"Open recent file: {most_recent['name']}",
                'confidence': 0.8,
                'alternatives': [{'path': f['path'], 'name': f['name']} for f in recent_files[1:]]
            }
        
        return None
    
    def _handle_find_file_by_pattern(self, query: str, match: re.Match, category: str) -> Dict[str, Any]:
        """Handle requests to find files by pattern"""
        pattern = match.group(1) if match.groups() else ""
        
        if pattern:
            matches = self.state_tracker.find_files_by_pattern(pattern, limit=5)
            
            if matches:
                return {
                    'resolved': True,
                    'command': 'open_file',
                    'parameters': {'file_path': matches[0]},
                    'description': f"Open file matching '{pattern}': {Path(matches[0]).name}",
                    'confidence': 0.7,
                    'alternatives': [{'path': f, 'name': Path(f).name} for f in matches[1:]]
                }
        
        return None
    
    def _handle_find_files_by_pattern(self, query: str, match: re.Match, category: str) -> Dict[str, Any]:
        """Handle requests to find multiple files by pattern"""
        pattern = match.group(1) if match.groups() else ""
        
        if pattern:
            matches = self.state_tracker.find_files_by_pattern(pattern, limit=10)
            
            if matches:
                return {
                    'resolved': True,
                    'command': 'list_files',
                    'parameters': {'file_paths': matches, 'pattern': pattern},
                    'description': f"Found {len(matches)} files matching '{pattern}'",
                    'confidence': 0.8
                }
        
        return None
    
    def _handle_get_file_by_date(self, query: str, match: re.Match, category: str) -> Dict[str, Any]:
        """Handle requests for files from specific dates"""
        pattern = match.group(1) if match.groups() else ""
        
        # Determine days ago based on query
        days_ago = 1  # Default to yesterday
        if "today" in query.lower():
            days_ago = 0
        elif "yesterday" in query.lower():
            days_ago = 1
        elif "week" in query.lower():
            days_ago = 7
        
        files = self.state_tracker.get_recent_files(10, file_type=None, days_ago=days_ago)
        
        if pattern:
            # Filter by pattern
            files = [f for f in files if pattern.lower() in f['name'].lower()]
        
        if files:
            return {
                'resolved': True,
                'command': 'list_files',
                'parameters': {'file_paths': [f['path'] for f in files]},
                'description': f"Files from {days_ago} day(s) ago matching '{pattern}'",
                'confidence': 0.7
            }
        
        return None
    
    def _handle_get_files_by_type(self, query: str, match: re.Match, category: str) -> Dict[str, Any]:
        """Handle requests for files by type"""
        file_type = match.group(1) if match.groups() else ""
        
        # Map common terms to file extensions
        type_mapping = {
            'document': ['pdf', 'doc', 'docx', 'txt'],
            'documents': ['pdf', 'doc', 'docx', 'txt'],
            'image': ['jpg', 'jpeg', 'png', 'gif', 'bmp'],
            'images': ['jpg', 'jpeg', 'png', 'gif', 'bmp'],
            'picture': ['jpg', 'jpeg', 'png', 'gif', 'bmp'],
            'pictures': ['jpg', 'jpeg', 'png', 'gif', 'bmp'],
            'video': ['mp4', 'avi', 'mkv', 'mov'],
            'videos': ['mp4', 'avi', 'mkv', 'mov'],
            'audio': ['mp3', 'wav', 'flac', 'm4a'],
            'music': ['mp3', 'wav', 'flac', 'm4a'],
            'presentation': ['ppt', 'pptx'],
            'spreadsheet': ['xls', 'xlsx', 'csv'],
            'code': ['py', 'js', 'html', 'css', 'cpp', 'java'],
        }
        
        extensions = type_mapping.get(file_type, [file_type])
        all_files = []
        
        for ext in extensions:
            files = self.state_tracker.get_recent_files(20, file_type=ext)
            all_files.extend(files)
        
        if all_files:
            # Remove duplicates and sort by timestamp
            unique_files = []
            seen_paths = set()
            for file_info in all_files:
                if file_info['path'] not in seen_paths:
                    unique_files.append(file_info)
                    seen_paths.add(file_info['path'])
            
            unique_files.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return {
                'resolved': True,
                'command': 'list_files',
                'parameters': {'file_paths': [f['path'] for f in unique_files[:10]]},
                'description': f"Recent {file_type} files",
                'confidence': 0.8
            }
        
        return None
    
    def _handle_get_recent_app(self, query: str, match: re.Match, category: str) -> Dict[str, Any]:
        """Handle requests for recent apps"""
        recent_apps = self.state_tracker.get_recent_apps(5)
        
        if recent_apps:
            most_recent = recent_apps[0]
            return {
                'resolved': True,
                'command': 'open_app',
                'parameters': {'app_name': most_recent['name']},
                'description': f"Open recent app: {most_recent['name']}",
                'confidence': 0.8,
                'alternatives': [{'name': app['name']} for app in recent_apps[1:]]
            }
        
        return None
    
    def _handle_close_recent_app(self, query: str, match: re.Match, category: str) -> Dict[str, Any]:
        """Handle requests to close recent apps"""
        recent_apps = self.state_tracker.get_recent_apps(3)
        
        if recent_apps:
            return {
                'resolved': True,
                'command': 'close_app',
                'parameters': {'app_name': recent_apps[0]['name']},
                'description': f"Close recent app: {recent_apps[0]['name']}",
                'confidence': 0.7
            }
        
        return None
    
    def _handle_close_recent_apps(self, query: str, match: re.Match, category: str) -> Dict[str, Any]:
        """Handle requests to close multiple recent apps"""
        recent_apps = self.state_tracker.get_recent_apps(5)
        
        if recent_apps:
            return {
                'resolved': True,
                'command': 'close_multiple_apps',
                'parameters': {'app_names': [app['name'] for app in recent_apps]},
                'description': f"Close {len(recent_apps)} recent apps",
                'confidence': 0.6
            }
        
        return None
    
    def _handle_open_app_by_pattern(self, query: str, match: re.Match, category: str) -> Dict[str, Any]:
        """Handle requests to open apps by pattern/name"""
        pattern = match.group(1) if match.groups() else ""
        
        if pattern:
            # Check user preferences first
            preference = self.context_manager.get_preference(pattern)
            if preference:
                return {
                    'resolved': True,
                    'command': 'open_app',
                    'parameters': {'app_name': preference},
                    'description': f"Open preferred {pattern}: {preference}",
                    'confidence': 0.9
                }
            
            # Otherwise, treat as direct app name
            return {
                'resolved': True,
                'command': 'open_app',
                'parameters': {'app_name': pattern},
                'description': f"Open app: {pattern}",
                'confidence': 0.7
            }
        
        return None
    
    def _handle_resolve_folder_context(self, query: str, match: re.Match, category: str) -> Dict[str, Any]:
        """Handle folder operations with context resolution"""
        folder_hint = match.group(1) if match.groups() else ""
        
        # Try to resolve using context manager
        context_result = self.context_manager.resolve_context(query)
        
        if context_result and context_result.get('value'):
            folder_path = context_result['value']
            return {
                'resolved': True,
                'command': 'open_folder',
                'parameters': {'folder_path': folder_path},
                'description': f"Open {context_result.get('keyword', 'folder')}: {Path(folder_path).name}",
                'confidence': context_result.get('confidence', 0.8)
            }
        
        return None
    
    def _handle_get_recent_folder(self, query: str, match: re.Match, category: str) -> Dict[str, Any]:
        """Handle requests for recent folders"""
        # Get recent files and extract their directories
        recent_files = self.state_tracker.get_recent_files(10)
        
        if recent_files:
            # Get most common recent directory
            directories = [f['directory'] for f in recent_files]
            from collections import Counter
            most_common_dir = Counter(directories).most_common(1)[0][0]
            
            return {
                'resolved': True,
                'command': 'open_folder',
                'parameters': {'folder_path': most_common_dir},
                'description': f"Open recent folder: {Path(most_common_dir).name}",
                'confidence': 0.7
            }
        
        return None
    
    def _handle_save_session(self, query: str, match: re.Match, category: str) -> Dict[str, Any]:
        """Handle session saving requests"""
        # Generate session name based on current time or extract from query
        session_name = f"session_{int(time.time())}"
        
        # Look for specific session name in query
        name_patterns = [r"save (?:as |my )?(.+?) session", r"call it (.+)"]
        for pattern in name_patterns:
            name_match = re.search(pattern, query.lower())
            if name_match:
                session_name = name_match.group(1).strip()
                break
        
        return {
            'resolved': True,
            'command': 'save_session',
            'parameters': {'session_name': session_name},
            'description': f"Save current session as: {session_name}",
            'confidence': 0.8
        }
    
    def _handle_restore_session(self, query: str, match: re.Match, category: str) -> Dict[str, Any]:
        """Handle session restoration requests"""
        session_name = match.group(1) if match.groups() else "default"
        
        return {
            'resolved': True,
            'command': 'restore_session',
            'parameters': {'session_name': session_name},
            'description': f"Restore session: {session_name}",
            'confidence': 0.8
        }
    
    def _handle_setup_workspace(self, query: str, match: re.Match, category: str) -> Dict[str, Any]:
        """Handle workspace setup requests"""
        workspace_type = match.group(1) if match.groups() else "default"
        
        return {
            'resolved': True,
            'command': 'setup_workspace',
            'parameters': {'workspace_type': workspace_type},
            'description': f"Setup {workspace_type} workspace",
            'confidence': 0.7
        }
    
    def _handle_list_running_apps(self, query: str, match: re.Match, category: str) -> Dict[str, Any]:
        """Handle requests to list running applications"""
        return {
            'resolved': True,
            'command': 'list_running_apps',
            'parameters': {},
            'description': "List currently running applications",
            'confidence': 0.9
        }
    
    def _handle_show_recent_activity(self, query: str, match: re.Match, category: str) -> Dict[str, Any]:
        """Handle requests to show recent activity"""
        # Determine time period
        days = 0  # Today by default
        if "yesterday" in query.lower():
            days = 1
        elif "week" in query.lower():
            days = 7
        
        return {
            'resolved': True,
            'command': 'show_activity',
            'parameters': {'days_ago': days},
            'description': f"Show recent activity from {days} day(s) ago",
            'confidence': 0.8
        }
    
    def _try_context_resolution(self, query: str) -> Optional[Dict[str, Any]]:
        """Try to resolve query using context manager"""
        context_result = self.context_manager.resolve_context(query)
        
        if context_result:
            # Determine appropriate command based on context type and value
            value = context_result.get('value', '')
            
            if Path(value).is_file():
                command = 'open_file'
                param_key = 'file_path'
                description = f"Open file: {Path(value).name}"
            elif Path(value).is_dir():
                command = 'open_folder'
                param_key = 'folder_path'
                description = f"Open folder: {Path(value).name}"
            else:
                # Treat as generic parameter
                command = 'execute_context'
                param_key = 'context_value'
                description = f"Execute with context: {context_result.get('keyword', 'value')}"
            
            return {
                'resolved': True,
                'command': command,
                'parameters': {param_key: value},
                'description': description,
                'confidence': context_result.get('confidence', 0.6),
                'context_info': context_result
            }
        
        return None
    
    def _get_query_suggestions(self, query: str) -> List[str]:
        """Get suggestions for unresolved queries"""
        suggestions = []
        
        # Get context suggestions
        context_suggestions = self.context_manager.suggest_shortcuts_for_query(query)
        for suggestion in context_suggestions[:3]:
            suggestions.append(f"Did you mean '{suggestion['keyword']}'? ({suggestion['description']})")
        
        # Get recent activity suggestions
        if not suggestions:
            recent_files = self.state_tracker.get_recent_files(3)
            for file_info in recent_files:
                suggestions.append(f"Recent file: {file_info['name']}")
        
        return suggestions
    
    def enhance_query_with_context(self, query: str) -> str:
        """
        Enhance a query with resolved context information
        
        Args:
            query (str): Original user query
            
        Returns:
            str: Enhanced query with context resolved
        """
        resolution = self.resolve_query(query)
        
        if resolution.get('resolved'):
            command = resolution.get('command')
            params = resolution.get('parameters', {})
            
            # Convert resolved command back to enhanced natural language
            if command == 'open_file' and 'file_path' in params:
                return f"open file at {params['file_path']}"
            elif command == 'open_folder' and 'folder_path' in params:
                return f"open folder at {params['folder_path']}"
            elif command == 'open_app' and 'app_name' in params:
                return f"open application {params['app_name']}"
        
        return query  # Return original if no enhancement possible


# Global resolver instance
_smart_resolver = None

def get_smart_resolver():
    """Get the global smart resolver instance"""
    global _smart_resolver
    if _smart_resolver is None:
        _smart_resolver = SmartQueryResolver()
    return _smart_resolver

def resolve_query(query):
    """Convenience function to resolve query"""
    resolver = get_smart_resolver()
    return resolver.resolve_query(query)

def enhance_query(query):
    """Convenience function to enhance query"""
    resolver = get_smart_resolver()
    return resolver.enhance_query_with_context(query)

# Test functionality
if __name__ == "__main__":
    print("=== Smart Query Resolver Test ===")
    
    resolver = SmartQueryResolver()
    
    # Test queries
    test_queries = [
        "open the last file",
        "open my school folder",
        "show me recent documents",
        "close that app", 
        "open chrome",
        "save my session",
        "what's running",
        "open the presentation from yesterday",
        "go to my downloads folder"
    ]
    
    for query in test_queries:
        print(f"\\nQuery: '{query}'")
        result = resolver.resolve_query(query)
        print(f"Resolution: {result}")
        
        if result.get('resolved'):
            print(f"  Command: {result['command']}")
            print(f"  Parameters: {result['parameters']}")
            print(f"  Description: {result['description']}")
            print(f"  Confidence: {result['confidence']}")
    
    print("\\n=== Test Complete ===")