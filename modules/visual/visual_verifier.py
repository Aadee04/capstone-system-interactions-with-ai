#!/usr/bin/env python3
"""
Visual Verifier
Provides screenshot capture and visual verification capabilities for confirming agent actions
"""

import time
import cv2
import numpy as np
from PIL import Image, ImageGrab
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import tempfile
import os

# Try to import OCR libraries with fallbacks
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    print("[Visual Verifier] Warning: pytesseract not available. Installing...")
    try:
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pytesseract"])
        import pytesseract
        TESSERACT_AVAILABLE = True
    except:
        print("[Visual Verifier] Could not install pytesseract. OCR features disabled.")
        TESSERACT_AVAILABLE = False

class VisualVerifier:
    """Provides visual verification capabilities using screenshots and basic image analysis"""
    
    def __init__(self):
        """Initialize the visual verifier"""
        self.screenshot_cache = {}
        self.verification_cache = {}
        
        # Create screenshots directory
        self.screenshots_dir = Path("data/screenshots")
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        # Common UI element templates (you can expand these)
        self.ui_templates = {
            'browser_indicators': ['Chrome', 'Firefox', 'Edge', 'Safari'],
            'file_manager_indicators': ['This PC', 'Documents', 'Downloads', 'Desktop'],
            'calculator_indicators': ['Calculator', '=', 'CE', 'C'],
            'error_indicators': ['Error', 'Failed', 'Cannot', 'Unable', 'Not found'],
            'success_indicators': ['Complete', 'Success', 'Finished', 'Done', 'OK']
        }
        
        # Initialize OCR if available
        if TESSERACT_AVAILABLE:
            try:
                # Try to set tesseract path for Windows
                tesseract_paths = [
                    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                    r"C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe".format(os.getenv('USERNAME', '')),
                    "tesseract"  # System PATH
                ]
                
                for path in tesseract_paths:
                    if os.path.exists(path) or path == "tesseract":
                        pytesseract.pytesseract.tesseract_cmd = path
                        # Test OCR
                        test_img = Image.new('RGB', (100, 50), color='white')
                        pytesseract.image_to_string(test_img)
                        print(f"[Visual Verifier] OCR initialized with Tesseract at: {path}")
                        break
                else:
                    print("[Visual Verifier] Warning: Tesseract not found. OCR may not work.")
                    
            except Exception as e:
                print(f"[Visual Verifier] Warning: OCR initialization failed: {e}")
        
        print("[Visual Verifier] Initialized")
    
    def take_screenshot(self, save_path: Optional[str] = None) -> str:
        """
        Take a screenshot of the current screen
        
        Args:
            save_path (str): Optional path to save screenshot
            
        Returns:
            str: Path to saved screenshot
        """
        try:
            # Capture screenshot
            screenshot = ImageGrab.grab()
            
            # Generate filename if not provided
            if not save_path:
                timestamp = int(time.time())
                save_path = self.screenshots_dir / f"screenshot_{timestamp}.png"
            
            # Save screenshot
            screenshot.save(save_path)
            
            # Cache the screenshot
            self.screenshot_cache[str(save_path)] = {
                'timestamp': time.time(),
                'size': screenshot.size,
                'mode': screenshot.mode
            }
            
            print(f"[Visual Verifier] Screenshot saved: {save_path}")
            return str(save_path)
            
        except Exception as e:
            print(f"[Visual Verifier] Error taking screenshot: {e}")
            return None
    
    def compare_screenshots(self, before_path: str, after_path: str, 
                          threshold: float = 0.1) -> Dict[str, Any]:
        """
        Compare two screenshots to detect changes
        
        Args:
            before_path (str): Path to before screenshot
            after_path (str): Path to after screenshot
            threshold (float): Change detection threshold (0.0 - 1.0)
            
        Returns:
            Dict: Comparison results with change detection
        """
        try:
            # Load images
            before_img = Image.open(before_path)
            after_img = Image.open(after_path)
            
            # Ensure same size
            if before_img.size != after_img.size:
                after_img = after_img.resize(before_img.size)
            
            # Convert to numpy arrays
            before_array = np.array(before_img)
            after_array = np.array(after_img)
            
            # Calculate difference
            diff = np.abs(before_array.astype(float) - after_array.astype(float))
            diff_normalized = diff / 255.0
            
            # Calculate change percentage
            change_percentage = np.mean(diff_normalized)
            
            # Detect if significant change occurred
            significant_change = change_percentage > threshold
            
            result = {
                'change_detected': significant_change,
                'change_percentage': float(change_percentage),
                'threshold': threshold,
                'before_path': before_path,
                'after_path': after_path,
                'analysis_timestamp': time.time()
            }
            
            print(f"[Visual Verifier] Screenshot comparison: {change_percentage:.3f} change "
                  f"({'significant' if significant_change else 'minimal'})")
            
            return result
            
        except Exception as e:
            print(f"[Visual Verifier] Error comparing screenshots: {e}")
            return {
                'change_detected': False,
                'error': str(e),
                'analysis_timestamp': time.time()
            }
    
    def extract_text_from_screenshot(self, screenshot_path: str) -> List[str]:
        """
        Extract text from screenshot using OCR
        
        Args:
            screenshot_path (str): Path to screenshot
            
        Returns:
            List[str]: Extracted text lines
        """
        if not TESSERACT_AVAILABLE:
            print("[Visual Verifier] OCR not available")
            return []
        
        try:
            # Load image
            image = Image.open(screenshot_path)
            
            # Perform OCR
            extracted_text = pytesseract.image_to_string(image)
            
            # Split into lines and clean
            text_lines = [line.strip() for line in extracted_text.split('\n') if line.strip()]
            
            print(f"[Visual Verifier] Extracted {len(text_lines)} text lines from screenshot")
            return text_lines
            
        except Exception as e:
            print(f"[Visual Verifier] Error extracting text: {e}")
            return []
    
    def verify_application_opened(self, app_name: str, screenshot_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify if an application was successfully opened
        
        Args:
            app_name (str): Name of the application
            screenshot_path (str): Path to screenshot (optional, will take new one if not provided)
            
        Returns:
            Dict: Verification results
        """
        if not screenshot_path:
            screenshot_path = self.take_screenshot()
        
        if not screenshot_path:
            return {'verified': False, 'error': 'Could not take screenshot'}
        
        # Extract text from screenshot
        text_lines = self.extract_text_from_screenshot(screenshot_path)
        all_text = ' '.join(text_lines).lower()
        
        # Check for application-specific indicators
        app_lower = app_name.lower()
        
        # Define application verification patterns
        verification_patterns = {
            'chrome': ['chrome', 'google chrome', 'new tab'],
            'firefox': ['firefox', 'mozilla firefox'],
            'edge': ['microsoft edge', 'edge'],
            'calculator': ['calculator', 'calc.exe'],
            'notepad': ['notepad', 'untitled'],
            'explorer': ['file explorer', 'this pc', 'documents'],
            'cmd': ['command prompt', 'c:\\', 'windows\\system32'],
            'powershell': ['powershell', 'ps ']
        }
        
        # Check patterns
        patterns = verification_patterns.get(app_lower, [app_lower])
        found_indicators = []
        
        for pattern in patterns:
            if pattern in all_text:
                found_indicators.append(pattern)
        
        verified = len(found_indicators) > 0
        
        result = {
            'verified': verified,
            'app_name': app_name,
            'found_indicators': found_indicators,
            'screenshot_path': screenshot_path,
            'verification_method': 'ocr_text_matching',
            'timestamp': time.time()
        }
        
        print(f"[Visual Verifier] App verification for '{app_name}': "
              f"{'✓ VERIFIED' if verified else '✗ NOT VERIFIED'} "
              f"(found: {found_indicators})")
        
        return result
    
    def verify_file_opened(self, file_name: str, screenshot_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify if a file was successfully opened
        
        Args:
            file_name (str): Name of the file
            screenshot_path (str): Path to screenshot
            
        Returns:
            Dict: Verification results
        """
        if not screenshot_path:
            screenshot_path = self.take_screenshot()
        
        if not screenshot_path:
            return {'verified': False, 'error': 'Could not take screenshot'}
        
        # Extract text from screenshot
        text_lines = self.extract_text_from_screenshot(screenshot_path)
        all_text = ' '.join(text_lines).lower()
        
        # Look for file name in window titles or content
        file_lower = Path(file_name).stem.lower()  # Get filename without extension
        
        verified = file_lower in all_text
        
        result = {
            'verified': verified,
            'file_name': file_name,
            'search_term': file_lower,
            'screenshot_path': screenshot_path,
            'verification_method': 'ocr_filename_matching',
            'timestamp': time.time()
        }
        
        print(f"[Visual Verifier] File verification for '{file_name}': "
              f"{'✓ VERIFIED' if verified else '✗ NOT VERIFIED'}")
        
        return result
    
    def verify_folder_opened(self, folder_path: str, screenshot_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify if a folder was successfully opened
        
        Args:
            folder_path (str): Path to the folder
            screenshot_path (str): Path to screenshot
            
        Returns:
            Dict: Verification results
        """
        if not screenshot_path:
            screenshot_path = self.take_screenshot()
        
        if not screenshot_path:
            return {'verified': False, 'error': 'Could not take screenshot'}
        
        # Extract text from screenshot
        text_lines = self.extract_text_from_screenshot(screenshot_path)
        all_text = ' '.join(text_lines).lower()
        
        # Look for folder name or path indicators
        folder_name = Path(folder_path).name.lower()
        path_parts = Path(folder_path).parts
        
        # Check for folder name and path components
        verification_indicators = [folder_name]
        verification_indicators.extend([part.lower() for part in path_parts[-2:]])  # Last 2 path components
        
        found_indicators = []
        for indicator in verification_indicators:
            if indicator in all_text:
                found_indicators.append(indicator)
        
        # Also check for file manager indicators
        file_manager_indicators = ['file explorer', 'this pc', 'folders']
        for indicator in file_manager_indicators:
            if indicator in all_text:
                found_indicators.append(f"file_manager:{indicator}")
        
        verified = len(found_indicators) > 0
        
        result = {
            'verified': verified,
            'folder_path': folder_path,
            'found_indicators': found_indicators,
            'screenshot_path': screenshot_path,
            'verification_method': 'ocr_folder_matching',
            'timestamp': time.time()
        }
        
        print(f"[Visual Verifier] Folder verification for '{folder_path}': "
              f"{'✓ VERIFIED' if verified else '✗ NOT VERIFIED'} "
              f"(found: {found_indicators})")
        
        return result
    
    def detect_error_dialogs(self, screenshot_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Detect if any error dialogs are present on screen
        
        Args:
            screenshot_path (str): Path to screenshot
            
        Returns:
            Dict: Error detection results
        """
        if not screenshot_path:
            screenshot_path = self.take_screenshot()
        
        if not screenshot_path:
            return {'errors_detected': False, 'error': 'Could not take screenshot'}
        
        # Extract text from screenshot
        text_lines = self.extract_text_from_screenshot(screenshot_path)
        all_text = ' '.join(text_lines).lower()
        
        # Look for error indicators
        error_keywords = [
            'error', 'failed', 'cannot', 'unable', 'not found', 'access denied',
            'permission denied', 'file not found', 'invalid', 'incorrect',
            'exception', 'warning', 'alert'
        ]
        
        detected_errors = []
        for keyword in error_keywords:
            if keyword in all_text:
                detected_errors.append(keyword)
        
        errors_found = len(detected_errors) > 0
        
        result = {
            'errors_detected': errors_found,
            'error_indicators': detected_errors,
            'screenshot_path': screenshot_path,
            'detection_method': 'ocr_keyword_matching',
            'timestamp': time.time()
        }
        
        if errors_found:
            print(f"[Visual Verifier] ⚠️  Error dialogs detected: {detected_errors}")
        
        return result
    
    def verify_action_success(self, action_type: str, target: str, 
                            before_screenshot: Optional[str] = None,
                            after_screenshot: Optional[str] = None) -> Dict[str, Any]:
        """
        Comprehensive action verification
        
        Args:
            action_type (str): Type of action (open_app, open_file, open_folder)
            target (str): Target of the action (app name, file path, etc.)
            before_screenshot (str): Screenshot before action
            after_screenshot (str): Screenshot after action
            
        Returns:
            Dict: Complete verification results
        """
        # Take after screenshot if not provided
        if not after_screenshot:
            after_screenshot = self.take_screenshot()
        
        results = {
            'action_type': action_type,
            'target': target,
            'verification_timestamp': time.time(),
            'screenshots': {
                'before': before_screenshot,
                'after': after_screenshot
            }
        }
        
        # Perform specific verification based on action type
        if action_type == 'open_app':
            app_verification = self.verify_application_opened(target, after_screenshot)
            results.update(app_verification)
            
        elif action_type == 'open_file':
            file_verification = self.verify_file_opened(target, after_screenshot)
            results.update(file_verification)
            
        elif action_type == 'open_folder':
            folder_verification = self.verify_folder_opened(target, after_screenshot)
            results.update(folder_verification)
        
        # Check for errors
        error_detection = self.detect_error_dialogs(after_screenshot)
        results['error_detection'] = error_detection
        
        # Compare screenshots if both available
        if before_screenshot and after_screenshot:
            comparison = self.compare_screenshots(before_screenshot, after_screenshot)
            results['screenshot_comparison'] = comparison
            
            # If no specific verification passed but significant change detected, 
            # assume success (something happened)
            if not results.get('verified', False) and comparison.get('change_detected', False):
                results['verified'] = True
                results['verification_method'] = 'change_detection_fallback'
        
        # Final verification decision
        final_success = (
            results.get('verified', False) and 
            not error_detection.get('errors_detected', False)
        )
        
        results['final_verification'] = final_success
        
        print(f"[Visual Verifier] Action '{action_type}' on '{target}': "
              f"{'✓ SUCCESS' if final_success else '✗ FAILED'}")
        
        return results
    
    def cleanup_old_screenshots(self, max_age_hours: int = 24):
        """Remove screenshots older than specified hours"""
        try:
            cutoff_time = time.time() - (max_age_hours * 60 * 60)
            removed_count = 0
            
            for screenshot_file in self.screenshots_dir.glob("screenshot_*.png"):
                if screenshot_file.stat().st_mtime < cutoff_time:
                    screenshot_file.unlink()
                    removed_count += 1
            
            if removed_count > 0:
                print(f"[Visual Verifier] Cleaned up {removed_count} old screenshots")
                
        except Exception as e:
            print(f"[Visual Verifier] Error during cleanup: {e}")
    
    def get_verification_summary(self) -> Dict[str, Any]:
        """Get summary of verification activities"""
        return {
            'screenshots_dir': str(self.screenshots_dir),
            'cached_screenshots': len(self.screenshot_cache),
            'ocr_available': TESSERACT_AVAILABLE,
            'supported_verifications': ['open_app', 'open_file', 'open_folder', 'error_detection']
        }


# Global visual verifier instance
_visual_verifier = None

def get_visual_verifier():
    """Get the global visual verifier instance"""
    global _visual_verifier
    if _visual_verifier is None:
        _visual_verifier = VisualVerifier()
    return _visual_verifier

def take_screenshot(save_path=None):
    """Convenience function to take screenshot"""
    verifier = get_visual_verifier()
    return verifier.take_screenshot(save_path)

def verify_action(action_type, target, before_screenshot=None, after_screenshot=None):
    """Convenience function to verify action"""
    verifier = get_visual_verifier()
    return verifier.verify_action_success(action_type, target, before_screenshot, after_screenshot)

def detect_errors(screenshot_path=None):
    """Convenience function to detect errors"""
    verifier = get_visual_verifier()
    return verifier.detect_error_dialogs(screenshot_path)

# Test functionality
if __name__ == "__main__":
    print("=== Visual Verifier Test ===")
    
    verifier = VisualVerifier()
    
    # Test screenshot
    print("\n1. Testing screenshot capture:")
    screenshot_path = verifier.take_screenshot()
    if screenshot_path:
        print(f"Screenshot saved: {screenshot_path}")
    
    # Test OCR
    if TESSERACT_AVAILABLE and screenshot_path:
        print("\n2. Testing OCR text extraction:")
        text_lines = verifier.extract_text_from_screenshot(screenshot_path)
        print(f"Extracted {len(text_lines)} text lines")
        for i, line in enumerate(text_lines[:5]):  # Show first 5 lines
            print(f"  {i+1}: {line}")
    
    # Test application verification
    print("\n3. Testing application verification:")
    app_result = verifier.verify_application_opened("explorer", screenshot_path)
    print(f"Explorer verification: {app_result}")
    
    # Test error detection
    print("\n4. Testing error detection:")
    error_result = verifier.detect_error_dialogs(screenshot_path)
    print(f"Error detection: {error_result}")
    
    # Test summary
    print("\n5. System summary:")
    summary = verifier.get_verification_summary()
    print(f"Summary: {summary}")
    
    print("\n=== Test Complete ===")