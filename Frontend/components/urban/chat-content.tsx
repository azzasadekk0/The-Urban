"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Paperclip, Mic, Bot, User, FileText, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

// Detect if a message is predominantly Arabic
function detectLanguage(text: string): "ar" | "en" {
  const arabicChars = (text.match(/[\u0600-\u06FF]/g) || []).length;
  return arabicChars > text.length * 0.2 ? "ar" : "en";
}

// Simple inline markdown renderer — no external deps
function SimpleMarkdown({ text }: { text: string }) {
  const lines = text.split("\n");
  return (
    <div className="space-y-1">
      {lines.map((line, i) => {
        // Numbered list
        if (/^\d+\.\s/.test(line)) {
          return <p key={i} className="ml-4">{renderInline(line.replace(/^\d+\.\s/, ""))}</p>;
        }
        // Bullet list
        if (/^[-*]\s/.test(line)) {
          return <p key={i} className="ml-4">• {renderInline(line.replace(/^[-*]\s/, ""))}</p>;
        }
        // Bold header-ish lines (standalone **text**)
        if (/^\*\*.*\*\*$/.test(line.trim())) {
          return <p key={i} className="font-semibold mt-2">{renderInline(line)}</p>;
        }
        // Separator
        if (line.trim() === "---") {
          return <hr key={i} className="border-border my-2" />;
        }
        // Empty line → spacing
        if (line.trim() === "") {
          return <div key={i} className="h-1" />;
        }
        return <p key={i}>{renderInline(line)}</p>;
      })}
    </div>
  );
}

function renderInline(text: string): React.ReactNode {
  // Bold: **text**
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return <span key={i}>{part}</span>;
  });
}

interface ChatContentProps {
  isArabic: boolean;
  initialSessionId?: string | null;
}

interface Message {
  id: string;
  type: "user" | "assistant";
  content: string;
  sources?: { name: string }[];
  timestamp: string;
}

const cleanText = (text: string) => {
  if (!text) return "";
  let t = text;
  // Remove internal debug key-value pairs only (keep markdown formatting)
  t = t.replace(/\*\*(Language|Context|Requires Calculation|Topics Detected|Reasoning|Chunks used in context|Suppressed laws|Calculation included|Response language|Active laws|Chunks retrieved|Status|Type|Extracted params|Error)[:\s]\*\*[^\n]*/gi, "");
  // Collapse excessive blank lines
  t = t.replace(/\n{3,}/g, "\n\n");
  return t.trim();
};

export function ChatContent({ isArabic, initialSessionId = null }: ChatContentProps) {
  const [inputValue, setInputValue] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(initialSessionId);
  const [isLoading, setIsLoading] = useState(false);
  // Tracks the UI language dynamically based on what the user is typing
  const [uiLang, setUiLang] = useState<"ar" | "en">(isArabic ? "ar" : "en");
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Update UI language whenever input changes
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setInputValue(val);
    if (val.trim().length > 2) {
      setUiLang(detectLanguage(val));
    }
  };

  const isRtl = uiLang === "ar";

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (initialSessionId) {
      const loadHistory = async () => {
        setIsLoading(true);
        try {
          const res = await fetch(`/api/chat/history/${initialSessionId}`);
          if (res.ok) {
            const data = await res.json();
            const history = data.history || [];
            const mapped = history.map((m: any, i: number) => {
              const d = new Date(m.ts + "Z");
              const ts = d.toLocaleString(undefined, { hour: '2-digit', minute: '2-digit' });
              return {
                id: `hist-${i}`,
                type: m.role,
                content: m.role === "assistant" ? cleanText(m.content) : m.content,
                timestamp: ts
              };
            });
            setMessages(mapped);
          }
        } catch (err) {
          console.error("Failed to load session history", err);
        } finally {
          setIsLoading(false);
        }
      };
      loadHistory();
    }
  }, [initialSessionId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = inputValue.trim();
    setInputValue("");
    
    const now = new Date();
    const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const newUserMsg: Message = {
      id: Date.now().toString(),
      type: "user",
      content: userMessage,
      timestamp: timeString
    };
    
    setMessages(prev => [...prev, newUserMsg]);
    setIsLoading(true);

    try {
      const detectedLang = detectLanguage(userMessage);
      // Also update UI direction for the response
      setUiLang(detectedLang);

      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          message: userMessage,
          language: detectedLang
        })
      });

      if (!response.ok) throw new Error("Failed to get response");
      
      const data = await response.json();
      
      if (!sessionId && data.session_id) {
        setSessionId(data.session_id);
      }

      const sources = (data.active_laws || []).map((law: string) => ({ name: law }));
      const asstTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      const asstMsg: Message = {
        id: Date.now().toString() + "-asst",
        type: "assistant",
        content: cleanText(data.response),
        sources: sources.length > 0 ? sources : undefined,
        timestamp: asstTime
      };

      setMessages(prev => [...prev, asstMsg]);
    } catch (error) {
      console.error("Chat error:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col h-screen" dir={isRtl ? "rtl" : "ltr"}>
      {/* Messages Area - scrollable */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-4">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
              {isRtl ? "ابدأ المحادثة بسؤال..." : "Start the conversation by asking a question..."}
            </div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  "flex gap-3",
                  message.type === "user" ? "justify-end" : "justify-start",
                  isRtl && "flex-row-reverse"
                )}
              >
                {message.type === "assistant" && (
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-1">
                    <Bot className="w-4 h-4 text-primary" />
                  </div>
                )}
                <div
                  className={cn(
                    "max-w-[80%] rounded-lg p-4",
                    message.type === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted border border-border",
                    isRtl && "text-right"
                  )}
                >
                  <div
                    dir="auto"
                    className={cn(
                      "text-sm leading-relaxed",
                      message.type === "user" ? "text-primary-foreground" : "text-foreground"
                    )}
                  >
                    {message.type === "assistant" ? (
                      <SimpleMarkdown text={message.content} />
                    ) : (
                      <span>{message.content}</span>
                    )}
                  </div>
                  {message.sources && (
                    <div className={cn("flex flex-wrap gap-2 mt-3 pt-3 border-t border-border/50", isRtl && "justify-end")}>
                      {message.sources.map((source, idx) => (
                        <Badge
                          key={idx}
                          variant="secondary"
                          className="text-xs gap-1 cursor-pointer hover:bg-secondary/80 bg-background"
                        >
                          <FileText className="w-3 h-3 text-primary/70" />
                          {source.name}
                        </Badge>
                      ))}
                    </div>
                  )}
                  <p className={cn("text-xs opacity-60 mt-2", message.type === "user" ? "text-primary-foreground/70" : "text-muted-foreground")}>
                    {message.timestamp}
                  </p>
                </div>
                {message.type === "user" && (
                  <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0 mt-1">
                    <User className="w-4 h-4 text-primary-foreground" />
                  </div>
                )}
              </div>
            ))
          )}
          
          {isLoading && (
            <div className={cn("flex gap-3 justify-start", isRtl && "flex-row-reverse")}>
              <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-1">
                <Bot className="w-4 h-4 text-primary" />
              </div>
              <div className={cn("max-w-[80%] rounded-lg p-4 bg-muted border border-border", isRtl && "text-right")}>
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  <span className="text-sm text-muted-foreground">
                    {isRtl ? "جاري التفكير..." : "Thinking..."}
                  </span>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area - fixed at bottom */}
      <div className="shrink-0 p-4 border-t border-border bg-card">
        <div className={cn("flex gap-2", isRtl && "flex-row-reverse")}>
          <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground shrink-0">
            <Paperclip className="w-5 h-5" />
          </Button>
          <Input
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder={isRtl ? "اكتب سؤالك هنا..." : "Type your question here..."}
            className={cn("flex-1 bg-muted/50", isRtl && "text-right")}
            dir={isRtl ? "rtl" : "ltr"}
          />
          <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground shrink-0">
            <Mic className="w-5 h-5" />
          </Button>
          <Button 
            size="icon" 
            onClick={handleSendMessage}
            disabled={isLoading || !inputValue.trim()}
            className="bg-primary hover:bg-primary/90 shrink-0 disabled:opacity-50"
          >
            <Send className={cn("w-4 h-4", isArabic && "rotate-180")} />
          </Button>
        </div>
      </div>
    </div>
  );
}
