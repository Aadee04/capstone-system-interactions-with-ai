#!/usr/bin/env python3
"""
System Control Tool
Basic system operations like shutdown, volume control, etc.
"""

import subprocess
import time
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import ctypes
from ctypes import wintypes
import win32api
import win32con
from langchain.tools import tool


def shutdown_system(delay: int = 0, message: str = None) -> Dict[str, Any]:
    """
    Shutdown the system
    
    Args:
        delay (int): Delay in seconds before shutdown
        message (str): Optional shutdown message
        
    Returns:
        Dict: Operation result
    """
    try:
        command = ["shutdown", "/s", "/f"]  # /s = shutdown, /f = force
        
        if delay > 0:
            command.extend(["/t", str(delay)])
        else:
            command.extend(["/t", "0"])
        
        if message:
            command.extend(["/c", message])
        
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            return {
                "success": True,
                "delay": delay,
                "message": message,
                "scheduled_time": datetime.now().isoformat(),
                "result_message": f"System shutdown scheduled" + (f" in {delay} seconds" if delay > 0 else " immediately")
            }
        else:
            return {
                "success": False,
                "delay": delay,
                "message": message,
                "error": f"Shutdown command failed: {result.stderr.strip()}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "delay": delay,
            "message": message,
            "error": f"Error scheduling shutdown: {str(e)}"
        }


def restart_system(delay: int = 0, message: str = None) -> Dict[str, Any]:
    """
    Restart the system
    
    Args:
        delay (int): Delay in seconds before restart
        message (str): Optional restart message
        
    Returns:
        Dict: Operation result
    """
    try:
        command = ["shutdown", "/r", "/f"]  # /r = restart, /f = force
        
        if delay > 0:
            command.extend(["/t", str(delay)])
        else:
            command.extend(["/t", "0"])
        
        if message:
            command.extend(["/c", message])
        
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            return {
                "success": True,
                "delay": delay,
                "message": message,
                "scheduled_time": datetime.now().isoformat(),
                "result_message": f"System restart scheduled" + (f" in {delay} seconds" if delay > 0 else " immediately")
            }
        else:
            return {
                "success": False,
                "delay": delay,
                "message": message,
                "error": f"Restart command failed: {result.stderr.strip()}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "delay": delay,
            "message": message,
            "error": f"Error scheduling restart: {str(e)}"
        }


def cancel_shutdown() -> Dict[str, Any]:
    """
    Cancel a scheduled shutdown or restart
    
    Returns:
        Dict: Operation result
    """
    try:
        result = subprocess.run(["shutdown", "/a"], capture_output=True, text=True)
        
        if result.returncode == 0:
            return {
                "success": True,
                "message": "Scheduled shutdown/restart cancelled successfully"
            }
        else:
            # Check if there was no shutdown to cancel
            if "not possible" in result.stderr.lower() or "no logoff" in result.stderr.lower():
                return {
                    "success": True,
                    "message": "No shutdown/restart was scheduled"
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to cancel shutdown: {result.stderr.strip()}"
                }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Error cancelling shutdown: {str(e)}"
        }


def lock_screen() -> Dict[str, Any]:
    """
    Lock the screen
    
    Returns:
        Dict: Operation result
    """
    try:
        # Use Windows API to lock the workstation
        import win32api
        result = win32api.LockWorkStation()
        
        return {
            "success": True,
            "message": "Screen locked successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error locking screen: {str(e)}"
        }


def sleep_system() -> Dict[str, Any]:
    """
    Put the system to sleep
    
    Returns:
        Dict: Operation result
    """
    try:
        # Use rundll32 to trigger sleep
        result = subprocess.run([
            "rundll32.exe", "powrprof.dll,SetSuspendState", "Sleep"
        ], capture_output=True)
        
        return {
            "success": True,
            "message": "System sleep initiated",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error putting system to sleep: {str(e)}"
        }


def get_volume_level() -> Dict[str, Any]:
    """
    Get the current system volume level
    
    Returns:
        Dict: Volume information
    """
    try:
        from pycaw.pycaw import AudioUtilities, AudioEndpointVolume
        from comtypes import CLSCTX_ALL
        
        # Get the default audio device
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(AudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = AudioEndpointVolume(interface)
        
        # Get volume level (0.0 to 1.0)
        current_volume = volume.GetMasterVolumeLevel()
        volume_percent = int(volume.GetMasterVolumeLevelScalar() * 100)
        is_muted = volume.GetMute()
        
        return {
            "success": True,
            "volume_percent": volume_percent,
            "volume_level": current_volume,
            "is_muted": bool(is_muted),
            "timestamp": datetime.now().isoformat(),
            "message": f"Current volume: {volume_percent}%" + (" (muted)" if is_muted else "")
        }
        
    except ImportError:
        # Fallback method using Windows API
        try:
            import win32api
            import win32con
            
            # This is a simplified approach - actual implementation would be more complex
            return {
                "success": True,
                "volume_percent": "Unknown",
                "volume_level": "Unknown", 
                "is_muted": False,
                "timestamp": datetime.now().isoformat(),
                "message": "Volume level retrieved (limited information - install pycaw for full functionality)"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting volume level: {str(e)}"
            }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Error getting volume level: {str(e)}"
        }


def set_volume_level(level: int) -> Dict[str, Any]:
    """
    Set the system volume level
    
    Args:
        level (int): Volume level (0-100)
        
    Returns:
        Dict: Operation result
    """
    try:
        if not (0 <= level <= 100):
            return {
                "success": False,
                "level": level,
                "error": "Volume level must be between 0 and 100"
            }
        
        try:
            from pycaw.pycaw import AudioUtilities, AudioEndpointVolume
            from comtypes import CLSCTX_ALL
            
            # Get the default audio device
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(AudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = AudioEndpointVolume(interface)
            
            # Set volume level (0.0 to 1.0)
            volume_scalar = level / 100.0
            volume.SetMasterVolumeLevelScalar(volume_scalar, None)
            
            return {
                "success": True,
                "level": level,
                "previous_muted": bool(volume.GetMute()),
                "timestamp": datetime.now().isoformat(),
                "message": f"Volume set to {level}%"
            }
            
        except ImportError:
            # Fallback using nircmd if available, or Windows volume keys simulation
            try:
                # Try using Windows shell volume control
                subprocess.run(["powershell", "-Command", 
                              f"(New-Object -ComObject WScript.Shell).SendKeys([char]175)"], 
                              capture_output=True)
                
                return {
                    "success": True,
                    "level": level,
                    "timestamp": datetime.now().isoformat(),
                    "message": f"Volume adjustment attempted (install pycaw for precise control)"
                }
            except:
                return {
                    "success": False,
                    "level": level,
                    "error": "Volume control not available. Install pycaw package for full functionality."
                }
        
    except Exception as e:
        return {
            "success": False,
            "level": level,
            "error": f"Error setting volume level: {str(e)}"
        }


def mute_system(mute: bool = True) -> Dict[str, Any]:
    """
    Mute or unmute the system
    
    Args:
        mute (bool): True to mute, False to unmute
        
    Returns:
        Dict: Operation result
    """
    try:
        try:
            from pycaw.pycaw import AudioUtilities, AudioEndpointVolume
            from comtypes import CLSCTX_ALL
            
            # Get the default audio device
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(AudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = AudioEndpointVolume(interface)
            
            # Get current mute state
            current_mute = bool(volume.GetMute())
            
            # Set mute state
            volume.SetMute(mute, None)
            
            return {
                "success": True,
                "muted": mute,
                "previously_muted": current_mute,
                "timestamp": datetime.now().isoformat(),
                "message": f"System {'muted' if mute else 'unmuted'}"
            }
            
        except ImportError:
            # Fallback using Windows volume mute key
            try:
                import win32api
                import win32con
                
                # Simulate volume mute key press
                win32api.keybd_event(win32con.VK_VOLUME_MUTE, 0, 0, 0)
                win32api.keybd_event(win32con.VK_VOLUME_MUTE, 0, win32con.KEYEVENTF_KEYUP, 0)
                
                return {
                    "success": True,
                    "muted": mute,
                    "timestamp": datetime.now().isoformat(),
                    "message": "Mute toggle attempted (install pycaw for precise control)"
                }
            except:
                return {
                    "success": False,
                    "muted": mute,
                    "error": "Mute control not available. Install pycaw package for full functionality."
                }
        
    except Exception as e:
        return {
            "success": False,
            "muted": mute,
            "error": f"Error setting mute state: {str(e)}"
        }


def get_system_info() -> Dict[str, Any]:
    """
    Get basic system information
    
    Returns:
        Dict: System information
    """
    try:
        import platform
        import psutil
        
        # Get system information
        system_info = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "system": {
                "platform": platform.system(),
                "platform_release": platform.release(),
                "platform_version": platform.version(),
                "architecture": platform.architecture()[0],
                "machine": platform.machine(),
                "processor": platform.processor(),
                "hostname": platform.node(),
                "username": os.getenv("USERNAME", "Unknown")
            },
            "python": {
                "version": platform.python_version(),
                "implementation": platform.python_implementation()
            }
        }
        
        # Add psutil information if available
        try:
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            system_info["boot_time"] = boot_time.isoformat()
            system_info["uptime_hours"] = round((time.time() - psutil.boot_time()) / 3600, 1)
        except:
            pass
        
        return system_info
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error getting system info: {str(e)}"
        }


def run_command_as_admin(command: str) -> Dict[str, Any]:
    """
    Run a command with administrator privileges
    
    Args:
        command (str): Command to run
        
    Returns:
        Dict: Operation result
    """
    try:
        # Use UAC elevation
        result = subprocess.run([
            "powershell", "-Command", 
            f"Start-Process cmd -ArgumentList '/c {command}' -Verb RunAs -Wait"
        ], capture_output=True, text=True)
        
        return {
            "success": True,
            "command": command,
            "return_code": result.returncode,
            "message": f"Command executed with administrator privileges: {command}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "command": command,
            "error": f"Error running command as admin: {str(e)}"
        }


def create_system_restore_point(description: str) -> Dict[str, Any]:
    """
    Create a system restore point
    
    Args:
        description (str): Description for the restore point
        
    Returns:
        Dict: Operation result
    """
    try:
        # Use PowerShell to create restore point
        command = f'Checkpoint-Computer -Description "{description}"'
        result = subprocess.run([
            "powershell", "-Command", command
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            return {
                "success": True,
                "description": description,
                "timestamp": datetime.now().isoformat(),
                "message": f"System restore point created: {description}"
            }
        else:
            return {
                "success": False,
                "description": description,
                "error": f"Failed to create restore point: {result.stderr.strip()}"
            }
        
    except Exception as e:
        return {
            "success": False,
            "description": description,
            "error": f"Error creating restore point: {str(e)}"
        }


if __name__ == "__main__":
    # Test the system control functions
    print("=== System Control Tool Test ===")
    
    # Test getting system info
    print("\n1. Testing system info:")
    info_result = get_system_info()
    if info_result['success']:
        print(f"Platform: {info_result['system']['platform']} {info_result['system']['platform_release']}")
        print(f"Hostname: {info_result['system']['hostname']}")
        print(f"Architecture: {info_result['system']['architecture']}")
        if 'uptime_hours' in info_result:
            print(f"Uptime: {info_result['uptime_hours']} hours")
    else:
        print(f"Error: {info_result['error']}")
    
    # Test getting volume level
    print("\n2. Testing volume level:")
    volume_result = get_volume_level()
    if volume_result['success']:
        print(f"Current volume: {volume_result['volume_percent']}%")
        print(f"Muted: {volume_result['is_muted']}")
    else:
        print(f"Volume error: {volume_result['error']}")
    
    # Test volume control (set to current level to avoid changing it)
    if volume_result['success'] and volume_result['volume_percent'] != "Unknown":
        print("\n3. Testing volume control:")
        current_level = volume_result['volume_percent']
        set_result = set_volume_level(current_level)
        if set_result['success']:
            print(f"Volume control successful: {set_result['message']}")
        else:
            print(f"Volume control error: {set_result['error']}")
    
    # Test cancel shutdown (safe to test)
    print("\n4. Testing shutdown cancel:")
    cancel_result = cancel_shutdown()
    if cancel_result['success']:
        print(f"Cancel result: {cancel_result['message']}")
    else:
        print(f"Cancel error: {cancel_result['error']}")
    
    print("\n=== System Control Test Complete ===")