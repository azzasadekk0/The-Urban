"use client";

import { useState, useEffect } from "react";
import { History, MessageSquare, Loader2, Clock, Languages } from "lucide-react";
import { cn } from "@/lib/utils";

interface Session {
  session_id: string;
  created_at: string;
  updated_at: string;
  language: string;
  message_count: number;
  preview: string | null;
}

interface HistoryContentProps {
  onSelectSession?: (sessionId: string) => void;
}

function formatTime(isoString: string): string {
  try {
    const d = new Date(isoString + "Z");
    return d.toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return isoString;
  }
}

export function HistoryContent({ onSelectSession }: HistoryContentProps) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchSessions() {
      try {
        const res = await fetch("/api/chat/sessions");
        if (!res.ok) throw new Error("Failed to fetch sessions");
        const data = await res.json();
        setSessions(data.sessions || []);
      } catch (err) {
        console.error(err);
        setError("Could not load history. Is the backend running?");
      } finally {
        setIsLoading(false);
      }
    }
    fetchSessions();
  }, []);

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground gap-2">
        <Loader2 className="h-5 w-5 animate-spin" />
        Loading history…
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center text-red-500 p-8 text-center">
        {error}
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground gap-3 p-8">
        <History className="h-12 w-12 opacity-30" />
        <p className="text-sm">No past conversations yet.</p>
        <p className="text-xs opacity-60">Start a chat and it will appear here.</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center gap-2 mb-6">
          <History className="h-5 w-5 text-primary" />
          <h2 className="text-lg font-bold text-foreground">Conversation History</h2>
          <span className="ml-auto text-xs text-muted-foreground bg-secondary px-2 py-1 rounded-full">
            {sessions.length} sessions
          </span>
        </div>

        <div className="space-y-3">
          {sessions.map((session) => (
            <button
              key={session.session_id}
              onClick={() => onSelectSession?.(session.session_id)}
              className={cn(
                "w-full text-left rounded-lg border border-border bg-card p-4",
                "hover:border-primary/40 hover:bg-secondary/40 transition-all group"
              )}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 min-w-0">
                  <div className="p-2 rounded-md bg-primary/10 shrink-0 mt-0.5">
                    <MessageSquare className="h-4 w-4 text-primary" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">
                      {session.preview ?? "Empty conversation"}
                    </p>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        {formatTime(session.updated_at)}
                      </span>
                      <span className="flex items-center gap-1 text-xs text-muted-foreground">
                        <MessageSquare className="h-3 w-3" />
                        {session.message_count} messages
                      </span>
                      {session.language && (
                        <span className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Languages className="h-3 w-3" />
                          {session.language.toUpperCase()}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <span className="text-xs text-primary opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                  Open →
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
