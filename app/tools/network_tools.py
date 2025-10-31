#!/usr/bin/env python3
"""
Network Tools
Network connectivity, WiFi management, and network operations
"""

import subprocess
import socket
import time
import requests
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import psutil
import re
from langchain.tools import tool


@tool
def get_network_status() -> Dict[str, Any]:
    """
    Get comprehensive network status information
    
    Returns:
        Dict: Network status and information
    """
    try:
        status = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "interfaces": [],
            "connectivity": {},
            "dns": {},
            "public_ip": None
        }
        
        # Get network interfaces
        interfaces = psutil.net_if_addrs()
        interface_stats = psutil.net_if_stats()
        
        for interface_name, addresses in interfaces.items():
            if interface_name in interface_stats:
                stats = interface_stats[interface_name]
                
                interface_info = {
                    "name": interface_name,
                    "is_up": stats.isup,
                    "speed": stats.speed if stats.speed > 0 else "Unknown",
                    "mtu": stats.mtu,
                    "addresses": []
                }
                
                for addr in addresses:
                    addr_info = {
                        "family": str(addr.family),
                        "address": addr.address,
                        "netmask": getattr(addr, 'netmask', None),
                        "broadcast": getattr(addr, 'broadcast', None)
                    }
                    interface_info["addresses"].append(addr_info)
                
                status["interfaces"].append(interface_info)
        
        # Test internet connectivity
        try:
            response = requests.get("http://httpbin.org/ip", timeout=5)
            if response.status_code == 200:
                status["connectivity"]["internet"] = True
                status["public_ip"] = response.json().get("origin")
            else:
                status["connectivity"]["internet"] = False
        except:
            status["connectivity"]["internet"] = False
        
        # Test DNS resolution
        try:
            socket.gethostbyname("google.com")
            status["dns"]["working"] = True
        except:
            status["dns"]["working"] = False
        
        # Get DNS servers
        try:
            result = subprocess.run(["nslookup", "google.com"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # Parse DNS servers from nslookup output
                dns_servers = []
                for line in result.stdout.split('\n'):
                    if 'Server:' in line:
                        server = line.split(':')[-1].strip()
                        if server:
                            dns_servers.append(server)
                status["dns"]["servers"] = dns_servers
        except:
            status["dns"]["servers"] = []
        
        return status
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error getting network status: {str(e)}"
        }


@tool
def ping_host(hostname: str, count: int = 4, timeout: int = 5) -> Dict[str, Any]:
    """
    Ping a host to test connectivity
    
    Args:
        hostname (str): Hostname or IP address to ping
        count (int): Number of ping packets to send
        timeout (int): Timeout in seconds
        
    Returns:
        Dict: Ping results
    """
    try:
        # Use Windows ping command
        command = ["ping", "-n", str(count), "-w", str(timeout * 1000), hostname]
        
        start_time = time.time()
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout + 10)
        end_time = time.time()
        
        success = result.returncode == 0
        output = result.stdout
        
        # Parse ping statistics
        stats = {
            "packets_sent": count,
            "packets_received": 0,
            "packet_loss_percent": 100,
            "min_time": None,
            "max_time": None,
            "avg_time": None
        }
        
        if success and output:
            # Parse Windows ping output
            lines = output.split('\n')
            
            # Look for statistics
            for line in lines:
                if "Received =" in line:
                    # Parse: Packets: Sent = 4, Received = 4, Lost = 0 (0% loss)
                    parts = line.split(',')
                    for part in parts:
                        if "Received =" in part:
                            stats["packets_received"] = int(part.split('=')[1].strip())
                        elif "Lost =" in part:
                            lost_part = part.split('=')[1].strip()
                            lost_count = int(lost_part.split()[0])
                            if count > 0:
                                stats["packet_loss_percent"] = (lost_count / count) * 100
                
                if "Minimum =" in line:
                    # Parse: Minimum = 1ms, Maximum = 3ms, Average = 2ms
                    parts = line.split(',')
                    for part in parts:
                        if "Minimum =" in part:
                            stats["min_time"] = part.split('=')[1].strip().replace('ms', '').strip()
                        elif "Maximum =" in part:
                            stats["max_time"] = part.split('=')[1].strip().replace('ms', '').strip()
                        elif "Average =" in part:
                            stats["avg_time"] = part.split('=')[1].strip().replace('ms', '').strip()
        
        return {
            "success": True,
            "hostname": hostname,
            "reachable": success,
            "total_time": round(end_time - start_time, 2),
            "statistics": stats,
            "raw_output": output,
            "message": f"Ping to {hostname}: {'Success' if success else 'Failed'}"
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "hostname": hostname,
            "reachable": False,
            "error": f"Ping to {hostname} timed out after {timeout} seconds"
        }
    except Exception as e:
        return {
            "success": False,
            "hostname": hostname,
            "reachable": False,
            "error": f"Error pinging {hostname}: {str(e)}"
        }


@tool
def get_wifi_networks() -> Dict[str, Any]:
    """
    Get available WiFi networks
    
    Returns:
        Dict: Available WiFi networks
    """
    try:
        # Use netsh to get WiFi profiles and available networks
        command = ["netsh", "wlan", "show", "profiles"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        
        saved_networks = []
        if result.returncode == 0:
            # Parse saved profiles
            for line in result.stdout.split('\n'):
                if "All User Profile" in line:
                    profile_name = line.split(':')[1].strip()
                    saved_networks.append(profile_name)
        
        # Get available networks
        command = ["netsh", "wlan", "show", "interfaces"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        
        current_connection = None
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if "SSID" in line and "BSSID" not in line:
                    current_connection = line.split(':')[1].strip()
                    break
        
        # Get available networks scan
        command = ["netsh", "wlan", "show", "network", "mode=bssid"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        
        available_networks = []
        if result.returncode == 0:
            current_network = {}
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line.startswith("SSID") and ":" in line:
                    if current_network:
                        available_networks.append(current_network)
                    current_network = {
                        "ssid": line.split(':', 1)[1].strip(),
                        "signal": None,
                        "authentication": None,
                        "encryption": None,
                        "is_saved": False,
                        "is_connected": False
                    }
                elif line.startswith("Signal") and current_network:
                    signal_str = line.split(':', 1)[1].strip()
                    current_network["signal"] = signal_str
                elif line.startswith("Authentication") and current_network:
                    current_network["authentication"] = line.split(':', 1)[1].strip()
                elif line.startswith("Encryption") and current_network:
                    current_network["encryption"] = line.split(':', 1)[1].strip()
            
            # Add the last network
            if current_network:
                available_networks.append(current_network)
            
            # Mark saved and connected networks
            for network in available_networks:
                network["is_saved"] = network["ssid"] in saved_networks
                network["is_connected"] = network["ssid"] == current_connection
        
        return {
            "success": True,
            "current_connection": current_connection,
            "saved_networks": saved_networks,
            "available_networks": available_networks,
            "scan_timestamp": datetime.now().isoformat(),
            "message": f"Found {len(available_networks)} available networks, {len(saved_networks)} saved profiles"
        }
        
    except Exception as e:
        return {
            "success": False,
            "current_connection": None,
            "saved_networks": [],
            "available_networks": [],
            "error": f"Error getting WiFi networks: {str(e)}"
        }


@tool
def connect_to_wifi(ssid: str, password: str = None) -> Dict[str, Any]:
    """
    Connect to a WiFi network
    
    Args:
        ssid (str): Network SSID
        password (str): Network password (if required)
        
    Returns:
        Dict: Connection result
    """
    try:
        # First check if the network profile already exists
        command = ["netsh", "wlan", "show", "profiles", f"name={ssid}"]
        result = subprocess.run(command, capture_output=True, text=True)
        
        profile_exists = result.returncode == 0
        
        if not profile_exists and password:
            # Create a new profile
            profile_xml = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{ssid}</name>
    <SSIDConfig>
        <SSID>
            <name>{ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{password}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>"""
            
            # Save profile to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
                f.write(profile_xml)
                profile_path = f.name
            
            try:
                # Add the profile
                command = ["netsh", "wlan", "add", "profile", f"filename={profile_path}"]
                result = subprocess.run(command, capture_output=True, text=True)
                
                if result.returncode != 0:
                    return {
                        "success": False,
                        "ssid": ssid,
                        "error": f"Failed to create WiFi profile: {result.stderr}"
                    }
            finally:
                # Clean up temp file
                try:
                    import os
                    os.unlink(profile_path)
                except:
                    pass
        
        # Connect to the network
        command = ["netsh", "wlan", "connect", f"name={ssid}"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            # Wait a moment and check connection status
            time.sleep(3)
            
            # Verify connection
            status_result = get_wifi_networks()
            if status_result["success"]:
                is_connected = status_result["current_connection"] == ssid
                
                return {
                    "success": True,
                    "ssid": ssid,
                    "connected": is_connected,
                    "profile_created": not profile_exists,
                    "timestamp": datetime.now().isoformat(),
                    "message": f"{'Connected to' if is_connected else 'Attempted connection to'} WiFi network: {ssid}"
                }
            else:
                return {
                    "success": True,
                    "ssid": ssid,
                    "connected": None,
                    "profile_created": not profile_exists,
                    "timestamp": datetime.now().isoformat(),
                    "message": f"Connection command sent to WiFi network: {ssid} (status unknown)"
                }
        else:
            return {
                "success": False,
                "ssid": ssid,
                "connected": False,
                "error": f"Failed to connect to WiFi: {result.stderr.strip()}"
            }
        
    except Exception as e:
        return {
            "success": False,
            "ssid": ssid,
            "connected": False,
            "error": f"Error connecting to WiFi: {str(e)}"
        }


@tool
def disconnect_wifi() -> Dict[str, Any]:
    """
    Disconnect from current WiFi network
    
    Returns:
        Dict: Operation result
    """
    try:
        command = ["netsh", "wlan", "disconnect"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "message": "Disconnected from WiFi network"
            }
        else:
            return {
                "success": False,
                "error": f"Failed to disconnect from WiFi: {result.stderr.strip()}"
            }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error disconnecting from WiFi: {str(e)}"
        }


@tool
def get_network_usage() -> Dict[str, Any]:
    """
    Get network usage statistics
    
    Returns:
        Dict: Network usage information
    """
    try:
        # Get network I/O statistics
        net_io = psutil.net_io_counters()
        
        # Get per-interface statistics
        net_io_per_interface = psutil.net_io_counters(pernic=True)
        
        interface_stats = []
        for interface, stats in net_io_per_interface.items():
            interface_stats.append({
                "interface": interface,
                "bytes_sent": stats.bytes_sent,
                "bytes_received": stats.bytes_recv,
                "packets_sent": stats.packets_sent,
                "packets_received": stats.packets_recv,
                "errors_in": stats.errin,
                "errors_out": stats.errout,
                "drops_in": stats.dropin,
                "drops_out": stats.dropout
            })
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "total": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_received": net_io.bytes_recv,
                "bytes_sent_mb": round(net_io.bytes_sent / (1024**2), 2),
                "bytes_received_mb": round(net_io.bytes_recv / (1024**2), 2),
                "packets_sent": net_io.packets_sent,
                "packets_received": net_io.packets_recv
            },
            "interfaces": interface_stats,
            "message": f"Network usage: {round(net_io.bytes_sent / (1024**2), 2)} MB sent, {round(net_io.bytes_recv / (1024**2), 2)} MB received"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error getting network usage: {str(e)}"
        }


@tool
def test_internet_speed() -> Dict[str, Any]:
    """
    Test internet connection speed (basic test)
    
    Returns:
        Dict: Speed test results
    """
    try:
        # Simple download speed test using a small file
        test_url = "http://httpbin.org/bytes/1048576"  # 1MB file
        
        start_time = time.time()
        response = requests.get(test_url, timeout=30)
        end_time = time.time()
        
        if response.status_code == 200:
            download_time = end_time - start_time
            file_size_mb = len(response.content) / (1024**2)
            speed_mbps = (file_size_mb * 8) / download_time  # Convert to Mbps
            
            return {
                "success": True,
                "download_speed_mbps": round(speed_mbps, 2),
                "download_time_seconds": round(download_time, 2),
                "file_size_mb": round(file_size_mb, 2),
                "timestamp": datetime.now().isoformat(),
                "message": f"Download speed: {round(speed_mbps, 2)} Mbps"
            }
        else:
            return {
                "success": False,
                "error": f"Speed test failed with HTTP {response.status_code}"
            }
        
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Speed test timed out"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error testing internet speed: {str(e)}"
        }


@tool
def send_notification(title: str, message: str, duration: int = 5) -> Dict[str, Any]:
    """
    Send a Windows notification
    
    Args:
        title (str): Notification title
        message (str): Notification message
        duration (int): Duration in seconds
        
    Returns:
        Dict: Operation result
    """
    try:
        # Use PowerShell to send Windows notification
        powershell_command = f"""
Add-Type -AssemblyName System.Windows.Forms
$notification = New-Object System.Windows.Forms.NotifyIcon
$notification.Icon = [System.Drawing.SystemIcons]::Information
$notification.Visible = $true
$notification.ShowBalloonTip({duration * 1000}, "{title}", "{message}", [System.Windows.Forms.ToolTipIcon]::Info)
Start-Sleep -Seconds {duration}
$notification.Dispose()
"""
        
        result = subprocess.run([
            "powershell", "-Command", powershell_command
        ], capture_output=True, text=True, timeout=duration + 5)
        
        return {
            "success": True,
            "title": title,
            "message": message,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
            "result_message": f"Notification sent: {title}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "title": title,
            "message": message,
            "error": f"Error sending notification: {str(e)}"
        }


if __name__ == "__main__":
    # Test the network tools
    print("=== Network Tools Test ===")
    
    # Test network status
    print("\n1. Testing network status:")
    status_result = get_network_status()
    if status_result['success']:
        print(f"Internet: {status_result['connectivity']['internet']}")
        print(f"DNS working: {status_result['dns']['working']}")
        print(f"Public IP: {status_result['public_ip']}")
        print(f"Interfaces: {len(status_result['interfaces'])}")
    else:
        print(f"Error: {status_result['error']}")
    
    # Test ping
    print("\n2. Testing ping to google.com:")
    ping_result = ping_host("google.com", count=2)
    if ping_result['success']:
        print(f"Ping successful: {ping_result['reachable']}")
        if ping_result['reachable']:
            stats = ping_result['statistics']
            print(f"Packets: {stats['packets_received']}/{stats['packets_sent']}")
            print(f"Avg time: {stats['avg_time']}")
    else:
        print(f"Ping error: {ping_result['error']}")
    
    # Test WiFi networks
    print("\n3. Testing WiFi networks:")
    wifi_result = get_wifi_networks()
    if wifi_result['success']:
        print(f"Current connection: {wifi_result['current_connection']}")
        print(f"Available networks: {len(wifi_result['available_networks'])}")
        print(f"Saved profiles: {len(wifi_result['saved_networks'])}")
    else:
        print(f"WiFi error: {wifi_result['error']}")
    
    # Test network usage
    print("\n4. Testing network usage:")
    usage_result = get_network_usage()
    if usage_result['success']:
        total = usage_result['total']
        print(f"Total sent: {total['bytes_sent_mb']} MB")
        print(f"Total received: {total['bytes_received_mb']} MB")
    else:
        print(f"Usage error: {usage_result['error']}")
    
    # Test notification
    print("\n5. Testing notification:")
    notif_result = send_notification("Test Notification", "This is a test message", 2)
    print(f"Notification result: {notif_result['success']}")
    
    print("\n=== Network Tools Test Complete ===")