"use client";

import React from "react";
import { usePathname } from "next/navigation";
import { PrivyLoginButton } from "@/components/auth/PrivyLoginButton";
import { FiSearch, FiBell } from "react-icons/fi";

export function Topbar() {
  const pathname = usePathname();

  // Simple Breadcrumbs logic
  const pathParts = pathname.split("/").filter(Boolean);
  const isDashboard = pathParts[0] === "dashboard";
  
  const getBreadcrumbTitle = () => {
    if (pathname === "/") return "Overview";
    if (pathname === "/profile") return "User Profile";
    if (isDashboard && pathParts[1] === "consumer") return "Seeker Studio";
    if (isDashboard && pathParts[1] === "provider") return "Provider Hub";
    if (isDashboard && pathParts[1] === "history") return "Transaction History";
    if (pathParts[0] === "intent") return `Intent Engine`;
    return pathParts.map(p => p.charAt(0).toUpperCase() + p.slice(1)).join(" / ");
  };

  return (
    <header className="h-16 border-b border-white/5 bg-background/80 backdrop-blur-md sticky top-0 z-40 flex items-center justify-between px-6">
      {/* Breadcrumbs */}
      <div className="flex items-center gap-2 text-sm font-mono text-text-muted">
        <span>Intentra</span>
        <span>/</span>
        <span className="text-foreground font-medium">{getBreadcrumbTitle()}</span>
      </div>

      {/* Right Actions */}
      <div className="flex items-center gap-4">
        <div className="hidden md:flex items-center gap-3">
          <button className="p-2 text-text-muted hover:text-foreground hover:bg-white/5 rounded-md transition-colors">
            <FiSearch className="w-4 h-4" />
          </button>
          <button className="p-2 text-text-muted hover:text-foreground hover:bg-white/5 rounded-md transition-colors">
            <FiBell className="w-4 h-4" />
          </button>
        </div>
        <div className="w-px h-6 bg-white/10 hidden md:block"></div>
        <PrivyLoginButton variant="glass" />
      </div>
    </header>
  );
}
