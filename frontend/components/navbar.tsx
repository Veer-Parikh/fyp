"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"

export function Navbar() {
  const pathname = usePathname()

  const isActive = (path: string) => {
    return pathname === path ? "text-accent font-semibold glow-text" : "text-muted-foreground hover:text-foreground"
  }

  return (
    <nav className="sticky top-0 z-50 border-b border-border/50 backdrop-blur-md bg-background/80">
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 group">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent to-secondary flex items-center justify-center text-foreground font-bold text-sm group-hover:shadow-lg group-hover:shadow-accent/50 transition-all duration-300">
              IDS
            </div>
            <span className="font-mono font-bold text-foreground hidden sm:inline cyber-gradient-text">XAI Suite</span>
          </Link>

          {/* Navigation Links */}
          <div className="flex items-center gap-8">
            <Link href="/" className={cn("font-mono text-sm transition-all duration-300", isActive("/"))}>
              Home
            </Link>
            <Link href="/ids" className={cn("font-mono text-sm transition-all duration-300", isActive("/ids"))}>
              IDS
            </Link>
            <Link
              href="/security"
              className={cn("font-mono text-sm transition-all duration-300", isActive("/security"))}
            >
              Security
            </Link>
          </div>

          {/* Status indicator */}
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-accent animate-pulse"></div>
            <span className="font-mono text-xs text-muted-foreground">ONLINE</span>
          </div>
        </div>
      </div>
    </nav>
  )
}
