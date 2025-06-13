"use client"

import { useState, useEffect } from "react"
import { usePathname } from "next/navigation"
import { DashboardSidebar } from "@/components/dashboard/sidebar"
import { ConnectWalletButton } from "@/components/ui/connect-wallet-button"
import { WalletProtection } from "@/components/wallet/WalletProtection"
import { cn } from "@/lib/utils"

export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [mounted, setMounted] = useState(false)
  const pathname = usePathname()

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) return null

  // Get page name from pathname
  const getPageName = () => {
    if (pathname === "/dashboard") return "Dashboard / Home"
    const segments = pathname.split("/")
    const pageName = segments[segments.length - 1]
    return `Dashboard / ${pageName.charAt(0).toUpperCase() + pageName.slice(1).replace(/-/g, " ")}`
  }

  return (
    <WalletProtection>
      <div className="relative min-h-screen bg-background overflow-hidden">
        {/* Enhanced background with subtle elegant effects */}
        <div
          aria-hidden
          className="z-[1] fixed inset-0 pointer-events-none isolate opacity-5">
          <div className="w-[35rem] h-[80rem] -translate-y-[350px] absolute left-0 top-0 -rotate-45 rounded-full bg-[radial-gradient(68.54%_68.72%_at_55.02%_31.46%,hsla(0,0%,100%,.08)_0,hsla(0,0%,100%,.02)_50%,hsla(0,0%,100%,0)_80%)]" />
          <div className="h-[80rem] absolute right-0 top-0 w-56 rotate-45 rounded-full bg-[radial-gradient(50%_50%_at_50%_50%,hsla(0,0%,100%,.06)_0,hsla(0,0%,100%,.02)_80%,transparent_100%)] [translate:5%_-50%]" />
        </div>
        
        {/* Refined grid background */}
        <div className="absolute inset-0 -z-10 h-full w-full bg-[linear-gradient(to_right,#ffffff05_1px,transparent_1px),linear-gradient(to_bottom,#ffffff05_1px,transparent_1px)] bg-[size:32px_32px]"></div>
        
        {/* Main layout with improved transitions */}
        <div className="flex">
          <DashboardSidebar open={sidebarOpen} setOpen={setSidebarOpen} />
          
          <div className={cn(
            "flex-1 transition-all duration-300 min-h-screen",
            sidebarOpen ? "ml-64" : "ml-16"
          )}>
            <div className="sticky top-0 z-10 backdrop-blur-sm bg-black/30 border-b border-white/10 py-3 px-6">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-medium text-white/90">{getPageName()}</h2>
                <ConnectWalletButton />
              </div>
            </div>
            
            <main className="py-10 px-12 max-w-[1400px] mx-auto">
              {children}
            </main>
          </div>
        </div>

        {/* Enhanced bottom gradient */}
        <div className="fixed bottom-0 left-0 right-0 h-20 bg-gradient-to-t from-background to-transparent pointer-events-none"></div>
      </div>
    </WalletProtection>
  )
}
