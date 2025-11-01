#!/usr/bin/env python3
"""
Text Processor Tool
Text processing, file operations, OCR, and text analysis
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import chardet
import json
from langchain.tools import tool


@tool
def read_text_from_file(file_path: str, encoding: str = None, max_size_mb: int = 10) -> Dict[str, Any]:
    """
    Read text content from a file
    
    Args:
        file_path (str): Path to the text file
        encoding (str): Text encoding (auto-detect if None)
        max_size_mb (int): Maximum file size in MB to read
        
    Returns:
        Dict: File content and metadata
    """
    try:
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {
                "success": False,
                "file_path": str(file_path),
                "error": f"File does not exist: {file_path}"
            }
        
        if not file_path.is_file():
            return {
                "success": False,
                "file_path": str(file_path),
                "error": f"Path is not a file: {file_path}"
            }
        
        # Check file size
        file_size = file_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        
        if file_size_mb > max_size_mb:
            return {
                "success": False,
                "file_path": str(file_path),
                "file_size_mb": round(file_size_mb, 2),
                "error": f"File too large ({file_size_mb:.1f} MB). Maximum allowed: {max_size_mb} MB"
            }
        
        # Auto-detect encoding if not specified
        if encoding is None:
            with open(file_path, 'rb') as f:
                raw_data = f.read(min(10000, file_size))  # Read first 10KB for detection
                detected = chardet.detect(raw_data)
                encoding = detected['encoding'] if detected['encoding'] else 'utf-8'
        
        # Read file content
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
        except UnicodeDecodeError:
            # Fallback to utf-8 with error handling
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            encoding = 'utf-8 (with error handling)'
        
        # Analyze content
        lines = content.split('\n')
        words = len(content.split())
        chars = len(content)
        chars_no_spaces = len(content.replace(' ', '').replace('\n', '').replace('\t', ''))
        
        return {
            "success": True,
            "file_path": str(file_path.absolute()),
            "content": content,
            "encoding": encoding,
            "statistics": {
                "file_size_bytes": file_size,
                "file_size_mb": round(file_size_mb, 3),
                "lines": len(lines),
                "words": words,
                "characters": chars,
                "characters_no_spaces": chars_no_spaces,
                "is_empty": chars == 0
            },
            "file_info": {
                "name": file_path.name,
                "extension": file_path.suffix,
                "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            },
            "message": f"Read {len(lines)} lines, {words} words from {file_path.name}"
        }
        
    except PermissionError:
        return {
            "success": False,
            "file_path": str(file_path),
            "error": f"Permission denied: Cannot read file {file_path}"
        }
    except Exception as e:
        return {
            "success": False,
            "file_path": str(file_path),
            "error": f"Error reading file: {str(e)}"
        }


@tool
def write_text_to_file(file_path: str, content: str, encoding: str = 'utf-8', 
                      mode: str = 'w', create_dirs: bool = True) -> Dict[str, Any]:
    """
    Write text content to a file
    
    Args:
        file_path (str): Path to write the file
        content (str): Text content to write
        encoding (str): Text encoding
        mode (str): Write mode ('w' for overwrite, 'a' for append)
        create_dirs (bool): Create parent directories if they don't exist
        
    Returns:
        Dict: Operation result
    """
    try:
        file_path = Path(file_path)
        
        # Create parent directories if needed
        if create_dirs and not file_path.parent.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if file exists for overwrite warning
        file_existed = file_path.exists()
        old_size = file_path.stat().st_size if file_existed else 0
        
        # Write content
        with open(file_path, mode, encoding=encoding) as f:
            f.write(content)
        
        # Get new file stats
        new_size = file_path.stat().st_size
        lines = content.count('\n') + 1 if content else 0
        words = len(content.split())
        
        return {
            "success": True,
            "file_path": str(file_path.absolute()),
            "mode": mode,
            "encoding": encoding,
            "statistics": {
                "bytes_written": len(content.encode(encoding)),
                "lines_written": lines,
                "words_written": words,
                "characters_written": len(content),
                "new_file_size": new_size,
                "old_file_size": old_size if file_existed else 0
            },
            "file_existed": file_existed,
            "created_directories": create_dirs and not file_path.parent.exists(),
            "timestamp": datetime.now().isoformat(),
            "message": f"{'Appended to' if mode == 'a' else 'Wrote'} {file_path.name} ({len(content)} chars)"
        }
        
    except PermissionError:
        return {
            "success": False,
            "file_path": str(file_path),
            "error": f"Permission denied: Cannot write to {file_path}"
        }
    except Exception as e:
        return {
            "success": False,
            "file_path": str(file_path),
            "error": f"Error writing file: {str(e)}"
        }


@tool
def search_in_file(file_path: str, search_term: str, case_sensitive: bool = False,
                  use_regex: bool = False, max_matches: int = 100) -> Dict[str, Any]:
    """
    Search for text in a file
    
    Args:
        file_path (str): Path to search in
        search_term (str): Text or regex pattern to search for
        case_sensitive (bool): Whether search is case sensitive
        use_regex (bool): Whether to treat search_term as regex
        max_matches (int): Maximum number of matches to return
        
    Returns:
        Dict: Search results
    """
    try:
        # First read the file
        read_result = read_text_from_file(file_path)
        if not read_result['success']:
            return read_result
        
        content = read_result['content']
        lines = content.split('\n')
        
        matches = []
        total_matches = 0
        
        # Prepare search pattern
        if use_regex:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                pattern = re.compile(search_term, flags)
            except re.error as e:
                return {
                    "success": False,
                    "file_path": str(file_path),
                    "search_term": search_term,
                    "error": f"Invalid regex pattern: {str(e)}"
                }
        else:
            search_lower = search_term.lower() if not case_sensitive else search_term
        
        # Search through lines
        for line_num, line in enumerate(lines, 1):
            line_matches = []
            
            if use_regex:
                # Regex search
                for match in pattern.finditer(line):
                    if total_matches >= max_matches:
                        break
                    
                    line_matches.append({
                        'start': match.start(),
                        'end': match.end(),
                        'matched_text': match.group(),
                        'groups': list(match.groups()) if match.groups() else []
                    })
                    total_matches += 1
            else:
                # Text search
                search_line = line.lower() if not case_sensitive else line
                start = 0
                
                while True:
                    pos = search_line.find(search_lower, start)
                    if pos == -1 or total_matches >= max_matches:
                        break
                    
                    line_matches.append({
                        'start': pos,
                        'end': pos + len(search_term),
                        'matched_text': line[pos:pos + len(search_term)],
                        'groups': []
                    })
                    total_matches += 1
                    start = pos + 1
            
            if line_matches:
                # Create preview with context
                preview = line.strip()
                if len(preview) > 200:
                    # Truncate long lines but keep match visible
                    first_match = line_matches[0]
                    start_pos = max(0, first_match['start'] - 50)
                    end_pos = min(len(line), first_match['end'] + 50)
                    preview = ('...' if start_pos > 0 else '') + line[start_pos:end_pos] + ('...' if end_pos < len(line) else '')
                
                matches.append({
                    'line_number': line_num,
                    'line_content': line,
                    'preview': preview,
                    'matches': line_matches,
                    'match_count': len(line_matches)
                })
            
            if total_matches >= max_matches:
                break
        
        return {
            "success": True,
            "file_path": str(file_path),
            "search_term": search_term,
            "case_sensitive": case_sensitive,
            "use_regex": use_regex,
            "results": {
                "total_matches": total_matches,
                "lines_with_matches": len(matches),
                "matches": matches,
                "truncated": total_matches >= max_matches
            },
            "file_stats": read_result['statistics'],
            "message": f"Found {total_matches} matches in {len(matches)} lines"
        }
        
    except Exception as e:
        return {
            "success": False,
            "file_path": str(file_path),
            "search_term": search_term,
            "error": f"Error searching in file: {str(e)}"
        }


@tool
def extract_text_from_image(image_path: str, language: str = 'eng') -> Dict[str, Any]:
    """
    Extract text from an image using OCR
    
    Args:
        image_path (str): Path to image file
        language (str): OCR language code
        
    Returns:
        Dict: Extracted text and metadata
    """
    try:
        try:
            import pytesseract
            from PIL import Image
        except ImportError:
            return {
                "success": False,
                "image_path": str(image_path),
                "error": "OCR dependencies not available. Install pillow and pytesseract packages."
            }
        
        image_path = Path(image_path)
        
        if not image_path.exists():
            return {
                "success": False,
                "image_path": str(image_path),
                "error": f"Image file does not exist: {image_path}"
            }
        
        # Open and process image
        try:
            image = Image.open(image_path)
            
            # Get image info
            image_info = {
                "format": image.format,
                "mode": image.mode,
                "size": image.size,
                "width": image.width,
                "height": image.height
            }
            
        except Exception as e:
            return {
                "success": False,
                "image_path": str(image_path),
                "error": f"Cannot open image file: {str(e)}"
            }
        
        # Extract text using OCR
        try:
            extracted_text = pytesseract.image_to_string(image, lang=language)
            
            # Get OCR confidence data
            data = pytesseract.image_to_data(image, lang=language, output_type=pytesseract.Output.DICT)
            
            # Calculate average confidence
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            # Extract word-level data
            words = []
            for i, word in enumerate(data['text']):
                if word.strip() and int(data['conf'][i]) > 0:
                    words.append({
                        'text': word,
                        'confidence': int(data['conf'][i]),
                        'bbox': {
                            'left': data['left'][i],
                            'top': data['top'][i],
                            'width': data['width'][i],
                            'height': data['height'][i]
                        }
                    })
            
        except Exception as e:
            return {
                "success": False,
                "image_path": str(image_path),
                "error": f"OCR processing failed: {str(e)}"
            }
        
        # Analyze extracted text
        lines = extracted_text.strip().split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        word_count = len(extracted_text.split())
        char_count = len(extracted_text.strip())
        
        return {
            "success": True,
            "image_path": str(image_path.absolute()),
            "extracted_text": extracted_text.strip(),
            "language": language,
            "image_info": image_info,
            "ocr_results": {
                "avg_confidence": round(avg_confidence, 2),
                "words_detected": len(words),
                "word_details": words[:50],  # Limit to first 50 words for response size
                "total_words_available": len(words)
            },
            "text_analysis": {
                "total_lines": len(lines),
                "non_empty_lines": len(non_empty_lines),
                "word_count": word_count,
                "character_count": char_count,
                "is_empty": char_count == 0
            },
            "timestamp": datetime.now().isoformat(),
            "message": f"Extracted {word_count} words from image with {avg_confidence:.1f}% confidence"
        }
        
    except Exception as e:
        return {
            "success": False,
            "image_path": str(image_path),
            "error": f"Error extracting text from image: {str(e)}"
        }


@tool
def translate_text(text: str, target_language: str, source_language: str = 'auto') -> Dict[str, Any]:
    """
    Translate text to another language
    
    Args:
        text (str): Text to translate
        target_language (str): Target language code
        source_language (str): Source language code ('auto' for detection)
        
    Returns:
        Dict: Translation result
    """
    try:
        try:
            from googletrans import Translator, LANGUAGES
        except ImportError:
            return {
                "success": False,
                "text": text[:100] + "..." if len(text) > 100 else text,
                "error": "Translation service not available. Install googletrans package."
            }
        
        if not text.strip():
            return {
                "success": False,
                "text": text,
                "error": "No text provided for translation"
            }
        
        # Validate language codes
        if target_language not in LANGUAGES and target_language != 'auto':
            return {
                "success": False,
                "text": text[:100] + "..." if len(text) > 100 else text,
                "target_language": target_language,
                "error": f"Unsupported target language: {target_language}",
                "supported_languages": list(LANGUAGES.keys())[:20]  # Show first 20
            }
        
        translator = Translator()
        
        # Perform translation
        try:
            if len(text) > 5000:
                return {
                    "success": False,
                    "text": text[:100] + "...",
                    "error": "Text too long for translation. Maximum 5000 characters."
                }
            
            result = translator.translate(text, dest=target_language, src=source_language)
            
            detected_lang = result.src
            confidence = getattr(result.extra_data, 'confidence', None)
            
            return {
                "success": True,
                "original_text": text,
                "translated_text": result.text,
                "source_language": {
                    "code": detected_lang,
                    "name": LANGUAGES.get(detected_lang, "Unknown")
                },
                "target_language": {
                    "code": target_language,
                    "name": LANGUAGES.get(target_language, "Unknown")
                },
                "detection_confidence": confidence,
                "text_stats": {
                    "original_chars": len(text),
                    "translated_chars": len(result.text),
                    "original_words": len(text.split()),
                    "translated_words": len(result.text.split())
                },
                "timestamp": datetime.now().isoformat(),
                "message": f"Translated from {LANGUAGES.get(detected_lang, detected_lang)} to {LANGUAGES.get(target_language, target_language)}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "text": text[:100] + "..." if len(text) > 100 else text,
                "error": f"Translation failed: {str(e)}"
            }
    
    except Exception as e:
        return {
            "success": False,
            "text": text[:100] + "..." if len(text) > 100 else text,
            "error": f"Error in translation: {str(e)}"
        }


def analyze_text(text: str) -> Dict[str, Any]:
    """
    Analyze text for various statistics and properties
    
    Args:
        text (str): Text to analyze
        
    Returns:
        Dict: Text analysis results
    """
    try:
        if not isinstance(text, str):
            text = str(text)
        
        # Basic statistics
        lines = text.split('\n')
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Character statistics
        chars_total = len(text)
        chars_no_spaces = len(text.replace(' ', '').replace('\n', '').replace('\t', ''))
        chars_alpha = sum(1 for c in text if c.isalpha())
        chars_numeric = sum(1 for c in text if c.isdigit())
        chars_special = chars_total - chars_alpha - chars_numeric - text.count(' ') - text.count('\n') - text.count('\t')
        
        # Word statistics
        word_lengths = [len(word) for word in words]
        avg_word_length = sum(word_lengths) / len(word_lengths) if word_lengths else 0
        
        # Sentence statistics
        sentence_lengths = [len(sentence.split()) for sentence in sentences]
        avg_sentence_length = sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0
        
        # Language detection patterns
        common_english_words = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
        english_word_count = sum(1 for word in words if word.lower() in common_english_words)
        likely_english = english_word_count / len(words) > 0.1 if words else False
        
        # Text complexity
        unique_words = set(word.lower() for word in words)
        lexical_diversity = len(unique_words) / len(words) if words else 0
        
        # Find most common words
        from collections import Counter
        word_freq = Counter(word.lower() for word in words if word.isalpha())
        most_common_words = word_freq.most_common(10)
        
        return {
            "success": True,
            "text_preview": text[:200] + ("..." if len(text) > 200 else ""),
            "basic_stats": {
                "total_characters": chars_total,
                "characters_no_spaces": chars_no_spaces,
                "total_words": len(words),
                "unique_words": len(unique_words),
                "total_lines": len(lines),
                "total_sentences": len(sentences),
                "is_empty": chars_total == 0
            },
            "character_breakdown": {
                "alphabetic": chars_alpha,
                "numeric": chars_numeric,
                "spaces": text.count(' '),
                "newlines": text.count('\n'),
                "tabs": text.count('\t'),
                "special_characters": chars_special
            },
            "averages": {
                "word_length": round(avg_word_length, 2),
                "sentence_length": round(avg_sentence_length, 2),
                "words_per_line": round(len(words) / len([l for l in lines if l.strip()]), 2) if any(l.strip() for l in lines) else 0
            },
            "text_properties": {
                "lexical_diversity": round(lexical_diversity, 3),
                "likely_english": likely_english,
                "reading_time_minutes": round(len(words) / 200, 1),  # Assume 200 WPM reading speed
                "contains_urls": bool(re.search(r'https?://', text)),
                "contains_emails": bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)),
                "contains_phone_numbers": bool(re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text))
            },
            "most_common_words": most_common_words,
            "timestamp": datetime.now().isoformat(),
            "message": f"Analyzed text: {len(words)} words, {len(sentences)} sentences, {lexical_diversity:.1%} lexical diversity"
        }
        
    except Exception as e:
        return {
            "success": False,
            "text_preview": text[:100] + "..." if len(text) > 100 else text,
            "error": f"Error analyzing text: {str(e)}"
        }


if __name__ == "__main__":
    # Test the text processing functions
    print("=== Text Processor Tool Test ===")
    
    # Create a test file
    test_content = """This is a test file.
It contains multiple lines.
Each line has different words and punctuation!
Numbers like 123 and symbols @#$ are also present.
This helps test various text analysis features."""
    
    print("\n1. Testing write text to file:")
    write_result = write_text_to_file("test_text.txt", test_content)
    print(f"Write result: {write_result['success']}")
    
    if write_result['success']:
        print("\n2. Testing read text from file:")
        read_result = read_text_from_file("test_text.txt")
        if read_result['success']:
            stats = read_result['statistics']
            print(f"Read {stats['lines']} lines, {stats['words']} words")
        
        print("\n3. Testing search in file:")
        search_result = search_in_file("test_text.txt", "test", case_sensitive=False)
        if search_result['success']:
            results = search_result['results']
            print(f"Found {results['total_matches']} matches in {results['lines_with_matches']} lines")
        
        print("\n4. Testing text analysis:")
        analyze_result = analyze_text(test_content)
        if analyze_result['success']:
            stats = analyze_result['basic_stats']
            props = analyze_result['text_properties']
            print(f"Analysis: {stats['total_words']} words, {props['lexical_diversity']:.2f} diversity")
        
        # Clean up test file
        try:
            os.remove("test_text.txt")
            print("\nTest file cleaned up")
        except:
            pass
    
    print("\n=== Text Processor Test Complete ===")