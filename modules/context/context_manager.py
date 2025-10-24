#!/usr/bin/env python3
"""
Context Manager
Handles user shortcuts, preferences, and contextual information resolution
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from collections import defaultdict, Counter
import re
import os

class ContextManager:
    """Manages user context, shortcuts, and preferences"""
    
    def __init__(self):
        """Initialize context manager"""
        
        # User-defined shortcuts
        self.user_shortcuts = {}
        
        # Learned preferences
        self.preferences = {}
        
        # Usage patterns for learning
        self.usage_patterns = defaultdict(list)
        
        # Context mappings for natural language
        self.context_mappings = {}
        
        # Files for persistence
        self.shortcuts_file = Path("data/user_shortcuts.json")
        self.preferences_file = Path("data/user_preferences.json")
        self.patterns_file = Path("data/usage_patterns.json")
        
        # Ensure data directory exists
        Path("data").mkdir(exist_ok=True)
        
        # Load existing data
        self.load_data()
        
        # Initialize default shortcuts
        self._initialize_default_shortcuts()
        
        print("[Context Manager] Initialized")
    
    def _initialize_default_shortcuts(self):
        """Set up common default shortcuts (paths/apps) if they don't exist"""
        default_shortcuts = {
            'desktop': str(Path.home() / 'Desktop'),
            'documents': str(Path.home() / 'Documents'),
            'downloads': str(Path.home() / 'Downloads'),
            'pictures': str(Path.home() / 'Pictures'),
            'music': str(Path.home() / 'Music'),
            'videos': str(Path.home() / 'Videos'),
            'home': str(Path.home())
        }
        
        # Only add if not already defined by user
        for key, path in default_shortcuts.items():
            if key not in self.user_shortcuts and os.path.exists(path):
                self.user_shortcuts[key] = path
        
        # Default application preferences
        default_preferences = {
            'browser': 'chrome',  # Default browser preference
            'editor': 'notepad',  # Default text editor
            'pdf_viewer': 'edge',  # Default PDF viewer
            'media_player': 'vlc'  # Default media player
        }
        
        for key, value in default_preferences.items():
            if key not in self.preferences:
                self.preferences[key] = value
    
    def add_user_shortcut(self, keyword: str, path_or_value: str, description: str = None):
        """
        Add a user-defined shortcut
        
        Args:
            keyword (str): The shortcut keyword (e.g., 'school', 'work')
            path_or_value (str): The path or value to map to
            description (str): Optional description
        """
        self.user_shortcuts[keyword.lower()] = {
            'value': path_or_value,
            'description': description or f"User shortcut for {keyword}",
            'created': time.time(),
            'usage_count': 0
        }
        
        self.save_shortcuts()
        print(f"[Context Manager] Added shortcut: {keyword} -> {path_or_value}")
    
    def resolve_context(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Resolve context from user query
        
        Args:
            query (str): User query containing contextual references
            
        Returns:
            Dict[str, Any]: Resolved context information or None
        """
        query_lower = query.lower()
        resolved_contexts = []
        
        # Check for user shortcuts
        for keyword, shortcut_info in self.user_shortcuts.items():
            if keyword in query_lower:
                if isinstance(shortcut_info, dict):
                    value = shortcut_info['value']
                    # Update usage count
                    shortcut_info['usage_count'] = shortcut_info.get('usage_count', 0) + 1
                else:
                    # Handle old format (just string values)
                    value = shortcut_info
                
                resolved_contexts.append({
                    'type': 'shortcut',
                    'keyword': keyword,
                    'value': value,
                    'confidence': self._calculate_keyword_confidence(keyword, query_lower)
                })
        
        # Check for contextual patterns
        contextual_info = self._resolve_contextual_patterns(query_lower)
        if contextual_info:
            resolved_contexts.extend(contextual_info)
        
        # Return best match if any found
        if resolved_contexts:
            best_match = max(resolved_contexts, key=lambda x: x['confidence'])
            return best_match
        
        return None
    
    def _calculate_keyword_confidence(self, keyword: str, query: str) -> float:
        """Calculate confidence score for keyword match"""
        # Exact word match gets higher score
        if f" {keyword} " in f" {query} ":
            return 0.9
        # Partial match
        elif keyword in query:
            return 0.7
        return 0.5
    
    def _resolve_contextual_patterns(self, query: str) -> List[Dict[str, Any]]:
        """Resolve common contextual patterns"""
        contexts = []
        
        # Pattern: "my [something] folder"
        folder_patterns = [
            r"my (\w+) folder",
            r"the (\w+) folder", 
            r"(\w+) directory",
            r"(\w+) files"
        ]
        
        for pattern in folder_patterns:
            matches = re.findall(pattern, query)
            for match in matches:
                if match in self.user_shortcuts:
                    contexts.append({
                        'type': 'folder_reference',
                        'keyword': match,
                        'value': self.user_shortcuts[match]['value'] if isinstance(self.user_shortcuts[match], dict) else self.user_shortcuts[match],
                        'confidence': 0.8
                    })
        
        return contexts
    
    def learn_preference(self, context: str, choice: str, success: bool = True):
        """
        Learn user preferences from their choices
        
        Args:
            context (str): The context of the choice (e.g., 'browser', 'editor')
            choice (str): The user's choice (e.g., 'chrome', 'notepad++')
            success (bool): Whether the choice was successful
        """
        if success:
            if context not in self.usage_patterns:
                self.usage_patterns[context] = []
            
            self.usage_patterns[context].append({
                'choice': choice,
                'timestamp': time.time(),
                'success': success
            })
            
            # Update preference based on most common successful choice
            recent_choices = [item['choice'] for item in self.usage_patterns[context][-10:] 
                           if item['success']]
            
            if recent_choices:
                most_common = Counter(recent_choices).most_common(1)[0][0]
                self.preferences[context] = most_common
                
        self.save_patterns()
        print(f"[Context Manager] Learned preference: {context} -> {choice} ({'success' if success else 'failure'})")
    
    def get_preference(self, context: str, default: str = None) -> str:
        """
        Get user preference for a given context
        
        Args:
            context (str): The context to get preference for
            default (str): Default value if no preference found
            
        Returns:
            str: The preferred choice
        """
        return self.preferences.get(context, default)
    
    def suggest_shortcuts_for_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Suggest shortcuts that might be relevant to the query
        
        Args:
            query (str): User query
            
        Returns:
            List[Dict]: List of suggested shortcuts
        """
        suggestions = []
        query_lower = query.lower()
        
        # Look for partial matches or related terms
        for keyword, shortcut_info in self.user_shortcuts.items():
            if isinstance(shortcut_info, dict):
                value = shortcut_info['value']
                description = shortcut_info.get('description', '')
            else:
                value = shortcut_info
                description = f"Path: {shortcut_info}"
            
            # Check if query contains related terms
            if (keyword in query_lower or 
                any(word in keyword for word in query_lower.split()) or
                any(word in description.lower() for word in query_lower.split())):
                
                suggestions.append({
                    'keyword': keyword,
                    'value': value,
                    'description': description,
                    'relevance': self._calculate_relevance(keyword, query_lower)
                })
        
        # Sort by relevance
        suggestions.sort(key=lambda x: x['relevance'], reverse=True)
        return suggestions[:5]  # Return top 5 suggestions
    
    def _calculate_relevance(self, keyword: str, query: str) -> float:
        """Calculate relevance score for suggestion"""
        score = 0.0
        
        # Exact match
        if keyword == query:
            score += 1.0
        # Contains keyword
        elif keyword in query:
            score += 0.8
        # Shared words
        else:
            keyword_words = set(keyword.split())
            query_words = set(query.split())
            overlap = len(keyword_words.intersection(query_words))
            if overlap > 0:
                score += 0.5 * (overlap / len(keyword_words))
        
        return score
    
    def create_dynamic_shortcut(self, query: str, resolved_path: str):
        """
        Automatically create shortcut based on user query pattern
        
        Args:
            query (str): The original query
            resolved_path (str): The path that was successfully resolved
        """
        # Extract potential keywords from query
        query_lower = query.lower()
        
        # Remove common words
        common_words = {'open', 'go', 'to', 'my', 'the', 'folder', 'directory', 'file', 'files'}
        query_words = [word for word in query_lower.split() if word not in common_words]
        
        # Suggest shortcut creation
        if query_words and os.path.exists(resolved_path):
            suggested_keyword = '_'.join(query_words[:2])  # Use first 2 meaningful words
            
            if suggested_keyword not in self.user_shortcuts:
                print(f"[Context Manager] Suggestion: Create shortcut '{suggested_keyword}' for {resolved_path}?")
                # In a real implementation, you might ask the user for confirmation
                # For now, we'll create it automatically if it seems useful
                
                if len(suggested_keyword) > 2 and len(suggested_keyword) < 20:
                    self.add_user_shortcut(
                        suggested_keyword, 
                        resolved_path, 
                        f"Auto-created from query: {query}"
                    )
    
    def get_contextual_file_suggestions(self, query: str, limit: int = 5) -> List[str]:
        """
        Get file suggestions based on context and user patterns
        
        Args:
            query (str): User query
            limit (int): Maximum number of suggestions
            
        Returns:
            List[str]: List of suggested file paths
        """
        from .system_state_tracker import get_state_tracker
        
        suggestions = []
        
        # Get recent files from state tracker
        state_tracker = get_state_tracker()
        recent_files = state_tracker.get_recent_files(20)
        
        # Filter based on query context
        query_lower = query.lower()
        for file_info in recent_files:
            file_name = file_info['name'].lower()
            file_path = file_info['path'].lower()
            
            # Check if query relates to this file
            if (any(word in file_name for word in query_lower.split()) or
                any(word in file_path for word in query_lower.split())):
                suggestions.append(file_info['path'])
                
                if len(suggestions) >= limit:
                    break
        
        return suggestions
    
    def analyze_usage_patterns(self) -> Dict[str, Any]:
        """Analyze usage patterns and provide insights"""
        analysis = {
            'total_shortcuts': len(self.user_shortcuts),
            'most_used_shortcuts': [],
            'preferences_summary': dict(self.preferences),
            'usage_trends': {}
        }
        
        # Find most used shortcuts
        shortcut_usage = []
        for keyword, info in self.user_shortcuts.items():
            if isinstance(info, dict) and 'usage_count' in info:
                shortcut_usage.append({
                    'keyword': keyword,
                    'usage_count': info['usage_count'],
                    'value': info['value']
                })
        
        shortcut_usage.sort(key=lambda x: x['usage_count'], reverse=True)
        analysis['most_used_shortcuts'] = shortcut_usage[:5]
        
        # Analyze usage trends for each pattern
        for context, pattern_list in self.usage_patterns.items():
            if pattern_list:
                recent_patterns = pattern_list[-10:]  # Last 10 uses
                choices = [p['choice'] for p in recent_patterns if p['success']]
                if choices:
                    analysis['usage_trends'][context] = {
                        'most_common': Counter(choices).most_common(1)[0][0],
                        'total_uses': len(pattern_list),
                        'success_rate': sum(1 for p in pattern_list if p['success']) / len(pattern_list)
                    }
        
        return analysis
    
    def cleanup_unused_shortcuts(self, days: int = 30):
        """Remove shortcuts that haven't been used in specified days"""
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        removed = []
        
        for keyword in list(self.user_shortcuts.keys()):
            shortcut_info = self.user_shortcuts[keyword]
            
            if isinstance(shortcut_info, dict):
                last_used = shortcut_info.get('last_used', shortcut_info.get('created', 0))
                usage_count = shortcut_info.get('usage_count', 0)
                
                # Remove if not used recently and low usage
                if last_used < cutoff_time and usage_count < 3:
                    removed.append(keyword)
                    del self.user_shortcuts[keyword]
        
        if removed:
            self.save_shortcuts()
            print(f"[Context Manager] Cleaned up {len(removed)} unused shortcuts")
        
        return removed
    
    def save_shortcuts(self):
        """Save shortcuts to file"""
        try:
            with open(self.shortcuts_file, 'w') as f:
                json.dump(self.user_shortcuts, f, indent=2)
        except Exception as e:
            print(f"[Context Manager] Error saving shortcuts: {e}")
    
    def save_preferences(self):
        """Save preferences to file"""
        try:
            with open(self.preferences_file, 'w') as f:
                json.dump(self.preferences, f, indent=2)
        except Exception as e:
            print(f"[Context Manager] Error saving preferences: {e}")
    
    def save_patterns(self):
        """Save usage patterns to file"""
        try:
            with open(self.patterns_file, 'w') as f:
                json.dump(dict(self.usage_patterns), f, indent=2)
        except Exception as e:
            print(f"[Context Manager] Error saving patterns: {e}")
    
    def save_all(self):
        """Save all data to files"""
        self.save_shortcuts()
        self.save_preferences()
        self.save_patterns()
    
    def load_data(self):
        """Load all data from files"""
        self.load_shortcuts()
        self.load_preferences()
        self.load_patterns()
    
    def load_shortcuts(self):
        """Load shortcuts from file"""
        try:
            if self.shortcuts_file.exists():
                with open(self.shortcuts_file, 'r') as f:
                    self.user_shortcuts = json.load(f)
                print(f"[Context Manager] Loaded {len(self.user_shortcuts)} shortcuts")
        except Exception as e:
            print(f"[Context Manager] Error loading shortcuts: {e}")
    
    def load_preferences(self):
        """Load preferences from file"""
        try:
            if self.preferences_file.exists():
                with open(self.preferences_file, 'r') as f:
                    self.preferences = json.load(f)
                print(f"[Context Manager] Loaded {len(self.preferences)} preferences")
        except Exception as e:
            print(f"[Context Manager] Error loading preferences: {e}")
    
    def load_patterns(self):
        """Load usage patterns from file"""
        try:
            if self.patterns_file.exists():
                with open(self.patterns_file, 'r') as f:
                    loaded_patterns = json.load(f)
                    self.usage_patterns = defaultdict(list, loaded_patterns)
                print(f"[Context Manager] Loaded usage patterns for {len(self.usage_patterns)} contexts")
        except Exception as e:
            print(f"[Context Manager] Error loading patterns: {e}")


# Global context manager instance
_context_manager = None

def get_context_manager():
    """Get the global context manager instance"""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager

def resolve_context(query):
    """Convenience function to resolve context"""
    manager = get_context_manager()
    return manager.resolve_context(query)

def add_shortcut(keyword, path, description=None):
    """Convenience function to add shortcut"""
    manager = get_context_manager()
    manager.add_user_shortcut(keyword, path, description)

def learn_preference(context, choice, success=True):
    """Convenience function to learn preference"""
    manager = get_context_manager()
    manager.learn_preference(context, choice, success)

def get_preference(context, default=None):
    """Convenience function to get preference"""
    manager = get_context_manager()
    return manager.get_preference(context, default)

# Test functionality
if __name__ == "__main__":
    print("=== Context Manager Test ===")
    
    manager = ContextManager()
    
    # Test adding shortcuts
    manager.add_user_shortcut("school", "C:/Users/Documents/School", "School work folder")
    manager.add_user_shortcut("projects", "C:/Users/Documents/Projects", "Programming projects")
    
    # Test context resolution
    test_queries = [
        "open my school folder",
        "go to projects directory", 
        "show me documents",
        "open work files"
    ]
    
    for query in test_queries:
        context = manager.resolve_context(query)
        print(f"\\nQuery: '{query}'")
        print(f"Context: {context}")
    
    # Test preference learning
    manager.learn_preference("browser", "chrome", True)
    manager.learn_preference("browser", "firefox", False)
    manager.learn_preference("editor", "vscode", True)
    
    print(f"\\nBrowser preference: {manager.get_preference('browser')}")
    print(f"Editor preference: {manager.get_preference('editor')}")
    
    # Test usage analysis
    analysis = manager.analyze_usage_patterns()
    print(f"\\nUsage analysis: {analysis}")
    
    print("\\n=== Test Complete ===")