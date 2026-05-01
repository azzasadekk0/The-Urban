"use client";

import { useState } from "react";
import {
  MessageSquare,
  ChevronLeft,
  ChevronRight,
  History,
  BookOpen,
  Plus,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface SidebarNavProps {
  activeItem: string;
  onItemChange: (item: string) => void;
  isArabic: boolean;
}

const navItems = [
  { id: "new", icon: Plus, labelEn: "New Conversation", labelAr: "محادثة جديدة" },
  { id: "chat", icon: MessageSquare, labelEn: "Ask The Urban", labelAr: "اسأل العمران" },
  { id: "knowledge", icon: BookOpen, labelEn: "Knowledge Base", labelAr: "قاعدة المعرفة" },
  { id: "history", icon: History, labelEn: "History", labelAr: "السجل" },
];

export function SidebarNav({ activeItem, onItemChange, isArabic }: SidebarNavProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          "flex flex-col h-screen bg-sidebar border-r border-sidebar-border transition-all duration-300",
          collapsed ? "w-16" : "w-64",
          isArabic && "border-r-0 border-l"
        )}
      >
        {/* Logo */}
        <div className={cn(
          "flex items-center gap-3 p-4 border-b border-sidebar-border",
          collapsed && "justify-center"
        )}>
          <div className="w-10 h-10 rounded-lg overflow-hidden shrink-0">
            <img 
              src="/logo.jpg" 
              alt="The Urban Logo" 
              className="w-full h-full object-cover"
            />
          </div>
          {!collapsed && (
            <div className={cn("flex flex-col", isArabic && "text-right")}>
              <span className="font-bold text-foreground text-lg">The Urban</span>
              <span className="text-xs text-muted-foreground">
                {isArabic ? "نظام الخبير الذكي" : "AI Expert System"}
              </span>
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          <div className={cn("text-xs font-semibold text-muted-foreground px-3 py-2", collapsed && "hidden")}>
            {isArabic ? "القائمة الرئيسية" : "MAIN MENU"}
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeItem === item.id;
            const label = isArabic ? item.labelAr : item.labelEn;

            const button = (
              <Button
                key={item.id}
                variant="ghost"
                onClick={() => onItemChange(item.id)}
                className={cn(
                  "w-full justify-start gap-3 h-11 px-3 transition-all",
                  isActive
                    ? "bg-primary/10 text-primary font-medium"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary",
                  collapsed && "justify-center px-0",
                  isArabic && !collapsed && "flex-row-reverse text-right"
                )}
              >
                <Icon className={cn("w-5 h-5 shrink-0", isActive && "text-primary")} />
                {!collapsed && <span>{label}</span>}
              </Button>
            );

            if (collapsed) {
              return (
                <Tooltip key={item.id}>
                  <TooltipTrigger asChild>{button}</TooltipTrigger>
                  <TooltipContent side={isArabic ? "left" : "right"} className="bg-card text-card-foreground">
                    {label}
                  </TooltipContent>
                </Tooltip>
              );
            }

            return button;
          })}
        </nav>

        {/* Collapse Toggle */}
        <div className="p-3 border-t border-sidebar-border">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setCollapsed(!collapsed)}
            className={cn(
              "w-full justify-center text-muted-foreground hover:text-foreground hover:bg-secondary"
            )}
          >
            {collapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <>
                <ChevronLeft className="w-4 h-4 mr-2" />
                <span>{isArabic ? "طي القائمة" : "Collapse"}</span>
              </>
            )}
          </Button>
        </div>
      </aside>
    </TooltipProvider>
  );
}
