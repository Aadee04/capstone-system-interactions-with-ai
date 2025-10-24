#!/usr/bin/env python3
"""
Get Recent Files Tool
Context-aware tool to retrieve recently accessed files
"""

from typing import Dict, List, Any, Optional
from modules.context.system_state_tracker import get_state_tracker
from langchain.tools import tool

def get_recent_files(count: int = 10, file_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Get recently accessed files with optional filtering
    
    Args:
        count (int): Number of recent files to return (default: 10)
        file_type (str): Filter by file extension (e.g., '.py', '.txt', '.docx')
        
    Returns:
        Dict: Contains recent files list and metadata
    """
    try:
        state_tracker = get_state_tracker()
        
        # Get recent files from state tracker
        recent_files = state_tracker.get_recent_files(count * 2 if file_type else count)
        
        # Filter by file type if specified
        if file_type:
            if not file_type.startswith('.'):
                file_type = '.' + file_type
            
            filtered_files = []
            for file_info in recent_files:
                if file_info.get('extension', '').lower() == file_type.lower():
                    filtered_files.append(file_info)
                    if len(filtered_files) >= count:
                        break
            
            recent_files = filtered_files
        else:
            recent_files = recent_files[:count]
        
        # Format for user-friendly display
        formatted_files = []
        for file_info in recent_files:
            formatted_file = {
                'name': file_info.get('name', 'Unknown'),
                'path': file_info.get('path', ''),
                'extension': file_info.get('extension', ''),
                'size_mb': round(file_info.get('size', 0) / (1024*1024), 2),
                'modified': file_info.get('modified', 'Unknown'),
                'app': file_info.get('app', 'Unknown')
            }
            formatted_files.append(formatted_file)
        
        return {
            "success": True,
            "files": formatted_files,
            "count": len(formatted_files),
            "filter_applied": file_type if file_type else "None",
            "message": f"Found {len(formatted_files)} recent files" + 
                      (f" of type {file_type}" if file_type else "")
        }
        
    except Exception as e:
        return {
            "success": False,
            "files": [],
            "count": 0,
            "filter_applied": file_type if file_type else "None",
            "error": f"Error retrieving recent files: {str(e)}"
        }


if __name__ == "__main__":
    # Test the function
    print("=== Get Recent Files Tool Test ===")
    
    # Test getting all recent files
    result = get_recent_files(5)
    print(f"\nAll recent files: {result}")
    
    # Test filtering by file type
    result_py = get_recent_files(5, ".py")
    print(f"\nPython files: {result_py}")
    
    result_txt = get_recent_files(3, "txt")
    print(f"\nText files: {result_txt}")