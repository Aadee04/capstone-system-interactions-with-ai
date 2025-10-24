#!/usr/bin/env python3
"""
Windows Text-to-Speech (TTS) Module
Uses Windows SAPI for native text-to-speech functionality
"""

import sys
import threading
import time
from queue import Queue, Empty

try:
    import pyttsx3
except ImportError:
    print("Installing pyttsx3 for Windows TTS...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyttsx3"])
    import pyttsx3

class WindowsTTS:
    """Windows Text-to-Speech handler using pyttsx3 and Windows SAPI"""
    
    def __init__(self):
        """Initialize the TTS engine with default settings"""
        self.engine = None
        self.speech_queue = Queue()
        self.is_speaking = False
        self.speech_thread = None
        self.stop_flag = False
        
        self._initialize_engine()
        self._start_speech_thread()
    
    def _initialize_engine(self):
        """Initialize the pyttsx3 engine with Windows SAPI"""
        try:
            self.engine = pyttsx3.init('sapi5')  # Use Windows SAPI
            
            # Set default properties
            self.set_rate(200)  # Default speaking rate
            self.set_volume(0.8)  # Default volume (0.0 to 1.0)
            
            # Try to set a default voice (prefer female voice if available)
            voices = self.engine.getProperty('voices')
            if voices:
                # Look for a female voice first, fallback to first available
                female_voice = None
                for voice in voices:
                    if 'zira' in voice.name.lower() or 'eva' in voice.name.lower():
                        female_voice = voice
                        break
                    elif 'female' in voice.name.lower():
                        female_voice = voice
                        break
                
                if female_voice:
                    self.engine.setProperty('voice', female_voice.id)
                    print(f"TTS Voice set to: {female_voice.name}")
                else:
                    self.engine.setProperty('voice', voices[0].id)
                    print(f"TTS Voice set to: {voices[0].name}")
            
            print("Windows TTS initialized successfully")
            
        except Exception as e:
            print(f"Failed to initialize TTS engine: {e}")
            self.engine = None
    
    def _start_speech_thread(self):
        """Start the background thread for speech processing"""
        self.speech_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self.speech_thread.start()
    
    def _speech_worker(self):
        """Background worker thread that processes speech queue"""
        while not self.stop_flag:
            try:
                # Wait for speech request with timeout
                text, priority = self.speech_queue.get(timeout=1.0)
                
                if self.engine and text.strip():
                    self.is_speaking = True
                    print(f"[TTS] Speaking: {text[:50]}{'...' if len(text) > 50 else ''}")
                    
                    try:
                        self.engine.say(text)
                        self.engine.runAndWait()
                    except Exception as e:
                        print(f"[TTS] Error during speech: {e}")
                    
                    self.is_speaking = False
                
                self.speech_queue.task_done()
                
            except Empty:
                continue  # Timeout, continue loop
            except Exception as e:
                print(f"[TTS] Worker thread error: {e}")
    
    def speak(self, text, priority=0):
        """
        Add text to speech queue
        
        Args:
            text (str): Text to speak
            priority (int): Priority level (0=normal, 1=high). Higher priority interrupts current speech.
        """
        if not text or not text.strip():
            return
        
        # If high priority, clear queue and stop current speech
        if priority > 0:
            self.stop_current_speech()
            # Clear existing queue
            while not self.speech_queue.empty():
                try:
                    self.speech_queue.get_nowait()
                    self.speech_queue.task_done()
                except Empty:
                    break
        
        # Add to queue
        self.speech_queue.put((text.strip(), priority))
    
    def speak_immediately(self, text):
        """
        Speak text immediately, interrupting any current speech
        
        Args:
            text (str): Text to speak immediately
        """
        self.speak(text, priority=1)
    
    def stop_current_speech(self):
        """Stop any currently playing speech"""
        if self.engine and self.is_speaking:
            try:
                self.engine.stop()
            except Exception as e:
                print(f"[TTS] Error stopping speech: {e}")
    
    def is_busy(self):
        """Check if TTS is currently speaking"""
        return self.is_speaking or not self.speech_queue.empty()
    
    def wait_until_done(self, timeout=30):
        """
        Wait until all queued speech is complete
        
        Args:
            timeout (int): Maximum time to wait in seconds
        """
        start_time = time.time()
        while self.is_busy() and (time.time() - start_time) < timeout:
            time.sleep(0.1)
    
    def set_rate(self, rate):
        """
        Set speaking rate
        
        Args:
            rate (int): Speaking rate (typically 100-300)
        """
        if self.engine:
            try:
                self.engine.setProperty('rate', rate)
                print(f"[TTS] Speaking rate set to: {rate}")
            except Exception as e:
                print(f"[TTS] Error setting rate: {e}")
    
    def set_volume(self, volume):
        """
        Set speaking volume
        
        Args:
            volume (float): Volume level (0.0 to 1.0)
        """
        if self.engine:
            try:
                volume = max(0.0, min(1.0, volume))  # Clamp between 0 and 1
                self.engine.setProperty('volume', volume)
                print(f"[TTS] Volume set to: {volume}")
            except Exception as e:
                print(f"[TTS] Error setting volume: {e}")
    
    def set_voice(self, voice_index=None, voice_name=None):
        """
        Set TTS voice
        
        Args:
            voice_index (int): Index of voice to use
            voice_name (str): Name of voice to search for
        """
        if not self.engine:
            return
        
        try:
            voices = self.engine.getProperty('voices')
            if not voices:
                print("[TTS] No voices available")
                return
            
            selected_voice = None
            
            if voice_name:
                # Search for voice by name
                for voice in voices:
                    if voice_name.lower() in voice.name.lower():
                        selected_voice = voice
                        break
            elif voice_index is not None:
                # Select by index
                if 0 <= voice_index < len(voices):
                    selected_voice = voices[voice_index]
            
            if selected_voice:
                self.engine.setProperty('voice', selected_voice.id)
                print(f"[TTS] Voice changed to: {selected_voice.name}")
            else:
                print(f"[TTS] Voice not found")
                
        except Exception as e:
            print(f"[TTS] Error setting voice: {e}")
    
    def list_voices(self):
        """List all available voices"""
        if not self.engine:
            print("[TTS] Engine not initialized")
            return []
        
        try:
            voices = self.engine.getProperty('voices')
            if voices:
                print("[TTS] Available voices:")
                for i, voice in enumerate(voices):
                    print(f"  {i}: {voice.name} (ID: {voice.id})")
                return [(i, voice.name, voice.id) for i, voice in enumerate(voices)]
            else:
                print("[TTS] No voices available")
                return []
        except Exception as e:
            print(f"[TTS] Error listing voices: {e}")
            return []
    
    def get_current_settings(self):
        """Get current TTS settings"""
        if not self.engine:
            return {"error": "Engine not initialized"}
        
        try:
            return {
                "rate": self.engine.getProperty('rate'),
                "volume": self.engine.getProperty('volume'),
                "voice": self.engine.getProperty('voice')
            }
        except Exception as e:
            print(f"[TTS] Error getting settings: {e}")
            return {"error": str(e)}
    
    def shutdown(self):
        """Clean shutdown of TTS system"""
        print("[TTS] Shutting down...")
        self.stop_flag = True
        self.stop_current_speech()
        
        # Wait for thread to finish
        if self.speech_thread and self.speech_thread.is_alive():
            self.speech_thread.join(timeout=2.0)
        
        if self.engine:
            try:
                self.engine.stop()
            except:
                pass
        
        print("[TTS] Shutdown complete")


# Global TTS instance
_tts_instance = None

def get_tts():
    """Get the global TTS instance (singleton pattern)"""
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = WindowsTTS()
    return _tts_instance

def speak(text, priority=0):
    """Convenience function to speak text using global TTS instance"""
    tts = get_tts()
    tts.speak(text, priority)

def speak_immediately(text):
    """Convenience function to speak text immediately"""
    tts = get_tts()
    tts.speak_immediately(text)

def stop_speech():
    """Convenience function to stop current speech"""
    tts = get_tts()
    tts.stop_current_speech()

def is_speaking():
    """Convenience function to check if TTS is busy"""
    tts = get_tts()
    return tts.is_busy()

def shutdown_tts():
    """Convenience function to shutdown TTS"""
    global _tts_instance
    if _tts_instance:
        _tts_instance.shutdown()
        _tts_instance = None

# Test functionality
if __name__ == "__main__":
    print("=== Windows TTS Test ===")
    
    tts = WindowsTTS()
    
    # List available voices
    tts.list_voices()
    
    # Test basic speech
    print("\n1. Testing basic speech:")
    tts.speak("Hello! This is a test of the Windows text to speech system.")
    tts.wait_until_done()
    
    # Test different rates
    print("\n2. Testing different speaking rates:")
    tts.set_rate(150)
    tts.speak("This is slow speech.")
    tts.wait_until_done()
    
    tts.set_rate(250)
    tts.speak("This is fast speech.")
    tts.wait_until_done()
    
    # Test volume
    print("\n3. Testing volume control:")
    tts.set_volume(0.5)
    tts.speak("This is at 50 percent volume.")
    tts.wait_until_done()
    
    # Test immediate speech (interrupting)
    print("\n4. Testing immediate speech:")
    tts.speak("This is a long sentence that should be interrupted by the next one.")
    time.sleep(1)  # Let it start speaking
    tts.speak_immediately("Interruption! This should stop the previous speech.")
    tts.wait_until_done()
    
    print("\n5. Current settings:")
    settings = tts.get_current_settings()
    print(f"Settings: {settings}")
    
    tts.shutdown()
    print("\n=== TTS Test Complete ===")