"use client"

import { FileText, Scale, Building2, Landmark, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { useState, useEffect } from "react"

interface KnowledgeIndexProps {
  isArabic?: boolean
}

interface DocumentStatus {
  filename: string
  law_name_en: string
  priority: string
  pdf_exists: boolean
  indexed: boolean
  chunk_count: number
}

interface StatusResponse {
  documents: DocumentStatus[]
  ingest_running: boolean
}

const priorityColors: Record<string, string> = {
  P1: "bg-primary/20 text-primary border-primary/30",
  P2: "bg-accent/20 text-accent border-accent/30",
  P3: "bg-emerald-500/20 text-emerald-500 border-emerald-500/30",
  P4: "bg-muted-foreground/20 text-muted-foreground border-muted-foreground/30",
  P5: "bg-muted-foreground/10 text-muted-foreground/70 border-muted-foreground/20",
  P6: "bg-muted-foreground/5 text-muted-foreground/50 border-muted-foreground/10",
}

function getIconForPriority(priority: string) {
  if (priority === "P1") return Scale
  if (priority === "P2") return Landmark
  if (priority === "P3") return Building2
  return FileText
}

export function KnowledgeIndex({ isArabic = false }: KnowledgeIndexProps) {
  const [data, setData] = useState<StatusResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchStatus() {
      try {
        const response = await fetch("/api/status")
        if (!response.ok) throw new Error("Failed to fetch status")
        const json = await response.json()
        setData(json)
      } catch (err) {
        console.error("Error fetching knowledge base status:", err)
        setError("Failed to load knowledge base status. Is the backend running?")
      } finally {
        setIsLoading(false)
      }
    }
    fetchStatus()
  }, [])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8 text-muted-foreground">
        <Loader2 className="h-6 w-6 animate-spin mr-2" />
        Loading Knowledge Base...
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="p-8 text-center text-red-500">
        <p>{error || "Unknown error occurred"}</p>
      </div>
    )
  }

  const enabledCount = data.documents.filter((d) => d.indexed).length

  return (
    <div className="max-w-4xl mx-auto py-8">
      <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-bold text-foreground">
              {isArabic ? "القوانين والتشريعات" : "Knowledge Base"}
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              {isArabic ? "قاعدة بيانات الذكاء الاصطناعي" : "AI Indexed Documents"}
            </p>
          </div>
          <div className="flex flex-col items-end">
            <span className="text-sm font-medium bg-secondary px-3 py-1 rounded-full">
              {enabledCount} / {data.documents.length} {isArabic ? "مفهرس" : "Indexed"}
            </span>
            {data.ingest_running && (
              <span className="text-xs text-primary animate-pulse mt-2 flex items-center gap-1">
                <Loader2 className="h-3 w-3 animate-spin" /> Ingestion Running
              </span>
            )}
          </div>
        </div>
        
        <div className="space-y-3">
          {data.documents.map((doc) => {
            const Icon = getIconForPriority(doc.priority)
            return (
              <div
                key={doc.filename}
                className={cn(
                  "flex items-center justify-between p-4 rounded-lg border transition-all",
                  doc.indexed
                    ? "bg-secondary/30 border-border hover:border-primary/30"
                    : "bg-muted/20 border-transparent opacity-60"
                )}
              >
                <div className="flex items-center gap-4">
                  <div className="p-2 rounded bg-secondary">
                    <Icon className="h-5 w-5 text-muted-foreground" />
                  </div>
                  <div>
                    <p className="text-base font-medium text-foreground">
                      {doc.law_name_en}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <p className="text-xs text-muted-foreground font-mono">
                        {doc.filename}
                      </p>
                      {doc.indexed && (
                        <span className="text-[10px] bg-primary/10 text-primary px-1.5 py-0.5 rounded">
                          {doc.chunk_count} chunks
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {!doc.pdf_exists && (
                    <span className="text-xs text-red-500 bg-red-500/10 px-2 py-1 rounded">
                      Missing PDF
                    </span>
                  )}
                  <span className={cn(
                    "text-xs font-mono font-medium px-2 py-1 rounded border",
                    priorityColors[doc.priority] || priorityColors["P4"]
                  )}>
                    {doc.priority}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
