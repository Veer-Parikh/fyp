"use client"

import type React from "react"

import { Navbar } from "@/components/navbar"
import { ChevronRight, Zap, Shield, Brain, Globe } from "lucide-react"

export default function Home() {
  return (
    <>
      <Navbar />
      <main className="min-h-screen bg-background">
        {/* Animated background grid */}
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

        {/* Hero Section */}
        <section className="relative max-w-7xl mx-auto px-6 py-24">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            {/* Left Content */}
            <div className="space-y-6">
              <div>
                <h1 className="text-5xl md:text-6xl font-bold font-mono mb-4 leading-tight">
                  <span className="cyber-gradient-text">Intrusion</span>
                  <br />
                  Detection
                  <br />
                  <span className="cyber-gradient-text">System</span>
                </h1>
                <p className="text-lg text-accent glow-text font-semibold">with eXplainable AI & NLP</p>
              </div>

              <p className="text-muted-foreground text-sm leading-relaxed max-w-md">
                Enhanced with Nmap Port Scanning • OWASP ZAP Auditing • Custom Web Crawler • Risk Scoring Engine
              </p>

              {/* Feature List */}
              <div className="space-y-3 py-6">
                <FeatureItem
                  icon={<Zap className="w-5 h-5" />}
                  text="Real-time threat detection with XAI explanations"
                />
                <FeatureItem icon={<Shield className="w-5 h-5" />} text="OWASP ZAP security auditing integration" />
                <FeatureItem icon={<Globe className="w-5 h-5" />} text="Advanced web crawling & reconnaissance" />
                <FeatureItem icon={<Brain className="w-5 h-5" />} text="NLP-based attack classification" />
              </div>

              {/* CTA Button */}
              <div className="flex gap-4 pt-4">
                <a
                  href="/security"
                  className="cyber-button px-6 py-3 bg-accent/20 hover:bg-accent/40 text-accent border border-accent/50 rounded font-mono text-sm font-semibold transition-all duration-300 flex items-center gap-2 group"
                >
                  Start Scanning
                  <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </a>
              </div>
            </div>

            {/* Right Visualization */}
            <div className="relative h-96 hidden md:flex items-center justify-center">
              <div className="relative w-full h-full">
                {/* Animated tech visualization */}
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="relative w-64 h-64">
                    {/* Outer rotating ring */}
                    <div
                      className="absolute inset-0 border-2 border-accent/30 rounded-full animate-spin"
                      style={{ animationDuration: "8s" }}
                    >
                      <div className="absolute top-0 left-1/2 w-3 h-3 bg-accent rounded-full -translate-x-1/2 -translate-y-1/2"></div>
                    </div>

                    {/* Middle rotating ring */}
                    <div
                      className="absolute inset-8 border-2 border-secondary/30 rounded-full animate-spin"
                      style={{ animationDuration: "6s", animationDirection: "reverse" }}
                    >
                      <div className="absolute right-0 top-1/2 w-3 h-3 bg-secondary rounded-full translate-x-1/2 -translate-y-1/2"></div>
                    </div>

                    {/* Inner rotating ring */}
                    <div
                      className="absolute inset-16 border-2 border-primary/30 rounded-full animate-spin"
                      style={{ animationDuration: "4s" }}
                    >
                      <div className="absolute bottom-0 left-1/2 w-3 h-3 bg-primary rounded-full -translate-x-1/2 translate-y-1/2"></div>
                    </div>

                    {/* Center core */}
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="w-6 h-6 rounded-full bg-gradient-to-br from-accent to-secondary glow-text animate-pulse"></div>
                    </div>
                  </div>
                </div>

                {/* Floating security icons */}
                <div className="absolute top-10 left-10 text-accent/40 animate-pulse" style={{ animationDelay: "0s" }}>
                  <Shield className="w-12 h-12" />
                </div>
                <div
                  className="absolute bottom-10 right-10 text-secondary/40 animate-pulse"
                  style={{ animationDelay: "0.5s" }}
                >
                  <Zap className="w-12 h-12" />
                </div>
                <div
                  className="absolute top-1/2 right-10 text-primary/40 animate-pulse"
                  style={{ animationDelay: "1s" }}
                >
                  <Brain className="w-12 h-12" />
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Features Grid */}
        <section className="relative max-w-7xl mx-auto px-6 py-20">
          <h2 className="text-3xl font-bold font-mono mb-12">Capabilities</h2>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            <CapabilityCard title="Port Scanning" description="Nmap-powered network reconnaissance" icon="📡" />
            <CapabilityCard title="Vulnerability Detection" description="OWASP ZAP security auditing" icon="🔍" />
            <CapabilityCard title="Web Crawling" description="Deep site structure analysis" icon="🕷️" />
            <CapabilityCard title="Risk Scoring" description="ML-based threat assessment" icon="📊" />
          </div>
        </section>

        {/* Footer */}
        <footer className="border-t border-border/50 mt-20 py-8 text-center">
          <p className="text-xs text-muted-foreground font-mono">Made with ❤️ for Cybersecurity Research</p>
        </footer>
      </main>
    </>
  )
}

function FeatureItem({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div className="flex items-center gap-3">
      <div className="text-accent glow-text">{icon}</div>
      <span className="text-sm text-foreground">{text}</span>
    </div>
  )
}

function CapabilityCard({ title, description, icon }: { title: string; description: string; icon: string }) {
  return (
    <div className="group relative p-6 rounded-lg bg-card/50 border border-accent/20 hover:border-accent/50 transition-all duration-300 glow-border">
      <div className="text-3xl mb-3">{icon}</div>
      <h3 className="font-mono font-semibold text-foreground mb-2">{title}</h3>
      <p className="text-xs text-muted-foreground">{description}</p>
    </div>
  )
}
