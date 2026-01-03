"use client"

import React, { useState } from "react"
import { Navbar } from "@/components/navbar"
import { ChatbotSidebar } from "@/components/chatbot-sidebar"

export function ClientLayout({ children }: { children: React.ReactNode }) {
  const [isChatOpen, setIsChatOpen] = useState(false)

  return (
    <>
      {/* Navbar with the toggle function */}
      <Navbar onChatToggle={() => setIsChatOpen((prev) => !prev)} />
      
      {/* Main Content */}
      <main className="relative min-h-screen">
        {children}
      </main>

      {/* Global Chatbot Sidebar */}
      <ChatbotSidebar 
        isOpen={isChatOpen} 
        onClose={() => setIsChatOpen(false)} 
      />
    </>
  )
}