"use client"

import { useState, useRef } from "react"
import { Navbar } from "@/components/navbar"
import { Loader } from "@/components/loader"
import { ResultViewer } from "@/components/result-viewer"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Play } from "lucide-react"

type ScanMode = "fast" | "deep" | "extreme"

export default function SecurityPage() {
  const [url, setUrl] = useState("")
  const [mode, setMode] = useState<ScanMode>("deep")
  const [enableCrawl, setEnableCrawl] = useState(true)
  const [enableLLM, setEnableLLM] = useState(true)
  const [exportPDF, setExportPDF] = useState(false)
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  // Prevent double-clicking
  const isScanning = useRef(false)

  const handleScan = async () => {
    const trimmed = url.trim()
    if (!trimmed) {
      setError("Please enter a valid target URL")
      return
    }

    // Prevent duplicate calls
    if (isScanning.current) {
      console.log("Scan already in progress, ignoring duplicate call")
      return
    }

    isScanning.current = true
    setLoading(true)
    setError(null)
    setResults(null)

    try {
      const params = new URLSearchParams({
        target: trimmed,
        mode,
        crawl: enableCrawl ? "true" : "false",
        use_llm: enableLLM ? "true" : "false",
        pdf: exportPDF ? "true" : "false",
      })

      const response = await fetch(
        `http://localhost:8000/scan/combined?${params.toString()}`,
        {
          method: "GET",
          mode: "cors",
        }
      )

      if (!response.ok) throw new Error(`API Error ${response.status}`)

      const contentType = response.headers.get("content-type")

      if (exportPDF) {
        const data = await response.json()

        // Save JSON results
        if (data.result) {
          setResults({ result: data.result })
        } else {
          setError("Scan JSON missing from server response.")
        }

        // Handle PDF base64 download
        if (data.pdf_base64) {
          try {
            const pdfBlob = await fetch(`data:application/pdf;base64,${data.pdf_base64}`).then(r => r.blob())
            const url = URL.createObjectURL(pdfBlob)
            const a = document.createElement("a")
            a.href = url
            a.download = "scan-report.pdf"
            a.click()
          } catch (e) {
            console.warn("PDF base64 decode failed:", e)
            setError("Could not download PDF.")
          }
        } else {
          setError("PDF data missing from server response.")
        }

        return
      }


      // Non-PDF path: plain JSON
      const data = await response.json()
      setResults(data)
    } catch (err: any) {
      setError(err.message || "Could not reach backend.")
    } finally {
      setLoading(false)
      isScanning.current = false
    }
  }

  const handleDownloadPdf = () => {
    if (results) {
      handleScan()
    }
  }

  return (
    <>
      <Navbar />
      <main className="min-h-screen bg-background">
        {/* Background grid */}
        <div className="fixed inset-0 opacity-5 pointer-events-none">
          <div
            className="absolute inset-0"
            style={{
              backgroundImage:
                "linear-gradient(0deg, rgba(0,255,150,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(0,255,150,0.1) 1px, transparent 1px)",
              backgroundSize: "50px 50px",
            }}
          ></div>
        </div>

        <section className="relative max-w-7xl mx-auto px-6 py-12">
          {/* Header */}
          <div className="mb-12">
            <h1 className="text-4xl md:text-5xl font-bold font-mono mb-4">
              <span className="cyber-gradient-text">Security</span>
              <br />
              Scanner
            </h1>
            <p className="text-muted-foreground">
              Run comprehensive security scans combining Nmap, OWASP ZAP, and web crawling
            </p>
          </div>

          {/* Main Scanning Card */}
          <Card className="mb-12 bg-card/50 border-accent/20 glow-border">
            <CardHeader>
              <CardTitle className="font-mono">Scan Configuration</CardTitle>
              <CardDescription>Enter target URL and configure scan parameters</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* URL Input */}
              <div className="space-y-2">
                <label className="block text-sm font-mono text-foreground">Target URL</label>
                <input
                  type="text"
                  placeholder="https://example.com"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  className="w-full px-4 py-3 rounded-lg bg-background/50 border border-border/50 focus:border-accent/50 text-foreground placeholder-muted-foreground focus:outline-none transition-colors font-mono text-sm"
                  disabled={loading}
                />
              </div>

              {/* Mode Selection */}
              <div className="space-y-2">
                <label className="block text-sm font-mono text-foreground">Scan Mode</label>
                <div className="grid grid-cols-3 gap-3">
                  {(["fast", "deep", "extreme"] as const).map((m) => (
                    <button
                      key={m}
                      onClick={() => setMode(m)}
                      disabled={loading}
                      className={`px-4 py-2 rounded font-mono text-sm transition-all ${
                        mode === m
                          ? "bg-accent/30 border border-accent text-accent"
                          : "bg-background/50 border border-border/50 text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      {m.charAt(0).toUpperCase() + m.slice(1)}
                    </button>
                  ))}
                </div>
              </div>

              {/* Toggles */}
              <div className="space-y-3">
                <label className="flex items-center gap-3 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={enableCrawl}
                    onChange={(e) => setEnableCrawl(e.target.checked)}
                    disabled={loading}
                    className="w-4 h-4 rounded border-accent/50 accent-accent"
                  />
                  <span className="text-sm font-mono text-foreground group-hover:text-accent transition-colors">
                    Enable Web Crawler
                  </span>
                </label>
                <label className="flex items-center gap-3 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={enableLLM}
                    onChange={(e) => setEnableLLM(e.target.checked)}
                    disabled={loading}
                    className="w-4 h-4 rounded border-accent/50 accent-accent"
                  />
                  <span className="text-sm font-mono text-foreground group-hover:text-accent transition-colors">
                    Enable LLM Analysis
                  </span>
                </label>
                <label className="flex items-center gap-3 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={exportPDF}
                    onChange={(e) => setExportPDF(e.target.checked)}
                    disabled={loading}
                    className="w-4 h-4 rounded border-accent/50 accent-accent"
                  />
                  <span className="text-sm font-mono text-foreground group-hover:text-accent transition-colors">
                    Export PDF Report
                  </span>
                </label>
              </div>

              {/* Error Message */}
              {error && (
                <div className="p-4 rounded-lg bg-red-400/10 border border-red-400/30">
                  <p className="text-sm text-red-400 font-mono">{error}</p>
                </div>
              )}

              {/* Scan Button */}
              <button
                onClick={handleScan}
                disabled={loading || !url}
                className="w-full cyber-button flex items-center justify-center gap-2 px-6 py-3 bg-accent/20 hover:bg-accent/40 text-accent border border-accent/50 rounded-lg font-mono font-semibold transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Play className="w-4 h-4" />
                {loading ? "Scanning..." : "Start Scan"}
              </button>
            </CardContent>
          </Card>

          {/* Loading State */}
          {loading && (
            <div className="mb-12">
              <Card className="bg-card/50 border-accent/20">
                <CardContent className="py-12">
                  <Loader />
                </CardContent>
              </Card>
            </div>
          )}

          {results && !loading && (
            <div className="space-y-10 mt-10">
              <h2 className="text-3xl font-bold font-mono">Scan Results</h2>

              {/* Target Summary */}
              <Card className="border-accent/30 bg-card/50">
                <CardHeader>
                  <CardTitle className="font-mono">Target Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="font-mono text-sm"><b>Target:</b> {results.result.target}</p>
                  <p className="font-mono text-sm"><b>Scan Mode:</b> {results.result.scan_mode}</p>
                  <p className="font-mono text-sm"><b>Risk Score:</b> {results.result.risk_score}</p>
                  <p className="font-mono text-sm"><b>LLM Used:</b> {results.result.llm_used ? "Yes" : "No"}</p>
                </CardContent>
              </Card>

              {/* NMAP Section */}
              <Card className="border-border bg-card/30">
                <CardHeader>
                  <CardTitle className="font-mono">NMAP Results</CardTitle>
                  <CardDescription>Detected open ports, services, and versions</CardDescription>
                </CardHeader>
                <CardContent>
                  {results.result.nmap.ports.length === 0 ? (
                    <p className="text-muted-foreground font-mono">No open ports detected.</p>
                  ) : (
                    <ul className="font-mono text-sm space-y-2">
                      {results.result.nmap.ports.map((p: any, i: number) => (
                        <li key={i} className="border border-border rounded p-2">
                          <b>Port:</b> {p.port} — {p.state} ({p.service})
                        </li>
                      ))}
                    </ul>
                  )}
                </CardContent>
              </Card>

              {/* ZAP Alerts */}
              <Card className="border-red-400/40 bg-card/30">
                <CardHeader>
                  <CardTitle className="font-mono">ZAP Alerts (Grouped by Severity)</CardTitle>
                </CardHeader>

                <CardContent className="space-y-4">
                  {["High", "Medium", "Low", "Informational"].map((sev) => {
                    const filtered = results.result.zap.alerts.filter(
                      (a: any) => a.risk.toLowerCase() === sev.toLowerCase()
                    )

                    return (
                      <details key={sev} className="border border-border rounded p-3">
                        <summary className="font-mono cursor-pointer">
                          {sev} ({filtered.length})
                        </summary>

                        <ul className="mt-3 space-y-2 font-mono text-sm">
                          {filtered.map((a: any, i: number) => (
                            <li key={i} className="p-2 border border-border rounded">
                              <b>{a.alert}</b>
                              <br />
                              <span className="text-muted-foreground">{a.url}</span>
                            </li>
                          ))}
                        </ul>
                      </details>
                    )
                  })}
                </CardContent>
              </Card>

              {/* Crawler Summary */}
              <Card className="border-blue-400/30 bg-card/30">
                <CardHeader>
                  <CardTitle className="font-mono">Crawler Findings</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="font-mono text-sm mb-4">
                    Pages crawled: {results.result.crawler.pages.length}
                  </p>

                  <ul className="font-mono text-sm space-y-2">
                    {results.result.crawler.pages.slice(0, 10).map((p: any, i: number) => (
                      <li key={i} className="border border-border rounded p-2">{p.url}</li>
                    ))}
                  </ul>
                </CardContent>
              </Card>

              {/* AI Summary Section */}
              {results.result.ai && !results.result.ai.error && (
                <Card className="border-purple-400/40 bg-card/30">
                  <CardHeader>
                    <CardTitle className="font-mono">AI Security Summary</CardTitle>
                    <CardDescription>Gemini XAI Security Report</CardDescription>
                  </CardHeader>

                  <CardContent className="space-y-6 font-mono text-sm">
                    <section>
                      <h3 className="font-bold text-lg mb-2">Executive Summary</h3>
                      <p>{results.result.ai.executive_summary}</p>
                    </section>

                    <section>
                      <h3 className="font-bold text-lg mb-2">Technical Analysis</h3>
                      <p>{results.result.ai.technical_analysis}</p>
                    </section>

                    <section>
                      <h3 className="font-bold text-lg mb-2">Conclusion</h3>
                      <p>{results.result.ai.conclusion}</p>
                    </section>

                    <section>
                      <h3 className="font-bold text-lg mb-2">Remediation Checklist</h3>
                      <ul className="list-disc ml-6">
                        {results.result.ai.remediation.map((r: string, i: number) => (
                          <li key={i}>{r}</li>
                        ))}
                      </ul>
                    </section>
                  </CardContent>
                </Card>
              )}

              {/* AI Error Display */}
              {results.result.ai && results.result.ai.error && (
                <Card className="border-yellow-400/40 bg-card/30">
                  <CardHeader>
                    <CardTitle className="font-mono text-yellow-400">AI Analysis Unavailable</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="font-mono text-sm text-muted-foreground">
                      {results.result.ai.error === "exception" 
                        ? results.result.ai.message.includes("429") 
                          ? "Rate limit exceeded. Please wait a moment and try again, or disable LLM analysis."
                          : `Error: ${results.result.ai.message}`
                        : `Error: ${results.result.ai.error}`}
                    </p>
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          {/* Placeholder */}
          {!loading && !results && !error && (
            <Card className="bg-card/50 border-border/50">
              <CardContent className="py-12 text-center">
                <p className="text-muted-foreground font-mono">
                  Enter a target URL and click "Start Scan" to begin security analysis
                </p>
              </CardContent>
            </Card>
          )}
        </section>
      </main>
    </>
  )
}
