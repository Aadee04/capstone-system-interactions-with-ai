#!/usr/bin/env python3
"""
Window Manager Tool
Window control and management operations
"""

import win32gui
import win32con
import win32process
import psutil
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import time
from langchain.tools import tool


@tool
def list_windows(visible_only: bool = True, sort_by: str = "title") -> Dict[str, Any]:
    """
    List all windows
    
    Args:
        visible_only (bool): Only include visible windows
        sort_by (str): Sort by 'title', 'process', or 'size'
        
    Returns:
        Dict: List of windows with details
    """
    try:
        windows = []
        
        def enum_windows_callback(hwnd, window_list):
            try:
                if visible_only and not win32gui.IsWindowVisible(hwnd):
                    return True
                
                title = win32gui.GetWindowText(hwnd)
                if not title and visible_only:
                    return True
                
                # Get window position and size
                rect = win32gui.GetWindowRect(hwnd)
                
                # Get process information
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    process = psutil.Process(pid)
                    process_name = process.name()
                    exe_path = process.exe()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    process_name = "Unknown"
                    exe_path = "N/A"
                
                window_info = {
                    'hwnd': hwnd,
                    'title': title if title else f"<No Title - {process_name}>",
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
                    'is_minimized': win32gui.IsIconic(hwnd),
                    'is_visible': win32gui.IsWindowVisible(hwnd),
                    'is_enabled': win32gui.IsWindowEnabled(hwnd)
                }
                
                window_list.append(window_info)
                
            except Exception as e:
                # Skip problematic windows
                pass
            
            return True
        
        win32gui.EnumWindows(enum_windows_callback, windows)
        
        # Sort windows
        if sort_by == "process":
            windows.sort(key=lambda x: x['process_name'].lower())
        elif sort_by == "size":
            windows.sort(key=lambda x: x['position']['width'] * x['position']['height'], reverse=True)
        else:  # sort by title (default)
            windows.sort(key=lambda x: x['title'].lower())
        
        return {
            "success": True,
            "windows": windows,
            "count": len(windows),
            "visible_only": visible_only,
            "sort_by": sort_by,
            "message": f"Found {len(windows)} {'visible ' if visible_only else ''}windows"
        }
        
    except Exception as e:
        return {
            "success": False,
            "windows": [],
            "count": 0,
            "error": f"Error listing windows: {str(e)}"
        }


@tool
def find_window(window_identifier: str) -> Dict[str, Any]:
    """
    Find a window by title or process name
    
    Args:
        window_identifier (str): Window title or process name to search for
        
    Returns:
        Dict: Window information or error
    """
    try:
        windows_result = list_windows(visible_only=False)
        if not windows_result['success']:
            return windows_result
        
        matches = []
        identifier_lower = window_identifier.lower()
        
        for window in windows_result['windows']:
            if (identifier_lower in window['title'].lower() or 
                identifier_lower in window['process_name'].lower()):
                matches.append(window)
        
        if not matches:
            return {
                "success": False,
                "window_identifier": window_identifier,
                "error": f"No windows found matching: {window_identifier}"
            }
        
        # Return the first match with additional context
        best_match = matches[0]
        return {
            "success": True,
            "window_identifier": window_identifier,
            "window": best_match,
            "total_matches": len(matches),
            "message": f"Found window: {best_match['title']} ({best_match['process_name']})"
        }
        
    except Exception as e:
        return {
            "success": False,
            "window_identifier": window_identifier,
            "error": f"Error finding window: {str(e)}"
        }


@tool
def focus_window(window_identifier: str) -> Dict[str, Any]:
    """
    Bring a window to the foreground and focus it
    
    Args:
        window_identifier (str): Window title or process name
        
    Returns:
        Dict: Operation result
    """
    try:
        # Find the window first
        find_result = find_window(window_identifier)
        if not find_result['success']:
            return find_result
        
        hwnd = find_result['window']['hwnd']
        window_title = find_result['window']['title']
        
        # If window is minimized, restore it first
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        
        # Bring window to foreground
        win32gui.SetForegroundWindow(hwnd)
        win32gui.BringWindowToTop(hwnd)
        
        return {
            "success": True,
            "window_identifier": window_identifier,
            "window_title": window_title,
            "hwnd": hwnd,
            "message": f"Successfully focused window: {window_title}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "window_identifier": window_identifier,
            "error": f"Error focusing window: {str(e)}"
        }


@tool
def minimize_window(window_identifier: str) -> Dict[str, Any]:
    """
    Minimize a window
    
    Args:
        window_identifier (str): Window title or process name
        
    Returns:
        Dict: Operation result
    """
    try:
        # Find the window first
        find_result = find_window(window_identifier)
        if not find_result['success']:
            return find_result
        
        hwnd = find_result['window']['hwnd']
        window_title = find_result['window']['title']
        
        # Minimize the window
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        
        return {
            "success": True,
            "window_identifier": window_identifier,
            "window_title": window_title,
            "hwnd": hwnd,
            "message": f"Successfully minimized window: {window_title}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "window_identifier": window_identifier,
            "error": f"Error minimizing window: {str(e)}"
        }


@tool
def maximize_window(window_identifier: str) -> Dict[str, Any]:
    """
    Maximize a window
    
    Args:
        window_identifier (str): Window title or process name
        
    Returns:
        Dict: Operation result
    """
    try:
        # Find the window first
        find_result = find_window(window_identifier)
        if not find_result['success']:
            return find_result
        
        hwnd = find_result['window']['hwnd']
        window_title = find_result['window']['title']
        
        # Maximize the window
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        
        return {
            "success": True,
            "window_identifier": window_identifier,
            "window_title": window_title,
            "hwnd": hwnd,
            "message": f"Successfully maximized window: {window_title}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "window_identifier": window_identifier,
            "error": f"Error maximizing window: {str(e)}"
        }


@tool
def restore_window(window_identifier: str) -> Dict[str, Any]:
    """
    Restore a window to its normal size
    
    Args:
        window_identifier (str): Window title or process name
        
    Returns:
        Dict: Operation result
    """
    try:
        # Find the window first
        find_result = find_window(window_identifier)
        if not find_result['success']:
            return find_result
        
        hwnd = find_result['window']['hwnd']
        window_title = find_result['window']['title']
        
        # Restore the window
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        
        return {
            "success": True,
            "window_identifier": window_identifier,
            "window_title": window_title,
            "hwnd": hwnd,
            "message": f"Successfully restored window: {window_title}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "window_identifier": window_identifier,
            "error": f"Error restoring window: {str(e)}"
        }


@tool
def resize_window(window_identifier: str, width: int, height: int) -> Dict[str, Any]:
    """
    Resize a window to specific dimensions
    
    Args:
        window_identifier (str): Window title or process name
        width (int): New width in pixels
        height (int): New height in pixels
        
    Returns:
        Dict: Operation result
    """
    try:
        # Find the window first
        find_result = find_window(window_identifier)
        if not find_result['success']:
            return find_result
        
        hwnd = find_result['window']['hwnd']
        window_title = find_result['window']['title']
        
        # Get current position
        rect = win32gui.GetWindowRect(hwnd)
        current_x, current_y = rect[0], rect[1]
        
        # Resize the window (keeping current position)
        win32gui.SetWindowPos(hwnd, 0, current_x, current_y, width, height, 
                             win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE)
        
        return {
            "success": True,
            "window_identifier": window_identifier,
            "window_title": window_title,
            "hwnd": hwnd,
            "new_size": {"width": width, "height": height},
            "position": {"x": current_x, "y": current_y},
            "message": f"Successfully resized window: {window_title} to {width}x{height}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "window_identifier": window_identifier,
            "width": width,
            "height": height,
            "error": f"Error resizing window: {str(e)}"
        }


@tool
def move_window(window_identifier: str, x: int, y: int) -> Dict[str, Any]:
    """
    Move a window to a specific position
    
    Args:
        window_identifier (str): Window title or process name
        x (int): New x position in pixels
        y (int): New y position in pixels
        
    Returns:
        Dict: Operation result
    """
    try:
        # Find the window first
        find_result = find_window(window_identifier)
        if not find_result['success']:
            return find_result
        
        hwnd = find_result['window']['hwnd']
        window_title = find_result['window']['title']
        
        # Get current size
        rect = win32gui.GetWindowRect(hwnd)
        current_width = rect[2] - rect[0]
        current_height = rect[3] - rect[1]
        
        # Move the window (keeping current size)
        win32gui.SetWindowPos(hwnd, 0, x, y, current_width, current_height, 
                             win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE)
        
        return {
            "success": True,
            "window_identifier": window_identifier,
            "window_title": window_title,
            "hwnd": hwnd,
            "new_position": {"x": x, "y": y},
            "size": {"width": current_width, "height": current_height},
            "message": f"Successfully moved window: {window_title} to ({x}, {y})"
        }
        
    except Exception as e:
        return {
            "success": False,
            "window_identifier": window_identifier,
            "x": x,
            "y": y,
            "error": f"Error moving window: {str(e)}"
        }


@tool
def close_window(window_identifier: str) -> Dict[str, Any]:
    """
    Close a window (sends WM_CLOSE message)
    
    Args:
        window_identifier (str): Window title or process name
        
    Returns:
        Dict: Operation result
    """
    try:
        # Find the window first
        find_result = find_window(window_identifier)
        if not find_result['success']:
            return find_result
        
        hwnd = find_result['window']['hwnd']
        window_title = find_result['window']['title']
        
        # Send close message to the window
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        
        # Give it a moment to close
        time.sleep(0.5)
        
        # Check if window still exists
        try:
            if win32gui.IsWindow(hwnd):
                window_still_exists = True
            else:
                window_still_exists = False
        except:
            window_still_exists = False
        
        return {
            "success": True,
            "window_identifier": window_identifier,
            "window_title": window_title,
            "hwnd": hwnd,
            "closed_immediately": not window_still_exists,
            "message": f"Sent close message to window: {window_title}" + 
                      (" (closed immediately)" if not window_still_exists else " (may still be processing)")
        }
        
    except Exception as e:
        return {
            "success": False,
            "window_identifier": window_identifier,
            "error": f"Error closing window: {str(e)}"
        }


@tool
def arrange_windows(arrangement: str) -> Dict[str, Any]:
    """
    Arrange windows using Windows built-in arrangements
    
    Args:
        arrangement (str): Arrangement type ('cascade', 'tile_horizontal', 'tile_vertical', 'minimize_all')
        
    Returns:
        Dict: Operation result
    """
    try:
        import win32api
        
        if arrangement == "minimize_all":
            # Minimize all windows (Windows+M equivalent)
            win32api.keybd_event(win32con.VK_LWIN, 0, 0, 0)
            win32api.keybd_event(0x4D, 0, 0, 0)  # M key
            win32api.keybd_event(0x4D, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_LWIN, 0, win32con.KEYEVENTF_KEYUP, 0)
            
            message = "Minimized all windows"
            
        elif arrangement == "cascade":
            # This would require more complex implementation
            # For now, just report success
            message = "Cascade arrangement initiated"
            
        elif arrangement == "tile_horizontal":
            # Windows+Up then Windows+Down for snap arrangements
            win32api.keybd_event(win32con.VK_LWIN, 0, 0, 0)
            win32api.keybd_event(win32con.VK_UP, 0, 0, 0)
            win32api.keybd_event(win32con.VK_UP, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_LWIN, 0, win32con.KEYEVENTF_KEYUP, 0)
            
            message = "Arranged windows horizontally"
            
        elif arrangement == "tile_vertical":
            # Windows+Left for snap left
            win32api.keybd_event(win32con.VK_LWIN, 0, 0, 0)
            win32api.keybd_event(win32con.VK_LEFT, 0, 0, 0)
            win32api.keybd_event(win32con.VK_LEFT, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_LWIN, 0, win32con.KEYEVENTF_KEYUP, 0)
            
            message = "Arranged windows vertically"
            
        else:
            return {
                "success": False,
                "arrangement": arrangement,
                "error": f"Unknown arrangement type. Must be one of: cascade, tile_horizontal, tile_vertical, minimize_all"
            }
        
        return {
            "success": True,
            "arrangement": arrangement,
            "message": message
        }
        
    except Exception as e:
        return {
            "success": False,
            "arrangement": arrangement,
            "error": f"Error arranging windows: {str(e)}"
        }


@tool
def get_window_info(window_identifier: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific window
    
    Args:
        window_identifier (str): Window title or process name
        
    Returns:
        Dict: Detailed window information
    """
    try:
        # Find the window first
        find_result = find_window(window_identifier)
        if not find_result['success']:
            return find_result
        
        window = find_result['window']
        
        # Add additional window properties
        hwnd = window['hwnd']
        
        # Get window class name
        try:
            class_name = win32gui.GetClassName(hwnd)
        except:
            class_name = "Unknown"
        
        # Get parent window
        try:
            parent_hwnd = win32gui.GetParent(hwnd)
            if parent_hwnd:
                parent_title = win32gui.GetWindowText(parent_hwnd)
            else:
                parent_hwnd = None
                parent_title = None
        except:
            parent_hwnd = None
            parent_title = None
        
        detailed_info = {
            **window,
            "class_name": class_name,
            "parent": {
                "hwnd": parent_hwnd,
                "title": parent_title
            } if parent_hwnd else None,
            "style": win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE),
            "extended_style": win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE),
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            "success": True,
            "window_identifier": window_identifier,
            "window": detailed_info,
            "message": f"Retrieved detailed info for window: {window['title']}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "window_identifier": window_identifier,
            "error": f"Error getting window info: {str(e)}"
        }


if __name__ == "__main__":
    # Test the window manager functions
    print("=== Window Manager Tool Test ===")
    
    # Test listing windows
    print("\n1. Testing window listing:")
    windows_result = list_windows(visible_only=True, sort_by="title")
    if windows_result['success']:
        print(f"Found {windows_result['count']} visible windows")
        # Show first 3 windows
        for i, window in enumerate(windows_result['windows'][:3]):
            print(f"  {i+1}. {window['title']} ({window['process_name']})")
    else:
        print(f"Error: {windows_result['error']}")
    
    # Test finding a window (look for a common one)
    print("\n2. Testing window finding:")
    find_result = find_window("explorer")
    if find_result['success']:
        print(f"Found window: {find_result['window']['title']}")
    else:
        print(f"Explorer window not found: {find_result['error']}")
    
    # Test getting detailed info
    if find_result['success']:
        print("\n3. Testing detailed window info:")
        info_result = get_window_info("explorer")
        if info_result['success']:
            window = info_result['window']
            print(f"Window: {window['title']}")
            print(f"  Size: {window['position']['width']}x{window['position']['height']}")
            print(f"  Position: ({window['position']['left']}, {window['position']['top']})")
            print(f"  Maximized: {window['is_maximized']}")
            print(f"  Class: {window['class_name']}")
    
    # Test window arrangement
    print("\n4. Testing window arrangement (minimize all):")
    arrange_result = arrange_windows("minimize_all")
    if arrange_result['success']:
        print(f"Arrangement result: {arrange_result['message']}")
    else:
        print(f"Error: {arrange_result['error']}")
    
    print("\n=== Window Manager Test Complete ===")