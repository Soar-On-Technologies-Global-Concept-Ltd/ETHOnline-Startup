import React from "react";
import { Navbar } from "./Navbar";
import { Footer } from "./Footer";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <Navbar />
      <div className="flex-1 pt-16">
        {children}
      </div>
      <Footer />
    </div>
  );
}
