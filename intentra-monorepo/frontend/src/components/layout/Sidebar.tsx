"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { FiCommand, FiBriefcase, FiClock, FiSettings, FiX } from "react-icons/fi";

interface SidebarProps {
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
}

export function Sidebar({ isOpen, setIsOpen }: SidebarProps) {
  const pathname = usePathname();

  const navLinks = [
    { name: "Seeker Studio", href: "/dashboard/consumer", icon: FiCommand },
    { name: "Provider Hub", href: "/dashboard/provider", icon: FiBriefcase },
    { name: "History", href: "/dashboard/history", icon: FiClock },
  ];

  const bottomLinks = [
    { name: "User Profile", href: "/profile", icon: FiSettings },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 md:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}

      <aside className={`w-64 fixed top-0 left-0 bottom-0 bg-background border-r border-white/5 flex flex-col z-50 transition-transform duration-300 ${isOpen ? "translate-x-0" : "-translate-x-full"} md:translate-x-0`}>
        {/* Brand */}
        <div className="h-16 flex items-center justify-between px-6 border-b border-white/5">
          <Link href="/" className="flex items-center gap-2.5 group" onClick={() => setIsOpen(false)}>
            <div className="w-7 h-7 rounded-md bg-white text-black font-display font-extrabold flex items-center justify-center text-sm shadow-sm group-hover:scale-105 transition-transform">
              I
            </div>
            <span className="text-lg font-display font-bold tracking-tight text-foreground">Intentra</span>
          </Link>
          <button 
            className="md:hidden p-2 text-text-muted hover:text-foreground hover:bg-white/5 rounded-md"
            onClick={() => setIsOpen(false)}
          >
            <FiX className="w-5 h-5" />
          </button>
        </div>

        {/* Main Nav */}
        <nav className="flex-1 px-3 py-6 space-y-1 overflow-y-auto">
          <div className="px-3 mb-2 text-[10px] uppercase tracking-widest text-text-muted font-semibold font-mono">
            Operations
          </div>
          {navLinks.map((link) => {
            const isActive = pathname === link.href;
            const Icon = link.icon;
            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setIsOpen(false)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-sm font-mono ${
                  isActive
                    ? "bg-white/10 text-foreground font-medium shadow-sm border border-white/5"
                    : "text-text-muted hover:text-foreground hover:bg-white/5"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-primary" : ""}`} />
                {link.name}
              </Link>
            );
          })}
        </nav>

        {/* Bottom Nav */}
        <div className="p-3 border-t border-white/5">
          {bottomLinks.map((link) => {
            const isActive = pathname === link.href;
            const Icon = link.icon;
            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setIsOpen(false)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-sm font-mono ${
                  isActive
                    ? "bg-white/10 text-foreground font-medium border border-white/5"
                    : "text-text-muted hover:text-foreground hover:bg-white/5"
                }`}
              >
                <Icon className="w-4 h-4" />
                {link.name}
              </Link>
            );
          })}
        </div>
      </aside>
    </>
  );
}
