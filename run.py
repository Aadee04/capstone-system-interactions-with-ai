#!/usr/bin/env python3
"""
Desktop Assistant - Main Entry Point
Provides multiple ways to run the assistant: CLI, STT, or GUI
Designed to work well when compiled to .exe
"""

import sys
import os
import threading
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config/secrets.env")

def import_agent_system():
    """Import agent system with error handling"""
    try:
        from app.agent import app as agent_app
        from langchain_core.messages import HumanMessage
        return agent_app, HumanMessage
    except ImportError as e:
        print(f"Error importing agent system: {e}")
        print("Make sure all dependencies are installed and paths are correct")
        return None, None

def import_stt_system():
    """Import STT system with error handling"""
    try:
        from modules.stt.transcription import start_stt_loop
        return start_stt_loop
    except ImportError as e:
        print(f"Error importing STT system: {e}")
        print("STT functionality will be disabled")
        return None

def import_tts_system():
    """Import TTS system with error handling"""
    try:
        from modules.tts.agent_tts_integration import get_agent_tts, process_message
        return get_agent_tts, process_message
    except ImportError as e:
        print(f"Error importing TTS system: {e}")
        print("TTS functionality will be disabled")
        return None, None

class DesktopAssistant:
    """Main Desktop Assistant class"""
    
    def __init__(self, enable_tts=True, enable_stt=True):
        """
        Initialize the Desktop Assistant
        
        Args:
            enable_tts (bool): Enable text-to-speech
            enable_stt (bool): Enable speech-to-text
        """
        print("🤖 Desktop Assistant Starting...")
        
        # Initialize components
        self.agent_app = None
        self.stt_function = None
        self.tts_integration = None
        self.process_tts_message = None
        self.enable_tts = enable_tts
        self.enable_stt = enable_stt
        self.running = False
        self.stt_thread = None
        
        # Load systems
        self._load_agent_system()
        self._load_stt_system()
        self._load_tts_system()
        
        print("✅ Desktop Assistant Initialized")
    
    def _load_agent_system(self):
        """Load the agent system"""
        print("📝 Loading Agent System...")
        self.agent_app, self.HumanMessage = import_agent_system()
        if self.agent_app:
            print("✅ Agent System Loaded")
        else:
            print("❌ Agent System Failed to Load")
    
    def _load_stt_system(self):
        """Load the STT system"""
        if not self.enable_stt:
            print("🔇 STT Disabled")
            return
            
        print("🎤 Loading STT System...")
        self.stt_function = import_stt_system()
        if self.stt_function:
            print("✅ STT System Loaded")
        else:
            print("❌ STT System Failed to Load")
    
    def _load_tts_system(self):
        """Load the TTS system"""
        if not self.enable_tts:
            print("🔇 TTS Disabled")
            return
            
        print("🔊 Loading TTS System...")
        tts_imports = import_tts_system()
        if tts_imports[0] and tts_imports[1]:
            get_tts_func, self.process_tts_message = tts_imports
            self.tts_integration = get_tts_func()  # Initialize instance
            print("✅ TTS System Loaded")
        else:
            print("❌ TTS System Failed to Load")
    
    def process_user_input(self, user_input, source="CLI"):
        """
        Process user input through the agent system
        
        Args:
            user_input (str): User input text
            source (str): Source of input (CLI, STT, GUI)
            
        Returns:
            bool: True if processing was successful
        """
        if not self.agent_app or not user_input.strip():
            return False
        
        try:
            print(f"[{source}] User: {user_input}")
            
            # Create input for agent
            inputs = {
                "messages": [self.HumanMessage(content=user_input)], 
                "completed_tools": []
            }
            
            # Process through agent system
            responses = list(self.agent_app.stream(inputs, stream_mode="values"))
            
            # Handle responses
            for response in responses:
                if "messages" in response and response["messages"]:
                    last_message = response["messages"][-1]
                    
                    # Print response
                    if hasattr(last_message, "content") and last_message.content:
                        print(f"[Assistant] {last_message.content}")
                        
                        # Process with TTS if available
                        if self.process_tts_message:
                            # Try to determine agent type from response context
                            agent_type = self._detect_agent_type(response)
                            self.process_tts_message(last_message, agent_type)
                    
                    # Handle tool calls
                    elif hasattr(last_message, "tool_calls") and last_message.tool_calls:
                        print(f"[Tool Calls] {len(last_message.tool_calls)} tools executed")
            
            return True
            
        except Exception as e:
            error_msg = f"Error processing input: {e}"
            print(f"❌ {error_msg}")
            if self.tts_integration:
                self.tts_integration.speak_system_message(error_msg)
            return False
    
    def _detect_agent_type(self, response):
        """Try to detect which agent type generated the response"""
        # This is a simple heuristic - you might want to improve this
        # based on your agent state or response patterns
        if "current_executor" in response:
            executor = response.get("current_executor", "")
            if "chatter" in executor:
                return "chatter"
            elif "tooler" in executor:
                return "tooler" 
            elif "coder" in executor:
                return "coder"
        
        return "unknown"
    
    def run_cli_mode(self):
        """Run in CLI mode - traditional text input/output"""
        print("\n🖥️  CLI Mode Started")
        print("Type 'exit', 'quit', or 'q' to stop")
        print("Type 'toggle-tts' to toggle text-to-speech")
        print("-" * 50)
        
        while True:
            try:
                user_input = input("\n💬 You: ").strip()
                
                if user_input.lower() in ["exit", "quit", "q"]:
                    print("👋 Goodbye!")
                    break
                
                if user_input.lower() == "toggle-tts":
                    if self.tts_integration:
                        self.tts_integration.toggle_tts()
                        status = "enabled" if self.tts_integration.enabled else "disabled"
                        print(f"🔊 TTS {status}")
                    else:
                        print("❌ TTS not available")
                    continue
                
                if user_input:
                    self.process_user_input(user_input, "CLI")
            
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error in CLI mode: {e}")
    
    def run_stt_mode(self):
        """Run in STT mode - voice input with text output"""
        if not self.stt_function:
            print("❌ STT not available. Falling back to CLI mode.")
            self.run_cli_mode()
            return
        
        print("\n🎤 Voice Mode Started")
        print("Say the wake word to activate, or press Ctrl+C to stop")
        print("-" * 50)
        
        self.running = True
        
        # Start STT in background thread
        self.stt_thread = threading.Thread(target=self._run_stt_loop, daemon=True)
        self.stt_thread.start()
        
        # Keep main thread alive and handle commands
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping voice mode...")
            self.running = False
            if self.stt_thread:
                self.stt_thread.join(timeout=2)
            print("👋 Goodbye!")
    
    def _run_stt_loop(self):
        """Run STT loop in background thread"""
        try:
            self.stt_function()
        except Exception as e:
            print(f"❌ STT Error: {e}")
            self.running = False
    
    def run_gui_mode(self):
        """Run in GUI mode - placeholder for future GUI implementation"""
        print("\n🖼️  GUI Mode")
        print("GUI mode is not implemented yet.")
        print("This is where the GUI would be initialized when converted to .exe")
        print("Falling back to CLI mode...")
        self.run_cli_mode()
    
    def shutdown(self):
        """Clean shutdown of all systems"""
        print("🛑 Shutting down Desktop Assistant...")
        
        self.running = False
        
        # Shutdown TTS
        if self.tts_integration:
            self.tts_integration.disable_tts()
        
        # Wait for STT thread
        if self.stt_thread and self.stt_thread.is_alive():
            self.stt_thread.join(timeout=3)
        
        print("✅ Shutdown complete")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Desktop Assistant")
    parser.add_argument(
        "--mode", 
        choices=["cli", "voice", "gui"], 
        default="cli",
        help="Run mode: cli (text), voice (speech), or gui (graphical)"
    )
    parser.add_argument(
        "--no-tts", 
        action="store_true", 
        help="Disable text-to-speech"
    )
    parser.add_argument(
        "--no-stt", 
        action="store_true", 
        help="Disable speech-to-text"
    )
    
    args = parser.parse_args()
    
    # Initialize assistant
    assistant = DesktopAssistant(
        enable_tts=not args.no_tts,
        enable_stt=not args.no_stt
    )
    
    try:
        # Run in selected mode
        if args.mode == "cli":
            assistant.run_cli_mode()
        elif args.mode == "voice":
            assistant.run_stt_mode()
        elif args.mode == "gui":
            assistant.run_gui_mode()
    
    except Exception as e:
        print(f"❌ Fatal error: {e}")
    
    finally:
        assistant.shutdown()

if __name__ == "__main__":
    main()
