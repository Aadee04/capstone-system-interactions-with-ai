#!/usr/bin/env python3
"""
Process Manager Tool
Comprehensive application and system process management
"""

import psutil
import subprocess
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import os
import signal
from langchain.tools import tool


@tool
def list_running_apps(include_system: bool = False, sort_by: str = "name") -> Dict[str, Any]:
    """
    List all running applications
    
    Args:
        include_system (bool): Include system processes
        sort_by (str): Sort by 'name', 'cpu', 'memory', or 'pid'
        
    Returns:
        Dict: List of running applications with details
    """
    try:
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'exe', 'cpu_percent', 'memory_percent', 
                                        'create_time', 'status', 'cmdline']):
            try:
                pinfo = proc.info
                
                # Skip system processes unless requested
                if not include_system:
                    if (not pinfo['exe'] or 
                        pinfo['name'].startswith(('svchost', 'System', 'Registry', 'dwm', 'csrss', 'winlogon'))):
                        continue
                
                # Get CPU percentage (may need a moment to calculate)
                cpu_percent = proc.cpu_percent()
                
                process_info = {
                    'pid': pinfo['pid'],
                    'name': pinfo['name'],
                    'exe_path': pinfo['exe'] if pinfo['exe'] else 'N/A',
                    'cpu_percent': round(cpu_percent, 1),
                    'memory_percent': round(pinfo['memory_percent'], 1),
                    'memory_mb': round(proc.memory_info().rss / (1024*1024), 1),
                    'status': pinfo['status'],
                    'created': datetime.fromtimestamp(pinfo['create_time']).isoformat(),
                    'command_line': ' '.join(pinfo['cmdline']) if pinfo['cmdline'] else 'N/A'
                }
                
                processes.append(process_info)
                
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        # Sort processes
        if sort_by == "cpu":
            processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        elif sort_by == "memory":
            processes.sort(key=lambda x: x['memory_percent'], reverse=True)
        elif sort_by == "pid":
            processes.sort(key=lambda x: x['pid'])
        else:  # sort by name (default)
            processes.sort(key=lambda x: x['name'].lower())
        
        return {
            "success": True,
            "processes": processes,
            "count": len(processes),
            "include_system": include_system,
            "sort_by": sort_by,
            "message": f"Found {len(processes)} running {'processes' if include_system else 'applications'}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "processes": [],
            "count": 0,
            "error": f"Error listing processes: {str(e)}"
        }


@tool
def get_process_info(process_identifier: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific process
    
    Args:
        process_identifier (str): Process name or PID
        
    Returns:
        Dict: Detailed process information
    """
    try:
        target_proc = None
        
        # Try to find process by PID first
        if process_identifier.isdigit():
            try:
                target_proc = psutil.Process(int(process_identifier))
            except psutil.NoSuchProcess:
                pass
        
        # If not found by PID, search by name
        if target_proc is None:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'].lower() == process_identifier.lower():
                        target_proc = proc
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        
        if target_proc is None:
            return {
                "success": False,
                "process_identifier": process_identifier,
                "error": f"Process not found: {process_identifier}"
            }
        
        # Get detailed process information
        with target_proc.oneshot():
            proc_info = {
                "success": True,
                "pid": target_proc.pid,
                "name": target_proc.name(),
                "exe_path": target_proc.exe() if target_proc.exe() else "N/A",
                "status": target_proc.status(),
                "cpu_percent": round(target_proc.cpu_percent(), 1),
                "memory_percent": round(target_proc.memory_percent(), 1),
                "memory_info": {
                    "rss_mb": round(target_proc.memory_info().rss / (1024*1024), 1),
                    "vms_mb": round(target_proc.memory_info().vms / (1024*1024), 1)
                },
                "created": datetime.fromtimestamp(target_proc.create_time()).isoformat(),
                "parent_pid": target_proc.ppid(),
                "num_threads": target_proc.num_threads(),
                "command_line": target_proc.cmdline(),
                "working_directory": target_proc.cwd() if target_proc.cwd() else "N/A",
                "username": target_proc.username() if target_proc.username() else "N/A"
            }
            
            # Get child processes
            try:
                children = target_proc.children()
                proc_info["children"] = [{"pid": child.pid, "name": child.name()} for child in children]
                proc_info["child_count"] = len(children)
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                proc_info["children"] = []
                proc_info["child_count"] = 0
            
            return proc_info
        
    except psutil.AccessDenied:
        return {
            "success": False,
            "process_identifier": process_identifier,
            "error": f"Access denied: Cannot access process information for {process_identifier}"
        }
    except Exception as e:
        return {
            "success": False,
            "process_identifier": process_identifier,
            "error": f"Error getting process info: {str(e)}"
        }


@tool
def close_application(app_name: str, force: bool = False) -> Dict[str, Any]:
    """
    Close an application gracefully or forcefully
    
    Args:
        app_name (str): Application name or PID
        force (bool): Force close if graceful close fails
        
    Returns:
        Dict: Operation result with success status
    """
    try:
        target_processes = []
        
        # Find processes by name or PID
        if app_name.isdigit():
            try:
                proc = psutil.Process(int(app_name))
                target_processes.append(proc)
            except psutil.NoSuchProcess:
                return {
                    "success": False,
                    "app_name": app_name,
                    "error": f"Process with PID {app_name} not found"
                }
        else:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if app_name.lower() in proc.info['name'].lower():
                        target_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        
        if not target_processes:
            return {
                "success": False,
                "app_name": app_name,
                "error": f"No processes found matching: {app_name}"
            }
        
        closed_processes = []
        failed_processes = []
        
        for proc in target_processes:
            try:
                proc_name = proc.name()
                proc_pid = proc.pid
                
                if force:
                    # Force kill
                    proc.kill()
                else:
                    # Graceful termination
                    proc.terminate()
                    
                    # Wait for process to end
                    try:
                        proc.wait(timeout=5)  # Wait up to 5 seconds
                    except psutil.TimeoutExpired:
                        # If timeout, force kill
                        proc.kill()
                
                closed_processes.append({
                    "name": proc_name,
                    "pid": proc_pid,
                    "method": "force_killed" if force else "terminated"
                })
                
            except psutil.AccessDenied:
                failed_processes.append({
                    "name": proc.name(),
                    "pid": proc.pid,
                    "error": "Access denied"
                })
            except psutil.NoSuchProcess:
                # Process already ended
                closed_processes.append({
                    "name": proc.name(),
                    "pid": proc.pid,
                    "method": "already_ended"
                })
            except Exception as e:
                failed_processes.append({
                    "name": proc.name(),
                    "pid": proc.pid,
                    "error": str(e)
                })
        
        success = len(closed_processes) > 0
        
        return {
            "success": success,
            "app_name": app_name,
            "force": force,
            "closed_processes": closed_processes,
            "failed_processes": failed_processes,
            "message": f"Closed {len(closed_processes)} processes, {len(failed_processes)} failed"
        }
        
    except Exception as e:
        return {
            "success": False,
            "app_name": app_name,
            "error": f"Error closing application: {str(e)}"
        }


@tool
def get_system_resources() -> Dict[str, Any]:
    """
    Get current system resource usage
    
    Returns:
        Dict: System resource information
    """
    try:
        # CPU information
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        # Memory information
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Disk information
        disk_usage = psutil.disk_usage('/')
        
        # Network information (basic)
        network_io = psutil.net_io_counters()
        
        # Process counts
        process_count = len(psutil.pids())
        
        # Boot time
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime_seconds = time.time() - psutil.boot_time()
        uptime_hours = uptime_seconds / 3600
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "usage_percent": cpu_percent,
                "core_count": cpu_count,
                "frequency_mhz": round(cpu_freq.current) if cpu_freq else "N/A"
            },
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "usage_percent": memory.percent
            },
            "swap": {
                "total_gb": round(swap.total / (1024**3), 2),
                "used_gb": round(swap.used / (1024**3), 2),
                "usage_percent": swap.percent
            },
            "disk": {
                "total_gb": round(disk_usage.total / (1024**3), 2),
                "used_gb": round(disk_usage.used / (1024**3), 2),
                "free_gb": round(disk_usage.free / (1024**3), 2),
                "usage_percent": round((disk_usage.used / disk_usage.total) * 100, 1)
            },
            "network": {
                "bytes_sent_mb": round(network_io.bytes_sent / (1024**2), 2),
                "bytes_received_mb": round(network_io.bytes_recv / (1024**2), 2)
            },
            "system": {
                "process_count": process_count,
                "boot_time": boot_time.isoformat(),
                "uptime_hours": round(uptime_hours, 1)
            },
            "message": f"System resources: {cpu_percent}% CPU, {memory.percent}% RAM, {process_count} processes"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error getting system resources: {str(e)}"
        }


@tool
def set_process_priority(process_identifier: str, priority: str) -> Dict[str, Any]:
    """
    Set the priority of a process
    
    Args:
        process_identifier (str): Process name or PID
        priority (str): Priority level ('low', 'below_normal', 'normal', 'above_normal', 'high')
        
    Returns:
        Dict: Operation result with success status
    """
    try:
        # Map priority strings to psutil constants
        priority_map = {
            'low': psutil.IDLE_PRIORITY_CLASS,
            'below_normal': psutil.BELOW_NORMAL_PRIORITY_CLASS,
            'normal': psutil.NORMAL_PRIORITY_CLASS,
            'above_normal': psutil.ABOVE_NORMAL_PRIORITY_CLASS,
            'high': psutil.HIGH_PRIORITY_CLASS
        }
        
        if priority.lower() not in priority_map:
            return {
                "success": False,
                "process_identifier": process_identifier,
                "priority": priority,
                "error": f"Invalid priority. Must be one of: {list(priority_map.keys())}"
            }
        
        priority_value = priority_map[priority.lower()]
        target_proc = None
        
        # Find process by PID or name
        if process_identifier.isdigit():
            try:
                target_proc = psutil.Process(int(process_identifier))
            except psutil.NoSuchProcess:
                pass
        
        if target_proc is None:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'].lower() == process_identifier.lower():
                        target_proc = proc
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        
        if target_proc is None:
            return {
                "success": False,
                "process_identifier": process_identifier,
                "priority": priority,
                "error": f"Process not found: {process_identifier}"
            }
        
        # Set the priority
        old_priority = target_proc.nice()
        target_proc.nice(priority_value)
        
        return {
            "success": True,
            "process_identifier": process_identifier,
            "pid": target_proc.pid,
            "name": target_proc.name(),
            "old_priority": old_priority,
            "new_priority": priority,
            "message": f"Successfully set {target_proc.name()} priority to {priority}"
        }
        
    except psutil.AccessDenied:
        return {
            "success": False,
            "process_identifier": process_identifier,
            "priority": priority,
            "error": "Access denied: Cannot change process priority (may require administrator rights)"
        }
    except Exception as e:
        return {
            "success": False,
            "process_identifier": process_identifier,
            "priority": priority,
            "error": f"Error setting process priority: {str(e)}"
        }


@tool
def launch_application(app_path: str, arguments: List[str] = None, working_dir: str = None) -> Dict[str, Any]:
    """
    Launch an application
    
    Args:
        app_path (str): Path to executable or application name
        arguments (List[str]): Command line arguments
        working_dir (str): Working directory for the application
        
    Returns:
        Dict: Launch result with process information
    """
    try:
        command = [app_path]
        if arguments:
            command.extend(arguments)
        
        # Launch the process
        process = subprocess.Popen(
            command,
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give it a moment to start
        time.sleep(0.5)
        
        # Check if process is still running
        if process.poll() is None:
            # Process is running
            return {
                "success": True,
                "app_path": app_path,
                "arguments": arguments or [],
                "working_dir": working_dir,
                "pid": process.pid,
                "message": f"Successfully launched {app_path} with PID {process.pid}"
            }
        else:
            # Process ended quickly, might be an error
            stdout, stderr = process.communicate()
            return {
                "success": False,
                "app_path": app_path,
                "arguments": arguments or [],
                "working_dir": working_dir,
                "return_code": process.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "error": f"Application exited immediately with code {process.returncode}"
            }
        
    except FileNotFoundError:
        return {
            "success": False,
            "app_path": app_path,
            "arguments": arguments or [],
            "working_dir": working_dir,
            "error": f"Application not found: {app_path}"
        }
    except PermissionError:
        return {
            "success": False,
            "app_path": app_path,
            "arguments": arguments or [],
            "working_dir": working_dir,
            "error": f"Permission denied: Cannot launch {app_path}"
        }
    except Exception as e:
        return {
            "success": False,
            "app_path": app_path,
            "arguments": arguments or [],
            "working_dir": working_dir,
            "error": f"Error launching application: {str(e)}"
        }


if __name__ == "__main__":
    # Test the process manager functions
    print("=== Process Manager Tool Test ===")
    
    # Test system resources
    print("\n1. Testing system resources:")
    resources = get_system_resources()
    if resources['success']:
        print(f"CPU: {resources['cpu']['usage_percent']}%, RAM: {resources['memory']['usage_percent']}%")
        print(f"Processes: {resources['system']['process_count']}, Uptime: {resources['system']['uptime_hours']} hours")
    else:
        print(f"Error: {resources['error']}")
    
    # Test listing applications
    print("\n2. Testing application listing:")
    apps = list_running_apps(include_system=False, sort_by="memory")
    if apps['success']:
        print(f"Found {apps['count']} running applications")
        # Show top 3 by memory usage
        for i, app in enumerate(apps['processes'][:3]):
            print(f"  {i+1}. {app['name']}: {app['memory_percent']}% RAM, {app['cpu_percent']}% CPU")
    else:
        print(f"Error: {apps['error']}")
    
    # Test getting process info for a common process
    if apps['success'] and apps['count'] > 0:
        print("\n3. Testing process info:")
        first_app = apps['processes'][0]
        proc_info = get_process_info(str(first_app['pid']))
        if proc_info['success']:
            print(f"Process {proc_info['name']} (PID {proc_info['pid']}):")
            print(f"  Memory: {proc_info['memory_info']['rss_mb']} MB")
            print(f"  Threads: {proc_info['num_threads']}")
            print(f"  Children: {proc_info['child_count']}")
    
    print("\n=== Process Manager Test Complete ===")