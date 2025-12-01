"use client"

import { useState } from "react"
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

  // const handleScan = async () => {
  //   if (!url) {
  //     setError("Please enter a target URL")
  //     return
  //   }

  //   setLoading(true)
  //   setError(null)
  //   setResults(null)

  //   try {
  //     const params = new URLSearchParams({
  //       target: url,
  //       mode,
  //       crawl: enableCrawl.toString(),
  //       use_llm: enableLLM.toString(),
  //       pdf: exportPDF.toString(),
  //     })

  //     const response = await fetch(`http://localhost:8000/scan/combined?${params}`)

  //     if (!response.ok) {
  //       throw new Error(`API Error: ${response.statusText}`)
  //     }

  //     // Check if response is PDF
  //     const contentType = response.headers.get("content-type")
  //     if (contentType?.includes("application/pdf") && exportPDF) {
  //       const blob = await response.blob()
  //       const downloadUrl = window.URL.createObjectURL(blob)
  //       const link = document.createElement("a")
  //       link.href = downloadUrl
  //       link.download = "scan-report.pdf"
  //       document.body.appendChild(link)
  //       link.click()
  //       document.body.removeChild(link)
  //       window.URL.revokeObjectURL(downloadUrl)
  //     } else {
  //       const data = await response.json()
  //       setResults(data)
  //     }
  //   } catch (err: any) {
  //     setError(err.message || "Failed to run scan. Is the backend running on localhost:8000?")
  //   } finally {
  //     setLoading(false)
  //   }
  // }
  const handleScan = async () => {
  const trimmed = url.trim()
  if (!trimmed) {
    setError("Please enter a valid target URL")
    return
  }

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

    if (exportPDF && contentType?.includes("application/pdf")) {
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = "scan-report.pdf"
      a.click()
      window.URL.revokeObjectURL(url)
      return
    }

    const data = await response.json()
    setResults(data)
  } catch (err: any) {
    setError(err.message || "Could not reach backend.")
  } finally {
    setLoading(false)
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

          {/* Results */}
          {results && !loading && (
            <div className="space-y-6">
              <h2 className="text-2xl font-bold font-mono">Scan Results</h2>
              <ResultViewer data={results} onDownloadPdf={exportPDF ? handleDownloadPdf : undefined} />
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
