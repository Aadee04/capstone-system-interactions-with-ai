#!/usr/bin/env python3
"""
Media Tools
Screenshot capture, screen recording, and media playback control
"""

import os
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import tempfile
import json
from langchain.tools import tool


@tool
def take_screenshot(save_path: str = None, region: tuple = None, 
                   include_cursor: bool = False, format: str = "PNG") -> Dict[str, Any]:
    """
    Take a screenshot of the screen
    
    Args:
        save_path (str): Path to save screenshot (auto-generated if None)
        region (tuple): Region to capture (left, top, width, height)
        include_cursor (bool): Whether to include mouse cursor
        format (str): Image format (PNG, JPEG, BMP)
        
    Returns:
        Dict: Screenshot result with file path and metadata
    """
    try:
        # Import screenshot libraries
        try:
            from PIL import ImageGrab
            from PIL import Image
        except ImportError:
            return {
                "success": False,
                "error": "Screenshot dependencies not available. Install Pillow package."
            }
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Specify the relative or absolute path to 'screenshots' directory
        screenshots_dir = Path("data/screenshots")
        screenshots_dir.mkdir(parents=True, exist_ok=True)  # Ensure the folder exists
        save_path = screenshots_dir / f"screenshot_{timestamp}.{format.lower()}"
        
        # Create directory if needed
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Take screenshot
        start_time = time.time()
        
        if region:
            # Capture specific region
            left, top, width, height = region
            bbox = (left, top, left + width, top + height)
            screenshot = ImageGrab.grab(bbox=bbox, include_layered_windows=True)
        else:
            # Capture full screen
            screenshot = ImageGrab.grab(include_layered_windows=True)
        
        # Add cursor if requested (basic implementation)
        if include_cursor:
            # This is a simplified version - full cursor capture is more complex
            pass
        
        # Save screenshot
        screenshot.save(save_path, format.upper())
        
        end_time = time.time()
        
        # Get file info
        file_size = save_path.stat().st_size
        
        return {
            "tool_success": True,
            "tool_message": f"Screenshot saved: {save_path.name} ({screenshot.width}x{screenshot.height})"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error taking screenshot: {str(e)}"
        }


@tool
def record_screen(duration: int, save_path: str = None, region: tuple = None,
                 fps: int = 10, include_audio: bool = False) -> Dict[str, Any]:
    """
    Record screen for a specified duration
    
    Args:
        duration (int): Recording duration in seconds
        save_path (str): Path to save recording (auto-generated if None)
        region (tuple): Region to record (left, top, width, height)
        fps (int): Frames per second
        include_audio (bool): Whether to include audio
        
    Returns:
        Dict: Recording result with file path and metadata
    """
    try:
        # Generate save path if not provided
        if save_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = f"screen_recording_{timestamp}.mp4"
        
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            from PIL import ImageGrab
            import cv2
            import numpy as np
        except ImportError:
            return {
                "success": False,
                "error": "Screen recording dependencies not available. Install Pillow and opencv-python packages."
            }
        
        # Prepare recording parameters
        if region:
            left, top, width, height = region
            bbox = (left, top, left + width, top + height)
        else:
            # Get screen size
            screen = ImageGrab.grab()
            width, height = screen.size
            bbox = None
        
        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(save_path), fourcc, fps, (width, height))
        
        if not out.isOpened():
            return {
                "success": False,
                "error": "Failed to initialize video writer"
            }
        
        start_time = time.time()
        frame_count = 0
        target_frames = duration * fps
        
        try:
            print(f"Recording screen for {duration} seconds at {fps} FPS...")
            
            while frame_count < target_frames:
                # Capture frame
                screenshot = ImageGrab.grab(bbox=bbox)
                
                # Convert PIL image to OpenCV format
                frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                
                # Write frame
                out.write(frame)
                frame_count += 1
                
                # Wait for next frame
                time.sleep(1.0 / fps)
                
                # Check if we should stop early
                current_time = time.time()
                if current_time - start_time >= duration:
                    break
            
        finally:
            out.release()
        
        end_time = time.time()
        actual_duration = end_time - start_time
        
        # Get file info
        if save_path.exists():
            file_size = save_path.stat().st_size
            
            return {
                "success": True,
                "file_path": str(save_path.absolute()),
                "recording_params": {
                    "duration_requested": duration,
                    "duration_actual": round(actual_duration, 2),
                    "fps": fps,
                    "region": region,
                    "size": {"width": width, "height": height}
                },
                "file_info": {
                    "size_bytes": file_size,
                    "size_mb": round(file_size / (1024*1024), 2),
                    "frames_recorded": frame_count
                },
                "include_audio": include_audio,
                "timestamp": datetime.now().isoformat(),
                "message": f"Screen recording completed: {save_path.name} ({actual_duration:.1f}s, {frame_count} frames)"
            }
        else:
            return {
                "success": False,
                "error": "Recording file was not created"
            }
        
    except Exception as e:
        return {
            "success": False,
            "save_path": str(save_path) if 'save_path' in locals() else None,
            "error": f"Error recording screen: {str(e)}"
        }

@tool
def play_media_file(file_path: str, fullscreen: bool = False, volume: int = None) -> Dict[str, Any]:
    """
    Play a media file using default system player
    
    Args:
        file_path (str): Path to media file
        fullscreen (bool): Whether to play in fullscreen
        volume (int): Volume level (0-100)
        
    Returns:
        Dict: Playback result
    """
    try:
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {
                "success": False,
                "file_path": str(file_path),
                "error": f"Media file does not exist: {file_path}"
            }
        
        # Get file info
        file_size = file_path.stat().st_size
        file_extension = file_path.suffix.lower()
        
        # Common media extensions
        video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm']
        audio_extensions = ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma']
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']
        
        if file_extension in video_extensions:
            media_type = "video"
        elif file_extension in audio_extensions:
            media_type = "audio"
        elif file_extension in image_extensions:
            media_type = "image"
        else:
            media_type = "unknown"
        
        # Use Windows default media player
        try:
            # Start the media file with default application
            command = ["start", ""]
            
            if fullscreen and media_type == "video":
                # For fullscreen, we might need specific player parameters
                # This is simplified - actual implementation would depend on default player
                pass
            
            command.append(str(file_path))
            
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "file_path": str(file_path.absolute()),
                    "media_type": media_type,
                    "file_info": {
                        "name": file_path.name,
                        "extension": file_extension,
                        "size_bytes": file_size,
                        "size_mb": round(file_size / (1024*1024), 2)
                    },
                    "playback_options": {
                        "fullscreen": fullscreen,
                        "volume": volume
                    },
                    "timestamp": datetime.now().isoformat(),
                    "message": f"Started playing {media_type}: {file_path.name}"
                }
            else:
                return {
                    "success": False,
                    "file_path": str(file_path),
                    "error": f"Failed to start media playback: {result.stderr}"
                }
            
        except Exception as e:
            return {
                "success": False,
                "file_path": str(file_path),
                "error": f"Error starting media playback: {str(e)}"
            }
        
    except Exception as e:
        return {
            "success": False,
            "file_path": str(file_path) if 'file_path' in locals() else None,
            "error": f"Error playing media file: {str(e)}"
        }

@tool
def control_media_playback(action: str, application: str = None) -> Dict[str, Any]:
    """
    Control media playback (play, pause, stop, next, previous)
    
    Args:
        action (str): Control action ('play', 'pause', 'stop', 'next', 'previous', 'volume_up', 'volume_down', 'mute')
        application (str): Specific application to control (optional)
        
    Returns:
        Dict: Control result
    """
    try:
        import win32api
        import win32con
        
        # Map actions to Windows media keys
        media_keys = {
            'play': win32con.VK_MEDIA_PLAY_PAUSE,
            'pause': win32con.VK_MEDIA_PLAY_PAUSE,
            'stop': win32con.VK_MEDIA_STOP,
            'next': win32con.VK_MEDIA_NEXT_TRACK,
            'previous': win32con.VK_MEDIA_PREV_TRACK,
            'volume_up': win32con.VK_VOLUME_UP,
            'volume_down': win32con.VK_VOLUME_DOWN,
            'mute': win32con.VK_VOLUME_MUTE
        }
        
        if action not in media_keys:
            return {
                "tool_success": False,
                "tool_error": f"Unsupported media control action. Available: {list(media_keys.keys())}"
            }
        
        # Send media key
        key_code = media_keys[action]
        
        win32api.keybd_event(key_code, 0, 0, 0)  # Key down
        win32api.keybd_event(key_code, 0, win32con.KEYEVENTF_KEYUP, 0)  # Key up
        
        return {
            "tool_success": True,
            "tool_message": f"Sent media control: {action}"
        }
        
    except Exception as e:
        return {
            "tool_success": False,
            "tool_error": f"Error controlling media: {str(e)}"
        }

@tool
def get_media_info(file_path: str) -> Dict[str, Any]:
    """
    Get information about a media file
    
    Args:
        file_path (str): Path to media file
        
    Returns:
        Dict: Media file information
    """
    try:
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {
                "success": False,
                "file_path": str(file_path),
                "error": f"Media file does not exist: {file_path}"
            }
        
        # Basic file info
        file_stat = file_path.stat()
        file_size = file_stat.st_size
        file_extension = file_path.suffix.lower()
        
        media_info = {
            "success": True,
            "file_path": str(file_path.absolute()),
            "basic_info": {
                "name": file_path.name,
                "extension": file_extension,
                "size_bytes": file_size,
                "size_mb": round(file_size / (1024*1024), 2),
                "created": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat()
            }
        }
        
        # Determine media type
        video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v']
        audio_extensions = ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a']
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        
        if file_extension in video_extensions:
            media_type = "video"
        elif file_extension in audio_extensions:
            media_type = "audio"
        elif file_extension in image_extensions:
            media_type = "image"
        else:
            media_type = "unknown"
        
        media_info["media_type"] = media_type
        
        # Try to get detailed media info using FFmpeg if available
        try:
            command = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(file_path)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                ffprobe_data = json.loads(result.stdout)
                
                # Extract format information
                if 'format' in ffprobe_data:
                    format_info = ffprobe_data['format']
                    media_info["detailed_info"] = {
                        "duration": float(format_info.get('duration', 0)),
                        "duration_formatted": str(datetime.fromtimestamp(float(format_info.get('duration', 0))) - datetime.fromtimestamp(0)).split('.')[0],
                        "bit_rate": int(format_info.get('bit_rate', 0)),
                        "format_name": format_info.get('format_name', ''),
                        "tags": format_info.get('tags', {})
                    }
                
                # Extract stream information
                if 'streams' in ffprobe_data:
                    streams = []
                    for stream in ffprobe_data['streams']:
                        stream_info = {
                            "index": stream.get('index'),
                            "codec_name": stream.get('codec_name'),
                            "codec_type": stream.get('codec_type')
                        }
                        
                        if stream.get('codec_type') == 'video':
                            stream_info.update({
                                "width": stream.get('width'),
                                "height": stream.get('height'),
                                "r_frame_rate": stream.get('r_frame_rate'),
                                "pixel_format": stream.get('pix_fmt')
                            })
                        elif stream.get('codec_type') == 'audio':
                            stream_info.update({
                                "sample_rate": stream.get('sample_rate'),
                                "channels": stream.get('channels'),
                                "channel_layout": stream.get('channel_layout')
                            })
                        
                        streams.append(stream_info)
                    
                    media_info["streams"] = streams
                    
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            # FFmpeg not available or failed
            media_info["detailed_info"] = {"error": "FFmpeg not available for detailed analysis"}
        
        # For images, try to get basic image info
        if media_type == "image":
            try:
                from PIL import Image
                with Image.open(file_path) as img:
                    media_info["image_info"] = {
                        "width": img.width,
                        "height": img.height,
                        "mode": img.mode,
                        "format": img.format
                    }
            except ImportError:
                media_info["image_info"] = {"error": "PIL not available for image analysis"}
            except Exception:
                media_info["image_info"] = {"error": "Could not analyze image"}
        
        media_info["timestamp"] = datetime.now().isoformat()
        media_info["message"] = f"Media info retrieved for {media_type}: {file_path.name}"
        
        return media_info
        
    except Exception as e:
        return {
            "success": False,
            "file_path": str(file_path) if 'file_path' in locals() else None,
            "error": f"Error getting media info: {str(e)}"
        }

@tool
def capture_webcam_photo(save_path: str = None, camera_index: int = 0) -> Dict[str, Any]:
    """
    Capture a photo of the user.
    Capture a photo from the physical webcam.
    
    Args:
        save_path (str): Path to save photo (auto-generated if None)
        camera_index (int): Camera index (0 for default camera)
        
    Returns:
        Dict: Capture result
    """
    try:
        try:
            import cv2
        except ImportError:
            return {
                "tool_success": False,
                "tool_error": "Webcam capture dependencies not available. Install opencv-python package."
            }
        
        # Generate save path if not provided
        if save_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = f"webcam_photo_{timestamp}.jpg"
        
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize camera
        cap = cv2.VideoCapture(camera_index)
        
        if not cap.isOpened():
            return {
                "tool_success": False,
                "tool_error": f"Could not open camera {camera_index}"
            }
        
        try:
            # Get camera properties
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Capture frame
            ret, frame = cap.read()
            
            if not ret:
                return {
                    "tool_success": False,
                    "tool_error": "Failed to capture frame from camera"
                }
            
            # Save photo
            cv2.imwrite(str(save_path), frame)
            
            # Get file info
            file_size = save_path.stat().st_size
            
            return {
                "tool_success": True,
                "tool_message": f"Webcam photo captured: {save_path.name} ({width}x{height})"
            }
            
        finally:
            cap.release()
        
    except Exception as e:
        return {
            "success": False,
            "save_path": str(save_path) if 'save_path' in locals() else None,
            "camera_index": camera_index,
            "error": f"Error capturing webcam photo: {str(e)}"
        }


if __name__ == "__main__":
    # Test the media tools
    print("=== Media Tools Test ===")
    
    # Test screenshot
    print("\n1. Testing screenshot:")
    screenshot_result = take_screenshot.invoke({})

    print("\n2. Testing media control:")
    control_result = control_media.invoke({"action":"mute"})

    print("\n3. Testing webcam capture:")
    webcam_result = capture_webcam_photo.invoke({"save_path":"test_webcam.jpg"})

    
    print("\n=== Media Tools Test Complete ===")