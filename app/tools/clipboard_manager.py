#!/usr/bin/env python3
"""
Clipboard Manager Tool
Clipboard operations and history management
"""

import win32clipboard
import win32con
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from pathlib import Path
from langchain.tools import tool


class ClipboardHistory:
    """Manages clipboard history"""
    
    def __init__(self, max_items: int = 50):
        self.max_items = max_items
        self.history = []
        self.history_file = Path("data/clipboard/history.json")
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_history()
    
    def add_item(self, content: str, content_type: str = "text"):
        """Add item to history"""
        item = {
            'content': content,
            'type': content_type,
            'timestamp': time.time(),
            'datetime': datetime.now().isoformat()
        }
        
        # Remove duplicates
        self.history = [h for h in self.history if h['content'] != content]
        
        # Add to beginning
        self.history.insert(0, item)
        
        # Limit size
        if len(self.history) > self.max_items:
            self.history = self.history[:self.max_items]
        
        self._save_history()
    
    def get_history(self, limit: int = None) -> List[Dict]:
        """Get clipboard history"""
        if limit:
            return self.history[:limit]
        return self.history
    
    def clear_history(self):
        """Clear clipboard history"""
        self.history = []
        self._save_history()
    
    def _load_history(self):
        """Load history from file"""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
        except:
            self.history = []
    
    def _save_history(self):
        """Save history to file"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except:
            pass


# Global clipboard history instance
_clipboard_history = ClipboardHistory()


@tool
def get_clipboard_content() -> Dict[str, Any]:
    """
    Get current clipboard content
    
    Returns:
        Dict: Clipboard content and metadata
    """
    try:
        win32clipboard.OpenClipboard()
        
        try:
            # Try to get text content
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                content = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                content_type = "text"
            elif win32clipboard.IsClipboardFormatAvailable(win32con.CF_TEXT):
                content = win32clipboard.GetClipboardData(win32con.CF_TEXT)
                if isinstance(content, bytes):
                    content = content.decode('utf-8', errors='ignore')
                content_type = "text"
            else:
                # Check for other formats
                available_formats = []
                fmt = 0
                while True:
                    fmt = win32clipboard.EnumClipboardFormats(fmt)
                    if fmt == 0:
                        break
                    try:
                        format_name = win32clipboard.GetClipboardFormatName(fmt)
                        available_formats.append(f"{fmt} ({format_name})")
                    except:
                        available_formats.append(str(fmt))
                
                return {
                    "success": True,
                    "content": None,
                    "type": "non_text",
                    "available_formats": available_formats,
                    "timestamp": datetime.now().isoformat(),
                    "message": f"Clipboard contains non-text data. Available formats: {', '.join(available_formats[:3])}"
                }
            
            return {
                "success": True,
                "content": content,
                "type": content_type,
                "length": len(content) if content else 0,
                "timestamp": datetime.now().isoformat(),
                "message": f"Retrieved clipboard content ({len(content)} characters)" if content else "Clipboard is empty"
            }
            
        finally:
            win32clipboard.CloseClipboard()
            
    except Exception as e:
        return {
            "success": False,
            "content": None,
            "error": f"Error getting clipboard content: {str(e)}"
        }

@tool
def set_clipboard_content(content: str) -> Dict[str, Any]:
    """
    Set clipboard content
    
    Args:
        content (str): Content to set in clipboard
        
    Returns:
        Dict: Operation result
    """
    try:
        if not isinstance(content, str):
            content = str(content)
        
        win32clipboard.OpenClipboard()
        
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, content)
            
            # Add to history
            _clipboard_history.add_item(content, "text")
            
            return {
                "success": True,
                "content": content,
                "length": len(content),
                "timestamp": datetime.now().isoformat(),
                "message": f"Clipboard updated with {len(content)} characters"
            }
            
        finally:
            win32clipboard.CloseClipboard()
            
    except Exception as e:
        return {
            "success": False,
            "content": content,
            "error": f"Error setting clipboard content: {str(e)}"
        }


@tool
def get_clipboard_history(limit: int = 10) -> Dict[str, Any]:
    """
    Get clipboard history
    
    Args:
        limit (int): Maximum number of items to return
        
    Returns:
        Dict: Clipboard history
    """
    try:
        history = _clipboard_history.get_history(limit)
        
        # Format for display
        formatted_history = []
        for item in history:
            # Truncate long content for display
            display_content = item['content']
            if len(display_content) > 100:
                display_content = display_content[:97] + "..."
            
            formatted_item = {
                'content': item['content'],
                'display_content': display_content,
                'type': item['type'],
                'datetime': item['datetime'],
                'length': len(item['content'])
            }
            formatted_history.append(formatted_item)
        
        return {
            "success": True,
            "history": formatted_history,
            "count": len(formatted_history),
            "limit": limit,
            "message": f"Retrieved {len(formatted_history)} clipboard history items"
        }
        
    except Exception as e:
        return {
            "success": False,
            "history": [],
            "count": 0,
            "error": f"Error getting clipboard history: {str(e)}"
        }


@tool
def restore_clipboard_item(index: int) -> Dict[str, Any]:
    """
    Restore a clipboard item from history
    
    Args:
        index (int): Index of item in history (0 = most recent)
        
    Returns:
        Dict: Operation result
    """
    try:
        history = _clipboard_history.get_history()
        
        if not history:
            return {
                "success": False,
                "index": index,
                "error": "Clipboard history is empty"
            }
        
        if index < 0 or index >= len(history):
            return {
                "success": False,
                "index": index,
                "error": f"Invalid index. History has {len(history)} items (0-{len(history)-1})"
            }
        
        item = history[index]
        result = set_clipboard_content(item['content'])
        
        if result['success']:
            return {
                "success": True,
                "index": index,
                "content": item['content'],
                "original_datetime": item['datetime'],
                "restored_datetime": datetime.now().isoformat(),
                "message": f"Restored clipboard item from {item['datetime']}"
            }
        else:
            return {
                "success": False,
                "index": index,
                "error": f"Failed to restore clipboard item: {result.get('error', 'Unknown error')}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "index": index,
            "error": f"Error restoring clipboard item: {str(e)}"
        }


@tool
def clear_clipboard_history() -> Dict[str, Any]:
    """
    Clear clipboard history
    
    Returns:
        Dict: Operation result
    """
    try:
        old_count = len(_clipboard_history.get_history())
        _clipboard_history.clear_history()
        
        return {
            "success": True,
            "cleared_items": old_count,
            "timestamp": datetime.now().isoformat(),
            "message": f"Cleared {old_count} items from clipboard history"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error clearing clipboard history: {str(e)}"
        }


@tool
def copy_text_from_screen() -> Dict[str, Any]:
    """
    Simulate Ctrl+C to copy selected text
    
    Returns:
        Dict: Operation result
    """
    try:
        import win32api
        import win32con
        
        # Get current clipboard content for comparison
        old_content_result = get_clipboard_content()
        old_content = old_content_result.get('content', '') if old_content_result['success'] else ''
        
        # Simulate Ctrl+C
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        win32api.keybd_event(0x43, 0, 0, 0)  # C key
        win32api.keybd_event(0x43, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
        
        # Wait a moment for clipboard to update
        time.sleep(0.2)
        
        # Get new clipboard content
        new_content_result = get_clipboard_content()
        
        if new_content_result['success']:
            new_content = new_content_result.get('content', '')
            
            if new_content != old_content:
                return {
                    "success": True,
                    "copied_content": new_content,
                    "length": len(new_content) if new_content else 0,
                    "timestamp": datetime.now().isoformat(),
                    "message": f"Copied {len(new_content) if new_content else 0} characters to clipboard"
                }
            else:
                return {
                    "success": True,
                    "copied_content": new_content,
                    "length": len(new_content) if new_content else 0,
                    "timestamp": datetime.now().isoformat(),
                    "message": "Copy command sent (clipboard content unchanged)"
                }
        else:
            return {
                "success": False,
                "error": f"Failed to read clipboard after copy: {new_content_result.get('error', 'Unknown error')}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Error copying text from screen: {str(e)}"
        }


@tool
def paste_text_to_screen() -> Dict[str, Any]:
    """
    Simulate Ctrl+V to paste clipboard content
    
    Returns:
        Dict: Operation result
    """
    try:
        import win32api
        import win32con
        
        # Get current clipboard content to report what will be pasted
        content_result = get_clipboard_content()
        
        # Simulate Ctrl+V
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        win32api.keybd_event(0x56, 0, 0, 0)  # V key
        win32api.keybd_event(0x56, 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
        
        if content_result['success']:
            content = content_result.get('content', '')
            return {
                "success": True,
                "pasted_content": content,
                "length": len(content) if content else 0,
                "timestamp": datetime.now().isoformat(),
                "message": f"Pasted {len(content) if content else 0} characters from clipboard"
            }
        else:
            return {
                "success": True,
                "pasted_content": None,
                "length": 0,
                "timestamp": datetime.now().isoformat(),
                "message": "Paste command sent (clipboard content unknown)"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Error pasting text to screen: {str(e)}"
        }


@tool
def type_text(text: str, delay: float = 0.01) -> Dict[str, Any]:
    """
    Type text character by character
    
    Args:
        text (str): Text to type
        delay (float): Delay between keystrokes in seconds
        
    Returns:
        Dict: Operation result
    """
    try:
        import win32api
        import win32con
        
        for char in text:
            if char == '\n':
                # Handle newlines
                win32api.keybd_event(win32con.VK_RETURN, 0, 0, 0)
                win32api.keybd_event(win32con.VK_RETURN, 0, win32con.KEYEVENTF_KEYUP, 0)
            elif char == '\t':
                # Handle tabs
                win32api.keybd_event(win32con.VK_TAB, 0, 0, 0)
                win32api.keybd_event(win32con.VK_TAB, 0, win32con.KEYEVENTF_KEYUP, 0)
            else:
                # For regular characters, use Unicode input
                try:
                    # Convert to virtual key code
                    vk = win32api.VkKeyScan(char)
                    if vk != -1:
                        key_code = vk & 0xFF
                        shift_state = (vk >> 8) & 0xFF
                        
                        # Press shift if needed
                        if shift_state & 1:
                            win32api.keybd_event(win32con.VK_SHIFT, 0, 0, 0)
                        
                        # Press the key
                        win32api.keybd_event(key_code, 0, 0, 0)
                        win32api.keybd_event(key_code, 0, win32con.KEYEVENTF_KEYUP, 0)
                        
                        # Release shift if needed
                        if shift_state & 1:
                            win32api.keybd_event(win32con.VK_SHIFT, 0, win32con.KEYEVENTF_KEYUP, 0)
                    else:
                        # Use Unicode input for characters that can't be mapped
                        for byte in char.encode('utf-16le'):
                            win32api.keybd_event(0, byte, win32con.KEYEVENTF_UNICODE, 0)
                except:
                    # Skip characters that cause issues
                    continue
            
            if delay > 0:
                time.sleep(delay)
        
        return {
            "success": True,
            "text": text,
            "length": len(text),
            "delay": delay,
            "timestamp": datetime.now().isoformat(),
            "message": f"Typed {len(text)} characters with {delay}s delay"
        }
        
    except Exception as e:
        return {
            "success": False,
            "text": text,
            "delay": delay,
            "error": f"Error typing text: {str(e)}"
        }


if __name__ == "__main__":
    # Test the clipboard manager functions
    print("=== Clipboard Manager Tool Test ===")
    
    # Test getting current clipboard content
    print("\n1. Testing get clipboard content:")
    content_result = get_clipboard_content()
    print(f"Current clipboard: {content_result}")
    
    # Test setting clipboard content
    print("\n2. Testing set clipboard content:")
    test_text = f"Test clipboard content - {datetime.now().strftime('%H:%M:%S')}"
    set_result = set_clipboard_content(test_text)
    print(f"Set clipboard result: {set_result['success']}")
    
    # Test getting updated content
    print("\n3. Testing updated clipboard content:")
    updated_content = get_clipboard_content()
    if updated_content['success']:
        print(f"Updated content: {updated_content['content'][:50]}...")
    
    # Test clipboard history
    print("\n4. Testing clipboard history:")
    history_result = get_clipboard_history(5)
    if history_result['success']:
        print(f"History has {history_result['count']} items:")
        for i, item in enumerate(history_result['history'][:3]):
            print(f"  {i}: {item['display_content']}")
    
    # Test adding another item to history
    print("\n5. Adding another item to history:")
    set_result2 = set_clipboard_content("Another test item for history")
    print(f"Second set result: {set_result2['success']}")
    
    # Test history again
    print("\n6. Testing updated history:")
    history_result2 = get_clipboard_history(3)
    if history_result2['success']:
        print(f"Updated history has {history_result2['count']} items")
    
    print("\n=== Clipboard Manager Test Complete ===")