"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { PrivyLoginButton } from "@/components/auth/PrivyLoginButton";
import { Menu, X, ArrowUpRight } from "lucide-react";

export function Navbar() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { name: "Seeker Studio", href: "/dashboard/consumer" },
    { name: "Provider Hub", href: "/dashboard/provider" },
    { name: "History", href: "/dashboard/history" },
  ];

  return (
    <nav className="glass-nav px-6 py-3.5 fixed top-0 left-0 right-0 z-50 transition-all">
      <div className="max-w-7xl mx-auto flex justify-between items-center">
        {/* Brand Logo & Top Role Indicator */}
        <div className="flex items-center gap-4">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="w-7 h-7 rounded-md bg-white text-black font-display font-extrabold flex items-center justify-center text-sm shadow-sm group-hover:scale-105 transition-transform">
              I
            </div>
            <span className="text-lg font-display font-bold tracking-tight text-foreground">Intentra</span>
          </Link>

          {/* Nav Links (Desktop) */}
          <div className="hidden md:flex items-center gap-1 pl-4 border-l border-white/10 text-xs font-mono">
            {navLinks.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`px-3 py-1.5 rounded-md transition-all ${
                    isActive
                      ? "bg-white/10 text-foreground font-semibold border border-white/10"
                      : "text-text-muted hover:text-foreground hover:bg-white/5"
                  }`}
                >
                  {link.name}
                </Link>
              );
            })}
          </div>
        </div>

        {/* Right Auth & Profile Controls */}
        <div className="hidden md:flex items-center gap-3">
          <Link
            href="/profile"
            className="text-xs font-mono text-text-muted hover:text-foreground px-2.5 py-1 rounded-md border border-white/10 hover:border-white/20 transition-all"
          >
            Profile
          </Link>
          <PrivyLoginButton variant="glass" />
        </div>

        {/* Mobile Hamburger Toggle */}
        <div className="flex md:hidden items-center gap-2">
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-md bg-white/5 text-foreground border border-white/10"
          >
            {mobileMenuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden pt-4 pb-3 border-t border-white/10 mt-3 space-y-2">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              onClick={() => setMobileMenuOpen(false)}
              className="block px-3 py-2 rounded-md text-sm font-mono text-text-muted hover:text-foreground hover:bg-white/5"
            >
              {link.name}
            </Link>
          ))}
          <Link
            href="/profile"
            onClick={() => setMobileMenuOpen(false)}
            className="block px-3 py-2 rounded-md text-sm font-mono text-text-muted hover:text-foreground hover:bg-white/5"
          >
            User Profile
          </Link>
          <div className="pt-2">
            <PrivyLoginButton variant="glass" />
          </div>
        </div>
      )}
    </nav>
  );
}
