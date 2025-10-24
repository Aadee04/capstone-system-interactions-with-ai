#!/usr/bin/env python3
"""
TTS Integration for Agent System
Integrates Windows TTS with the agent responses
"""

import sys
import os

from modules.tts.windows_tts import get_tts, speak, speak_immediately, stop_speech, is_speaking
from langchain_core.messages import AIMessage, ToolMessage

class AgentTTSIntegration:
    """Integration class to handle TTS for agent responses"""
    
    def __init__(self, enabled=True, speak_chatter=True, speak_tool_results=True, speak_errors=True):
        """
        Initialize TTS integration
        
        Args:
            enabled (bool): Whether TTS is enabled
            speak_chatter (bool): Whether to speak chatter agent responses
            speak_tool_results (bool): Whether to speak tool execution results
            speak_errors (bool): Whether to speak error messages
        """
        self.enabled = enabled
        self.speak_chatter = speak_chatter
        self.speak_tool_results = speak_tool_results
        self.speak_errors = speak_errors
        self.tts = get_tts() if enabled else None
        
        if enabled:
            print("[Agent TTS] Integration enabled")
        else:
            print("[Agent TTS] Integration disabled")
    
    def process_agent_response(self, message, agent_type="unknown"):
        """
        Process an agent response and speak if appropriate
        
        Args:
            message: The message object (AIMessage, ToolMessage, etc.)
            agent_type (str): Type of agent ("chatter", "tooler", "coder", "verifier")
        """
        if not self.enabled:
            return
        
        try:
            if isinstance(message, AIMessage):
                self._handle_ai_message(message, agent_type)
            elif isinstance(message, ToolMessage):
                self._handle_tool_message(message, agent_type)
            elif isinstance(message, dict) and "content" in message:
                self._handle_dict_message(message, agent_type)
            elif hasattr(message, "content"):
                self._handle_generic_message(message, agent_type)
                
        except Exception as e:
            print(f"[Agent TTS] Error processing message: {e}")
    
    def _handle_ai_message(self, message, agent_type):
        """Handle AIMessage responses"""
        content = message.content.strip() if message.content else ""
        
        if not content:
            return
        
        if agent_type == "chatter" and self.speak_chatter:
            # Speak chatter responses immediately (they're meant for the user)
            self._speak_with_preprocessing(content, priority=0)
            
        elif agent_type in ["verifier", "planner"] and self.speak_errors:
            # Speak important system messages
            if any(word in content.lower() for word in ["error", "failed", "problem", "issue"]):
                self._speak_with_preprocessing(f"System message: {content}", priority=1)
    
    def _handle_tool_message(self, message, agent_type):
        """Handle ToolMessage responses (tool execution results)"""
        content = message.content.strip() if message.content else ""
        
        if not content or not self.speak_tool_results:
            return
        
        # Check if it's an error message
        is_error = any(word in content.lower() for word in ["error", "failed", "exception", "not found", "invalid"])
        
        if is_error and self.speak_errors:
            self._speak_with_preprocessing(f"Tool error: {content}", priority=1)
        elif not is_error:
            # Successful tool execution
            self._speak_with_preprocessing(f"Task completed: {content}", priority=0)
    
    def _handle_dict_message(self, message, agent_type):
        """Handle dictionary message format"""
        content = message.get("content", "").strip()
        
        if content and agent_type == "chatter" and self.speak_chatter:
            self._speak_with_preprocessing(content, priority=0)
    
    def _handle_generic_message(self, message, agent_type):
        """Handle generic message objects with content attribute"""
        content = getattr(message, "content", "").strip()
        
        if content and agent_type == "chatter" and self.speak_chatter:
            self._speak_with_preprocessing(content, priority=0)
    
    def _speak_with_preprocessing(self, text, priority=0):
        """
        Preprocess text and speak it
        
        Args:
            text (str): Text to speak
            priority (int): Speech priority
        """
        # Clean up text for better speech
        processed_text = self._preprocess_text(text)
        
        if processed_text:
            if priority > 0:
                speak_immediately(processed_text)
            else:
                speak(processed_text, priority)
    
    def _preprocess_text(self, text):
        """
        Preprocess text to make it more suitable for TTS
        
        Args:
            text (str): Original text
            
        Returns:
            str: Processed text
        """
        if not text:
            return ""
        
        # Remove common markdown/formatting
        text = text.replace("**", "").replace("*", "").replace("`", "")
        
        # Handle special characters and abbreviations
        replacements = {
            "&": "and",
            "@": "at",
            "#": "number",
            "%": "percent",
            "\\n": " ",
            "\\t": " ",
            "  ": " ",  # Multiple spaces
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Limit length for TTS (very long text can be problematic)
        if len(text) > 500:
            text = text[:497] + "..."
        
        return text.strip()
    
    def speak_system_message(self, message, priority=1):
        """
        Speak a system message with high priority
        
        Args:
            message (str): System message to speak
            priority (int): Priority level (default high)
        """
        if self.enabled:
            self._speak_with_preprocessing(f"System: {message}", priority)
    
    def speak_user_notification(self, message):
        """
        Speak a user notification
        
        Args:
            message (str): Notification message
        """
        if self.enabled:
            self._speak_with_preprocessing(message, priority=0)
    
    def enable_tts(self):
        """Enable TTS"""
        self.enabled = True
        if not self.tts:
            self.tts = get_tts()
        print("[Agent TTS] Enabled")
    
    def disable_tts(self):
        """Disable TTS"""
        self.enabled = False
        if is_speaking():
            stop_speech()
        print("[Agent TTS] Disabled")
    
    def toggle_tts(self):
        """Toggle TTS on/off"""
        if self.enabled:
            self.disable_tts()
        else:
            self.enable_tts()
    
    def configure(self, speak_chatter=None, speak_tool_results=None, speak_errors=None):
        """
        Configure TTS settings
        
        Args:
            speak_chatter (bool): Whether to speak chatter responses
            speak_tool_results (bool): Whether to speak tool results
            speak_errors (bool): Whether to speak error messages
        """
        if speak_chatter is not None:
            self.speak_chatter = speak_chatter
        if speak_tool_results is not None:
            self.speak_tool_results = speak_tool_results
        if speak_errors is not None:
            self.speak_errors = speak_errors
        
        print(f"[Agent TTS] Configuration updated: chatter={self.speak_chatter}, tools={self.speak_tool_results}, errors={self.speak_errors}")
    
    def get_status(self):
        """Get current TTS status"""
        return {
            "enabled": self.enabled,
            "speaking": is_speaking() if self.enabled else False,
            "speak_chatter": self.speak_chatter,
            "speak_tool_results": self.speak_tool_results,
            "speak_errors": self.speak_errors
        }


# Global TTS integration instance
_tts_integration = None

def get_agent_tts():
    """Get the global agent TTS integration instance"""
    global _tts_integration
    if _tts_integration is None:
        _tts_integration = AgentTTSIntegration()
    return _tts_integration

def process_message(message, agent_type="unknown"):
    """Convenience function to process a message for TTS"""
    integration = get_agent_tts()
    integration.process_agent_response(message, agent_type)

def speak_system(message):
    """Convenience function to speak system messages"""
    integration = get_agent_tts()
    integration.speak_system_message(message)

def speak_notification(message):
    """Convenience function to speak notifications"""
    integration = get_agent_tts()
    integration.speak_user_notification(message)

def toggle_agent_tts():
    """Convenience function to toggle TTS"""
    integration = get_agent_tts()
    integration.toggle_tts()

def configure_agent_tts(**kwargs):
    """Convenience function to configure TTS"""
    integration = get_agent_tts()
    integration.configure(**kwargs)

# Test the integration
if __name__ == "__main__":
    print("=== Agent TTS Integration Test ===")
    
    integration = AgentTTSIntegration()
    
    # Test chatter response
    print("\\n1. Testing chatter response:")
    chatter_msg = AIMessage(content="Hello! How can I assist you today?")
    integration.process_agent_response(chatter_msg, "chatter")
    
    # Test tool result
    print("\\n2. Testing tool result:")
    tool_msg = ToolMessage(content="Calculator opened successfully", tool_call_id="test")
    integration.process_agent_response(tool_msg, "tooler")
    
    # Test error message
    print("\\n3. Testing error message:")
    error_msg = ToolMessage(content="Error: Application not found", tool_call_id="test")
    integration.process_agent_response(error_msg, "tooler")
    
    # Test system message
    print("\\n4. Testing system message:")
    integration.speak_system_message("Agent system started successfully")
    
    # Wait for speech to complete
    import time
    time.sleep(3)
    
    print("\\n=== Agent TTS Integration Test Complete ===")