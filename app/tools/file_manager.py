#!/usr/bin/env python3
"""
File Manager Tool
Comprehensive file and folder management operations
"""

import os
import shutil
import stat
from pathlib import Path
from typing import Dict, List, Any, Optional
import time
from datetime import datetime
import glob
from langchain.tools import tool

@tool
def open_folder(path: str = None) -> str:
    """
    Open a folder in File Explorer (Windows), Finder (macOS), or default file manager (Linux).
    If no path is provided, opens the user's home directory.
    
    Args:
        path (str): Path to the folder to open. Defaults to user home directory.
        
    Returns:
        str: Success or error message
    """
    import subprocess
    import platform
    
    try:
        # Default to home directory if no path provided
        if path is None or path == "":
            path = str(Path.home())
        
        # Expand special paths
        if path.lower() == "downloads":
            path = str(Path.home() / "Downloads")
        elif path.lower() == "documents":
            path = str(Path.home() / "Documents")
        elif path.lower() == "desktop":
            path = str(Path.home() / "Desktop")
        
        folder_path = Path(path)
        
        # Check if path exists
        if not folder_path.exists():
            return f"Error: Folder does not exist: {path}"
        
        # Check if it's actually a directory
        if not folder_path.is_dir():
            return f"Error: Path is not a folder: {path}"
        
        # Get absolute path
        abs_path = str(folder_path.absolute())
        
        # Open folder based on OS
        system = platform.system()
        
        if system == "Windows":
            # Windows: Use explorer
            os.startfile(abs_path)
        elif system == "Darwin":
            # macOS: Use open command
            subprocess.run(["open", abs_path], check=True)
        else:
            # Linux: Try xdg-open
            subprocess.run(["xdg-open", abs_path], check=True)
        
        return f"Opened folder: {abs_path}"
        
    except PermissionError:
        return f"Error: Permission denied to open folder: {path}"
    except Exception as e:
        return f"Error opening folder: {str(e)}"


@tool
def create_folder(path: str, parents: bool = True) -> Dict[str, Any]:
    """
    Create a new folder
    
    Args:
        path (str): Path where to create the folder
        parents (bool): Create parent directories if they don't exist
        
    Returns:
        Dict: Operation result with success status
    """
    try:
        folder_path = Path(path)
        
        if folder_path.exists():
            return {
                "success": False,
                "path": path,
                "error": f"Folder already exists: {path}"
            }
        
        if parents:
            folder_path.mkdir(parents=True, exist_ok=True)
        else:
            folder_path.mkdir()
        
        return {
            "success": True,
            "path": str(folder_path.absolute()),
            "message": f"Folder created successfully: {path}"
        }
        
    except PermissionError:
        return {
            "success": False,
            "path": path,
            "error": f"Permission denied: Cannot create folder at {path}"
        }
    except Exception as e:
        return {
            "success": False,
            "path": path,
            "error": f"Error creating folder: {str(e)}"
        }


def delete_file_or_folder(path: str, force: bool = False) -> Dict[str, Any]:
    """
    Delete a file or folder
    
    Args:
        path (str): Path to delete
        force (bool): Force delete even if read-only or non-empty
        
    Returns:
        Dict: Operation result with success status
    """
    try:
        target_path = Path(path)
        
        if not target_path.exists():
            return {
                "success": False,
                "path": path,
                "error": f"Path does not exist: {path}"
            }
        
        # Get file/folder info before deletion
        is_file = target_path.is_file()
        size_mb = 0
        
        if is_file:
            size_mb = target_path.stat().st_size / (1024*1024)
        else:
            # Calculate folder size
            total_size = sum(f.stat().st_size for f in target_path.rglob('*') if f.is_file())
            size_mb = total_size / (1024*1024)
        
        # Handle read-only files if force is enabled
        if force and is_file and not os.access(target_path, os.W_OK):
            target_path.chmod(stat.S_IWRITE)
        
        # Delete the file or folder
        if is_file:
            target_path.unlink()
        else:
            if force:
                shutil.rmtree(target_path)
            else:
                target_path.rmdir()  # Only works if empty
        
        return {
            "success": True,
            "path": path,
            "type": "file" if is_file else "folder",
            "size_mb": round(size_mb, 2),
            "message": f"{'File' if is_file else 'Folder'} deleted successfully: {path}"
        }
        
    except PermissionError:
        return {
            "success": False,
            "path": path,
            "error": f"Permission denied: Cannot delete {path}"
        }
    except OSError as e:
        if "directory not empty" in str(e).lower():
            return {
                "success": False,
                "path": path,
                "error": f"Folder not empty. Use force=True to delete non-empty folders."
            }
        else:
            return {
                "success": False,
                "path": path,
                "error": f"OS error deleting path: {str(e)}"
            }
    except Exception as e:
        return {
            "success": False,
            "path": path,
            "error": f"Error deleting path: {str(e)}"
        }


def move_file_or_folder(source: str, destination: str, overwrite: bool = False) -> Dict[str, Any]:
    """
    Move a file or folder to a new location
    
    Args:
        source (str): Source path
        destination (str): Destination path
        overwrite (bool): Overwrite if destination exists
        
    Returns:
        Dict: Operation result with success status
    """
    try:
        source_path = Path(source)
        dest_path = Path(destination)
        
        if not source_path.exists():
            return {
                "success": False,
                "source": source,
                "destination": destination,
                "error": f"Source does not exist: {source}"
            }
        
        if dest_path.exists() and not overwrite:
            return {
                "success": False,
                "source": source,
                "destination": destination,
                "error": f"Destination already exists. Use overwrite=True to replace."
            }
        
        # If destination exists and overwrite is True, remove it first
        if dest_path.exists() and overwrite:
            if dest_path.is_file():
                dest_path.unlink()
            else:
                shutil.rmtree(dest_path)
        
        # Create parent directories if they don't exist
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Move the file or folder
        shutil.move(str(source_path), str(dest_path))
        
        return {
            "success": True,
            "source": source,
            "destination": str(dest_path.absolute()),
            "type": "file" if source_path.was_file() else "folder",
            "message": f"Successfully moved {source} to {destination}"
        }
        
    except PermissionError:
        return {
            "success": False,
            "source": source,
            "destination": destination,
            "error": f"Permission denied: Cannot move to {destination}"
        }
    except Exception as e:
        return {
            "success": False,
            "source": source,
            "destination": destination,
            "error": f"Error moving file: {str(e)}"
        }


def copy_file_or_folder(source: str, destination: str, overwrite: bool = False) -> Dict[str, Any]:
    """
    Copy a file or folder to a new location
    
    Args:
        source (str): Source path
        destination (str): Destination path
        overwrite (bool): Overwrite if destination exists
        
    Returns:
        Dict: Operation result with success status
    """
    try:
        source_path = Path(source)
        dest_path = Path(destination)
        
        if not source_path.exists():
            return {
                "success": False,
                "source": source,
                "destination": destination,
                "error": f"Source does not exist: {source}"
            }
        
        if dest_path.exists() and not overwrite:
            return {
                "success": False,
                "source": source,
                "destination": destination,
                "error": f"Destination already exists. Use overwrite=True to replace."
            }
        
        # Create parent directories if they don't exist
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file or folder
        if source_path.is_file():
            shutil.copy2(str(source_path), str(dest_path))
        else:
            if dest_path.exists() and overwrite:
                shutil.rmtree(dest_path)
            shutil.copytree(str(source_path), str(dest_path))
        
        # Get size info
        if source_path.is_file():
            size_mb = source_path.stat().st_size / (1024*1024)
        else:
            total_size = sum(f.stat().st_size for f in source_path.rglob('*') if f.is_file())
            size_mb = total_size / (1024*1024)
        
        return {
            "success": True,
            "source": source,
            "destination": str(dest_path.absolute()),
            "type": "file" if source_path.is_file() else "folder",
            "size_mb": round(size_mb, 2),
            "message": f"Successfully copied {source} to {destination}"
        }
        
    except PermissionError:
        return {
            "success": False,
            "source": source,
            "destination": destination,
            "error": f"Permission denied: Cannot copy to {destination}"
        }
    except Exception as e:
        return {
            "success": False,
            "source": source,
            "destination": destination,
            "error": f"Error copying file: {str(e)}"
        }


def find_files(search_term: str, location: str = None, file_type: str = None, max_results: int = 50) -> Dict[str, Any]:
    """
    Search for files matching a pattern
    
    Args:
        search_term (str): Search pattern (supports wildcards)
        location (str): Directory to search in (defaults to user home)
        file_type (str): Filter by file extension (e.g., '.txt', '.py')
        max_results (int): Maximum number of results to return
        
    Returns:
        Dict: Search results with file information
    """
    try:
        if location is None:
            location = str(Path.home())
        
        search_path = Path(location)
        
        if not search_path.exists():
            return {
                "success": False,
                "search_term": search_term,
                "location": location,
                "error": f"Search location does not exist: {location}"
            }
        
        # Build search pattern
        if not any(char in search_term for char in ['*', '?', '[']):
            search_pattern = f"*{search_term}*"
        else:
            search_pattern = search_term
        
        # Find matching files
        matches = []
        try:
            for file_path in search_path.rglob(search_pattern):
                if file_path.is_file():
                    # Filter by file type if specified
                    if file_type and not file_path.name.lower().endswith(file_type.lower()):
                        continue
                    
                    file_stat = file_path.stat()
                    matches.append({
                        'name': file_path.name,
                        'path': str(file_path.absolute()),
                        'size_mb': round(file_stat.st_size / (1024*1024), 3),
                        'modified': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                        'extension': file_path.suffix
                    })
                    
                    if len(matches) >= max_results:
                        break
        except PermissionError:
            # Continue searching in accessible directories
            pass
        
        return {
            "success": True,
            "search_term": search_term,
            "location": location,
            "file_type": file_type,
            "results": matches,
            "count": len(matches),
            "truncated": len(matches) >= max_results,
            "message": f"Found {len(matches)} files matching '{search_term}'"
        }
        
    except Exception as e:
        return {
            "success": False,
            "search_term": search_term,
            "location": location,
            "results": [],
            "count": 0,
            "error": f"Error searching files: {str(e)}"
        }


def get_file_info(path: str) -> Dict[str, Any]:
    """
    Get detailed information about a file or folder
    
    Args:
        path (str): Path to examine
        
    Returns:
        Dict: Detailed file/folder information
    """
    try:
        target_path = Path(path)
        
        if not target_path.exists():
            return {
                "success": False,
                "path": path,
                "error": f"Path does not exist: {path}"
            }
        
        file_stat = target_path.stat()
        is_file = target_path.is_file()
        
        info = {
            "success": True,
            "path": str(target_path.absolute()),
            "name": target_path.name,
            "type": "file" if is_file else "folder",
            "size_bytes": file_stat.st_size,
            "size_mb": round(file_stat.st_size / (1024*1024), 3),
            "created": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
            "accessed": datetime.fromtimestamp(file_stat.st_atime).isoformat(),
            "permissions": {
                "readable": os.access(target_path, os.R_OK),
                "writable": os.access(target_path, os.W_OK),
                "executable": os.access(target_path, os.X_OK)
            }
        }
        
        if is_file:
            info["extension"] = target_path.suffix
            info["stem"] = target_path.stem
        else:
            # For folders, count contents
            try:
                contents = list(target_path.iterdir())
                files = [p for p in contents if p.is_file()]
                folders = [p for p in contents if p.is_dir()]
                
                info["contents"] = {
                    "total_items": len(contents),
                    "files": len(files),
                    "folders": len(folders)
                }
                
                # Calculate total folder size
                total_size = sum(f.stat().st_size for f in target_path.rglob('*') if f.is_file())
                info["total_size_mb"] = round(total_size / (1024*1024), 3)
                
            except PermissionError:
                info["contents"] = {"error": "Permission denied to list contents"}
        
        return info
        
    except PermissionError:
        return {
            "success": False,
            "path": path,
            "error": f"Permission denied: Cannot access {path}"
        }
    except Exception as e:
        return {
            "success": False,
            "path": path,
            "error": f"Error getting file info: {str(e)}"
        }


def list_directory(path: str = None, show_hidden: bool = False, sort_by: str = "name") -> Dict[str, Any]:
    """
    List contents of a directory
    
    Args:
        path (str): Directory path (defaults to current directory)
        show_hidden (bool): Include hidden files/folders
        sort_by (str): Sort by 'name', 'size', 'modified', or 'type'
        
    Returns:
        Dict: Directory listing with file information
    """
    try:
        if path is None:
            path = os.getcwd()
        
        dir_path = Path(path)
        
        if not dir_path.exists():
            return {
                "success": False,
                "path": path,
                "error": f"Directory does not exist: {path}"
            }
        
        if not dir_path.is_dir():
            return {
                "success": False,
                "path": path,
                "error": f"Path is not a directory: {path}"
            }
        
        contents = []
        
        for item in dir_path.iterdir():
            # Skip hidden files unless requested
            if not show_hidden and item.name.startswith('.'):
                continue
            
            try:
                item_stat = item.stat()
                
                item_info = {
                    'name': item.name,
                    'path': str(item.absolute()),
                    'type': 'file' if item.is_file() else 'folder',
                    'size_mb': round(item_stat.st_size / (1024*1024), 3),
                    'modified': datetime.fromtimestamp(item_stat.st_mtime).isoformat(),
                    'permissions': {
                        'readable': os.access(item, os.R_OK),
                        'writable': os.access(item, os.W_OK)
                    }
                }
                
                if item.is_file():
                    item_info['extension'] = item.suffix
                
                contents.append(item_info)
                
            except (PermissionError, OSError):
                # Skip inaccessible items
                continue
        
        # Sort contents
        if sort_by == "size":
            contents.sort(key=lambda x: x['size_mb'], reverse=True)
        elif sort_by == "modified":
            contents.sort(key=lambda x: x['modified'], reverse=True)
        elif sort_by == "type":
            contents.sort(key=lambda x: (x['type'], x['name']))
        else:  # sort by name (default)
            contents.sort(key=lambda x: x['name'].lower())
        
        files = [item for item in contents if item['type'] == 'file']
        folders = [item for item in contents if item['type'] == 'folder']
        
        return {
            "success": True,
            "path": str(dir_path.absolute()),
            "contents": contents,
            "summary": {
                "total_items": len(contents),
                "files": len(files),
                "folders": len(folders),
                "total_size_mb": round(sum(item['size_mb'] for item in files), 3)
            },
            "sort_by": sort_by,
            "show_hidden": show_hidden,
            "message": f"Listed {len(contents)} items in {path}"
        }
        
    except PermissionError:
        return {
            "success": False,
            "path": path,
            "error": f"Permission denied: Cannot access directory {path}"
        }
    except Exception as e:
        return {
            "success": False,
            "path": path,
            "error": f"Error listing directory: {str(e)}"
        }


if __name__ == "__main__":
    # Test the file manager functions
    print("=== File Manager Tool Test ===")
    
    # Test directory listing
    print("\n1. Testing directory listing:")
    list_result = list_directory("C:\\Users", sort_by="name")
    if list_result['success']:
        print(f"Directory contains {list_result['summary']['total_items']} items")
    else:
        print(f"Error: {list_result['error']}")
    
    # Test file search
    print("\n2. Testing file search:")
    search_result = find_files("*.py", max_results=5)
    print(f"Found {search_result['count']} Python files")
    
    # Test creating a test folder
    print("\n3. Testing folder creation:")
    test_folder = "C:\\Users\\Documents\\test_folder_temp"
    create_result = create_folder(test_folder)
    print(f"Create folder result: {create_result['success']}")
    
    # Test file info
    if create_result['success']:
        print("\n4. Testing file info:")
        info_result = get_file_info(test_folder)
        if info_result['success']:
            print(f"Folder info: {info_result['type']}, created: {info_result['created']}")
        
        # Clean up test folder
        print("\n5. Cleaning up test folder:")
        delete_result = delete_file_or_folder(test_folder)
        print(f"Delete result: {delete_result['success']}")
    
    print("\n=== File Manager Test Complete ===")