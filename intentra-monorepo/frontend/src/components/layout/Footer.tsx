import React from "react";

export function Footer() {
  return (
    <footer className="border-t border-white/10 bg-black/60 py-8 px-6 mt-20 text-xs font-mono text-text-muted">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="font-display font-bold text-foreground">Intentra Protocol</span>
          <span>• ETHOnline 2026</span>
        </div>

        <div className="flex flex-wrap justify-center gap-6">
          <span>Settlement: Arc USDC</span>
          <span>Auth: Privy</span>
          <span>Identity: World ID</span>
          <span>Indexer: The Graph</span>
        </div>

        <div>
          <span>AI Prepares. Humans Authorize.</span>
        </div>
      </div>
    </footer>
  );
}
