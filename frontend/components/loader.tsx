"use client"

import { useState, useEffect } from "react"

const SCAN_PHASES = [
  "Initializing reconnaissance...",
  "Running Nmap port scan...",
  "Launching OWASP ZAP auditor...",
  "Executing web crawler...",
  "Analyzing findings...",
  "Generating XAI explanations...",
]

export function Loader() {
  const [currentPhase, setCurrentPhase] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentPhase((prev) => (prev + 1) % SCAN_PHASES.length)
    }, 1500)

    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex flex-col items-center justify-center gap-6 py-12">
      {/* Animated grid background */}
      <div className="relative w-24 h-24">
        <div
          className="absolute inset-0 border-2 border-accent/30 rounded-lg animate-spin"
          style={{ animationDuration: "4s" }}
        ></div>
        <div
          className="absolute inset-2 border-2 border-secondary/30 rounded-lg animate-spin"
          style={{ animationDuration: "3s", animationDirection: "reverse" }}
        ></div>
        <div
          className="absolute inset-4 border-2 border-primary/30 rounded-lg animate-spin"
          style={{ animationDuration: "2s" }}
        ></div>

        {/* Center dot */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-3 h-3 rounded-full bg-accent glow-text animate-pulse"></div>
        </div>
      </div>

      {/* Scan phase text with animation */}
      <div className="text-center">
        <div className="font-mono text-sm h-6 min-h-6">
          <span className="text-accent glow-text animate-pulse">
            {"> "}
            {SCAN_PHASES[currentPhase]}
          </span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="w-48 h-1 bg-border rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-accent via-secondary to-primary rounded-full"
          style={{
            animation: "data-flow 2s linear infinite",
            width: "30%",
          }}
        ></div>
      </div>

      {/* Status text */}
      <p className="text-xs text-muted-foreground font-mono">Security analysis in progress...</p>
    </div>
  )
}
