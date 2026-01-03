"use client"

import React, { useState, useRef, useEffect } from "react"
import { Send, Bot, User, X, ShieldAlert, Sparkles, Trash2, Terminal } from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

export function ChatbotSidebar({ isOpen, onClose }: { isOpen: boolean, onClose: () => void }) {
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState<{ role: "user" | "bot"; text: string }[]>([
    { role: "bot", text: "System Online. **OWASP Sentinel** active.\n\nReady to analyze vulnerabilities and provide remediation protocols.\n\nAwaiting input..." }
  ])
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isLoading, isOpen])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return
    
    const userMsg = input
    setMessages(prev => [...prev, { role: "user", text: userMsg }])
    setInput("")
    setIsLoading(true)

    try {
      const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMsg }),
      })
      
      const data = await response.json()
      const cleanText = data.response.replace(/\u001b\[[0-9;]*m/g, '')
      setMessages(prev => [...prev, { role: "bot", text: cleanText }])
    } catch (error) {
      setMessages(prev => [...prev, { role: "bot", text: "⚠️ **Network Failure**: Unable to connect to Security Engine." }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleClearChat = () => {
    setMessages([{ role: "bot", text: "Logs cleared. Awaiting new query..." }])
  }

  return (
    // UPDATED BACKGROUND: Reverted to bg-background/95 + backdrop-blur to match your previous screenshot
    <div className={`fixed top-0 right-0 h-full w-full sm:w-[600px] bg-background/95 backdrop-blur-xl border-l border-accent/20 transition-transform duration-300 z-50 ${isOpen ? "translate-x-0" : "translate-x-full"} shadow-2xl shadow-accent/5 flex flex-col`}>
      
      {/* Header */}
      <div className="p-4 border-b border-accent/10 flex items-center justify-between bg-accent/5 shrink-0">
        <div className="flex items-center gap-3 text-accent">
          <div className="relative flex items-center justify-center w-8 h-8 rounded bg-accent/10 border border-accent/30">
            <ShieldAlert className="w-5 h-5" />
            <div className="absolute top-0 right-0 w-1.5 h-1.5 bg-accent rounded-full animate-pulse shadow-[0_0_10px_rgba(0,255,150,0.8)]" />
          </div>
          <div>
            <span className="font-mono font-bold text-sm tracking-wider block text-foreground">OWASP SENTINEL</span>
            <div className="flex items-center gap-1.5">
              <span className="w-1 h-1 bg-accent rounded-full" />
              <span className="text-[10px] text-accent/80 font-mono uppercase tracking-widest">v2.0 ONLINE</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button 
            onClick={handleClearChat} 
            className="p-2 hover:bg-destructive/10 hover:text-destructive rounded transition-colors text-muted-foreground" 
            title="Purge Logs"
          >
            <Trash2 className="w-4 h-4" />
          </button>
          <button onClick={onClose} className="p-2 hover:bg-accent/10 rounded transition-colors text-muted-foreground hover:text-accent">
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Messages Area - NEW SCROLLBAR THEME ADDED */}
      <div className="
        flex-1 overflow-y-auto min-h-0 p-6 space-y-6 scroll-smooth 
        scrollbar-thin scrollbar-thumb-accent/20 scrollbar-track-transparent hover:scrollbar-thumb-accent/40
        [&::-webkit-scrollbar]:w-1.5
        [&::-webkit-scrollbar-track]:bg-transparent
        [&::-webkit-scrollbar-thumb]:bg-accent/20
        [&::-webkit-scrollbar-thumb]:rounded-full
        [&::-webkit-scrollbar-thumb]:hover:bg-accent/40
      ">
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-4 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
            
            {/* Avatar */}
            <div className={`w-8 h-8 rounded flex items-center justify-center shrink-0 border ${msg.role === "bot" ? "bg-accent/5 border-accent/30 text-accent" : "bg-primary/10 border-primary/30 text-primary"}`}>
              {msg.role === "bot" ? <Terminal size={16} /> : <User size={16} />}
            </div>

            {/* Message Bubble */}
            <div className={`relative px-5 py-4 rounded-lg text-sm leading-relaxed max-w-[90%] font-mono shadow-md ${
              msg.role === "bot" 
                ? "bg-card border border-accent/10 text-card-foreground" 
                : "bg-accent/10 border border-accent/20 text-white"
            }`}>
              {msg.role === "bot" ? (
                <div className="markdown-content">
                  <ReactMarkdown 
                    remarkPlugins={[remarkGfm]}
                    components={{
                      p: ({children}) => <p className="mb-3 last:mb-0">{children}</p>,
                      strong: ({children}) => <span className="font-bold text-accent glow-text-sm">{children}</span>,
                      ul: ({children}) => <ul className="list-none pl-0 mb-3 space-y-2">{children}</ul>,
                      li: ({children}) => <li className="flex gap-2"><span className="text-accent shrink-0">›</span><span>{children}</span></li>,
                      code: ({children}) => <code className="bg-background/50 px-1.5 py-0.5 rounded text-xs text-accent border border-accent/20">{children}</code>,
                      pre: ({children}) => <pre className="bg-background/50 p-4 rounded-lg overflow-x-auto my-3 border border-accent/20 text-xs text-muted-foreground shadow-inner custom-scrollbar">{children}</pre>,
                      a: ({href, children}) => <a href={href} className="text-blue-400 hover:text-blue-300 hover:underline decoration-blue-400/30 underline-offset-4" target="_blank" rel="noopener noreferrer">{children}</a>,
                      blockquote: ({children}) => <blockquote className="border-l-2 border-accent/50 pl-4 py-1 italic text-muted-foreground my-2 bg-accent/5">{children}</blockquote>
                    }}
                  >
                    {msg.text}
                  </ReactMarkdown>
                </div>
              ) : (
                msg.text
              )}
            </div>
          </div>
        ))}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex gap-4 animate-pulse">
            <div className="w-8 h-8 rounded bg-accent/5 border border-accent/20 flex items-center justify-center shrink-0">
              <Sparkles size={16} className="text-accent" />
            </div>
            <div className="flex items-center gap-2 text-xs text-accent/70 font-mono mt-2">
              <span className="w-1.5 h-1.5 bg-accent rounded-full animate-bounce [animation-delay:-0.3s]"></span>
              <span className="w-1.5 h-1.5 bg-accent rounded-full animate-bounce [animation-delay:-0.15s]"></span>
              <span className="w-1.5 h-1.5 bg-accent rounded-full animate-bounce"></span>
              <span className="ml-2 uppercase tracking-wider">Processing Neural Query...</span>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 bg-background/50 border-t border-accent/10 shrink-0 backdrop-blur-sm">
        <div className="relative group">
          <input 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Execute command or query vulnerability..."
            className="w-full bg-background/50 border border-accent/20 rounded-lg pl-4 pr-12 py-3.5 text-sm font-mono text-foreground focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-all placeholder:text-muted-foreground/40"
            autoFocus
          />
          <button 
            onClick={handleSend} 
            disabled={isLoading || !input.trim()}
            className="absolute right-2 top-2 p-1.5 bg-accent/10 text-accent border border-accent/20 rounded hover:bg-accent/20 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
          >
            <Send size={16} />
          </button>
        </div>
        <div className="flex justify-between items-center mt-2 px-1">
          <div className="text-[10px] text-accent/40 font-mono flex gap-2">
            <span>RAG: ENABLED</span>
            <span>•</span>
            <span>MODEL: GEMINI-1.5</span>
          </div>
          <div className="text-[10px] text-muted-foreground/30 font-mono">
            SECURE CONNECTION ESTABLISHED
          </div>
        </div>
      </div>
    </div>
  )
}