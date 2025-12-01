"use client"

import { useState } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { AlertCircle, CheckCircle2, Download } from "lucide-react"

interface ResultViewerProps {
  data: any
  onDownloadPdf?: () => void
}

export function ResultViewer({ data, onDownloadPdf }: ResultViewerProps) {
  const [copied, setCopied] = useState(false)

  const getRiskLevel = (score: number) => {
    if (score >= 80) return { label: "CRITICAL", color: "text-red-400", bg: "bg-red-400/10" }
    if (score >= 60) return { label: "HIGH", color: "text-orange-400", bg: "bg-orange-400/10" }
    if (score >= 40) return { label: "MEDIUM", color: "text-yellow-400", bg: "bg-yellow-400/10" }
    if (score >= 20) return { label: "LOW", color: "text-blue-400", bg: "bg-blue-400/10" }
    return { label: "INFO", color: "text-green-400", bg: "bg-green-400/10" }
  }

  const riskScore = data?.risk_score || 0
  const risk = getRiskLevel(riskScore)

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="space-y-6">
      {/* Risk Score Badge */}
      <div className={`${risk.bg} border border-accent/30 rounded-xl p-6 glow-border`}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-mono text-muted-foreground mb-2">OVERALL RISK SCORE</p>
            <div className="flex items-baseline gap-3">
              <span className={`text-5xl font-bold font-mono ${risk.color}`}>{Math.round(riskScore)}</span>
              <span className={`text-lg font-mono ${risk.color}`}>/100</span>
            </div>
          </div>
          <div className={`text-6xl font-mono ${risk.color} opacity-20`}>{Math.round(riskScore)}%</div>
        </div>
      </div>

      {/* Results Tabs */}
      <Tabs defaultValue="nmap" className="w-full">
        <TabsList className="grid w-full grid-cols-4 bg-card border border-border/50">
          <TabsTrigger value="nmap" className="font-mono text-xs">
            Nmap
          </TabsTrigger>
          <TabsTrigger value="zap" className="font-mono text-xs">
            ZAP
          </TabsTrigger>
          <TabsTrigger value="crawler" className="font-mono text-xs">
            Crawler
          </TabsTrigger>
          <TabsTrigger value="raw" className="font-mono text-xs">
            Raw
          </TabsTrigger>
        </TabsList>

        {/* Nmap Results */}
        <TabsContent value="nmap" className="space-y-4">
          <Card className="bg-card/50 border-accent/20 glow-border">
            <CardHeader>
              <CardTitle className="font-mono text-sm flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-accent" />
                Port Scan Results
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {data?.nmap?.ports && data.nmap.ports.length > 0 ? (
                <div className="space-y-2">
                  {data.nmap.ports.map((port: any, idx: number) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-2 rounded bg-background/50 border border-border/30"
                    >
                      <span className="font-mono text-xs">Port {port.port}</span>
                      <span
                        className={`font-mono text-xs px-2 py-1 rounded ${port.state === "open" ? "bg-red-400/20 text-red-400" : "bg-green-400/20 text-green-400"}`}
                      >
                        {port.state?.toUpperCase()}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">No port data available</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ZAP Results */}
        <TabsContent value="zap" className="space-y-4">
          <Card className="bg-card/50 border-accent/20 glow-border">
            <CardHeader>
              <CardTitle className="font-mono text-sm flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-orange-400" />
                Security Findings
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {data?.zap?.alerts && data.zap.alerts.length > 0 ? (
                <div className="space-y-2">
                  {data.zap.alerts.map((alert: any, idx: number) => (
                    <div key={idx} className="p-3 rounded bg-background/50 border border-border/30">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-mono text-xs font-semibold">{alert.name}</span>
                        <span
                          className={`font-mono text-xs px-2 py-1 rounded ${alert.riskcode >= 3 ? "bg-red-400/20 text-red-400" : "bg-yellow-400/20 text-yellow-400"}`}
                        >
                          Risk: {alert.riskcode}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground line-clamp-2">{alert.description}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">No vulnerabilities detected</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Crawler Results */}
        <TabsContent value="crawler" className="space-y-4">
          <Card className="bg-card/50 border-accent/20 glow-border">
            <CardHeader>
              <CardTitle className="font-mono text-sm flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-secondary" />
                Web Crawler Findings
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {data?.crawler?.urls && data.crawler.urls.length > 0 ? (
                <div className="space-y-2">
                  <p className="text-xs text-muted-foreground mb-3">Found {data.crawler.urls.length} URLs</p>
                  {data.crawler.urls.slice(0, 10).map((url: string, idx: number) => (
                    <div key={idx} className="p-2 rounded bg-background/50 border border-border/30">
                      <span className="font-mono text-xs text-accent truncate block">{url}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">No URLs discovered</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Raw JSON */}
        <TabsContent value="raw" className="space-y-4">
          <Card className="bg-card/50 border-accent/20">
            <CardHeader>
              <CardTitle className="font-mono text-sm">Raw JSON Response</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="bg-background/50 rounded border border-border/30 p-4 max-h-96 overflow-auto terminal-box">
                <pre className="font-mono text-xs text-accent/80 whitespace-pre-wrap break-words">
                  {JSON.stringify(data, null, 2)}
                </pre>
              </div>
              <button
                onClick={() => copyToClipboard(JSON.stringify(data, null, 2))}
                className="mt-3 px-3 py-1 text-xs font-mono bg-accent/20 hover:bg-accent/40 text-accent rounded border border-accent/50 transition-colors"
              >
                {copied ? "Copied!" : "Copy JSON"}
              </button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Download PDF Button */}
      {onDownloadPdf && (
        <button
          onClick={onDownloadPdf}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 font-mono text-sm bg-primary/20 hover:bg-primary/40 text-primary border border-primary/50 rounded transition-all"
        >
          <Download className="w-4 h-4" />
          Download PDF Report
        </button>
      )}
    </div>
  )
}
