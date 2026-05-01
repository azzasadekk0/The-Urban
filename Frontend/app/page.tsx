"use client";

import { useState, useCallback } from "react";
import { SidebarNav } from "@/components/urban/sidebar-nav";
import { ChatContent } from "@/components/urban/chat-content";
import { KnowledgeIndex } from "@/components/urban/knowledge-index";
import { HistoryContent } from "@/components/urban/history-content";

export default function TheUrbanDashboard() {
  const [activeItem, setActiveItem] = useState("chat");
  const [chatResetKey, setChatResetKey] = useState(0);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);

  const handleItemChange = useCallback((item: string) => {
    if (item === "new") {
      setChatResetKey((k) => k + 1);
      setSelectedSessionId(null);
      setActiveItem("chat");
    } else {
      setActiveItem(item);
    }
  }, []);

  return (
    <div className="flex min-h-screen bg-background">
      <SidebarNav
        activeItem={activeItem}
        onItemChange={handleItemChange}
        isArabic={false}
      />
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        <main className="flex-1 flex flex-col overflow-hidden">

          {activeItem === "chat" && (
            <ChatContent key={chatResetKey} isArabic={false} initialSessionId={selectedSessionId} />
          )}

          {activeItem === "knowledge" && (
            <div className="flex-1 overflow-y-auto p-4">
              <KnowledgeIndex isArabic={false} />
            </div>
          )}

          {activeItem === "history" && (
            <HistoryContent onSelectSession={(id) => {
              setSelectedSessionId(id);
              setChatResetKey((k) => k + 1);
              setActiveItem("chat");
            }} />
          )}

        </main>
      </div>
    </div>
  );
}
