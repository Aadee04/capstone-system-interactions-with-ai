import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

const Chat = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      content: "Hello! I'm your AI assistant. How can I help you today?",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsTyping(true);
    setError(null);

    try {
      const response = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ input: userMessage.content }),
      });

      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }

      const contentType = response.headers.get("content-type") ?? "";
      let assistantText = "";

      if (contentType.includes("application/json")) {
        const data = await response.json();
        if (typeof data === "string") {
          assistantText = data;
        } else if (typeof data === "object" && data !== null) {
          assistantText =
            data.response || data.answer || data.output || JSON.stringify(data);
        }
      } else {
        assistantText = await response.text();
      }

      if (!assistantText.trim()) {
        assistantText = "I didn't receive a response. Please try again.";
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: assistantText,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "An unknown network error occurred.";
      setError(`Failed to send message: ${message}`);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="flex flex-col h-screen p-6 gap-6">
      {/* Header */}
      <div className="glass rounded-2xl p-6">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center glow-pulse">
            <Sparkles className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-primary via-secondary to-accent bg-clip-text text-transparent">
              AI Assistant
            </h1>
            <p className="text-sm text-muted-foreground">Chat Mode</p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 glass rounded-2xl overflow-hidden">
        <ScrollArea className="h-full p-6" ref={scrollRef}>
          <div className="space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  "flex",
                  message.role === "user" ? "justify-end" : "justify-start"
                )}
              >
                <div
                  className={cn(
                    "max-w-[80%] rounded-2xl px-4 py-3",
                    message.role === "user"
                      ? "bg-gradient-to-br from-primary to-primary-glow text-primary-foreground"
                      : "glass border border-glass-border"
                  )}
                >
                  <p className="text-sm">{message.content}</p>
                  <span className="text-xs opacity-70 mt-1 block">
                    {message.timestamp.toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
              </div>
            ))}
            {isTyping && (
              <div className="flex justify-start">
                <div className="glass border border-glass-border rounded-2xl px-4 py-3">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 rounded-full bg-primary animate-bounce" />
                    <div className="w-2 h-2 rounded-full bg-secondary animate-bounce [animation-delay:0.2s]" />
                    <div className="w-2 h-2 rounded-full bg-accent animate-bounce [animation-delay:0.4s]" />
                  </div>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>
      </div>

      {/* Input */}
      <div className="glass rounded-2xl p-4">
        <div className="flex gap-3">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && handleSend()}
            placeholder="Type your message..."
            className="flex-1 bg-input border-glass-border focus:border-primary transition-all"
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim()}
            className="bg-gradient-to-br from-primary to-primary-glow hover:shadow-[0_0_30px_rgba(0,150,255,0.5)] transition-all"
          >
            <Send className="w-5 h-5" />
          </Button>
        </div>
        {error && (
          <p className="mt-2 text-sm text-destructive text-center">{error}</p>
        )}
      </div>
    </div>
  );
};

export default Chat;
