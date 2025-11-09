import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Mic, MicOff, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
 
const Voice = () => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSupported, setIsSupported] = useState(true);
  const recognitionRef = useRef<any>(null);
  const finalTranscriptRef = useRef("");
 
  useEffect(() => {
    // Configure browser speech recognition once on mount.
    if (typeof window === "undefined") {
      return;
    }
 
    const speechRecognitionConstructor =
      (window as typeof window & Record<string, any>).SpeechRecognition ||
      (window as typeof window & Record<string, any>).webkitSpeechRecognition;
 
    if (!speechRecognitionConstructor) {
      setIsSupported(false);
      return;
    }
 
    const recognition = new speechRecognitionConstructor();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";
 
    const sendTranscript = async (text: string) => {
      try {
        const response = await fetch("http://localhost:8000/query", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ input: text }),
        });
 
        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`);
        }
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : "An unknown network error occurred.";
        setError(`Failed to send transcript: ${message}`);
      }
    };
 
    recognition.onresult = (event: any) => {
      let interimTranscript = "";
 
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        const text = result[0].transcript;
 
        if (result.isFinal) {
          finalTranscriptRef.current += text;
        } else {
          interimTranscript += text;
        }
      }
 
      setTranscript(
        `${finalTranscriptRef.current}${interimTranscript}`.trim()
      );
      setError(null);
    };
 
    recognition.onerror = (event: any) => {
      const message =
        event.error === "not-allowed"
          ? "Microphone access denied. Please allow microphone permissions."
          : event.error === "no-speech"
            ? "No speech detected. Please try again."
            : `Speech recognition error: ${event.error}`;
      setError(message);
      setIsListening(false);
    };
 
    recognition.onend = () => {
      setIsListening(false);
      const textToSend = finalTranscriptRef.current.trim();
      if (textToSend) {
        void sendTranscript(textToSend);
      }
    };
 
    recognitionRef.current = recognition;
 
    return () => {
      recognition.onresult = null;
      recognition.onerror = null;
      recognition.onend = null;
      recognition.stop();
      recognitionRef.current = null;
    };
  }, []);
 
  const toggleListening = () => {
    if (!recognitionRef.current) {
      setError("Speech recognition is not supported in this browser.");
      return;
    }
 
    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
      return;
    }
 
    try {
      setTranscript("");
      setError(null);
      finalTranscriptRef.current = "";
      recognitionRef.current.start();
      setIsListening(true);
    } catch (err) {
      const message =
        err instanceof DOMException && err.name === "InvalidStateError"
          ? "Speech recognition is already running. Please wait a moment and try again."
          : "Unable to start speech recognition. Please try again.";
      setError(message);
      setIsListening(false);
    }
  };
 
  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-6 gap-8">
      {/* Header */}
      <div className="glass rounded-2xl p-6 max-w-md w-full">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center glow-pulse">
            <Sparkles className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-primary via-secondary to-accent bg-clip-text text-transparent">
              AI Assistant
            </h1>
            <p className="text-sm text-muted-foreground">Voice Mode</p>
          </div>
        </div>
      </div>
 
      {/* Voice Visualization */}
      <div className="relative">
        {/* Outer glow rings */}
        {isListening && (
          <>
            <div className="absolute inset-0 rounded-full bg-primary/20 animate-ping" />
            <div className="absolute inset-0 rounded-full bg-accent/20 animate-ping [animation-delay:0.5s]" />
          </>
        )}
 
        {/* Main mic button */}
        <div
          className={cn(
            "relative glass rounded-full p-8 transition-all duration-300",
            isListening && "shadow-[0_0_60px_rgba(0,150,255,0.8)]"
          )}
        >
          <Button
            onClick={toggleListening}
            size="lg"
            className={cn(
              "w-32 h-32 rounded-full transition-all duration-300",
              isListening
                ? "bg-gradient-to-br from-destructive to-destructive/70 hover:shadow-[0_0_40px_rgba(255,50,50,0.6)]"
                : "bg-gradient-to-br from-primary to-primary-glow hover:shadow-[0_0_40px_rgba(0,150,255,0.6)]",
              !isSupported && "opacity-50 cursor-not-allowed"
            )}
            disabled={!isSupported}
          >
            {isListening ? (
              <MicOff className="w-16 h-16" />
            ) : (
              <Mic className="w-16 h-16" />
            )}
          </Button>
        </div>
      </div>
 
      {/* Transcript Display */}
      <div className="glass rounded-2xl p-6 max-w-md w-full min-h-[120px] flex items-center justify-center">
        <div className="flex flex-col gap-2 text-center">
          {transcript ? (
            <p className="text-muted-foreground">{transcript}</p>
          ) : (
            <p className="text-muted-foreground/50">
              {isSupported
                ? isListening
                  ? "Listening..."
                  : "Press the microphone to start speaking"
                : "Speech recognition is not supported in this browser."}
            </p>
          )}
          {error && <p className="text-destructive text-sm">{error}</p>}
        </div>
      </div>
 
      {/* Status Indicator */}
      <div className="glass rounded-full px-6 py-2 flex items-center gap-2">
        <div
          className={cn(
            "w-2 h-2 rounded-full transition-all",
            !isSupported
              ? "bg-destructive animate-pulse"
              : isListening
                ? "bg-primary animate-pulse"
                : "bg-muted"
          )}
        />
        <span className="text-sm text-muted-foreground">
          {!isSupported ? "Not supported" : isListening ? "Listening..." : "Ready"}
        </span>
      </div>
    </div>
  );
};
 
export default Voice;
 