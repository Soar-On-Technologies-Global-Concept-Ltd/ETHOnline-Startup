"use client";

import { PrimaryButton } from "@/components/ui/PrimaryButton";
import { SolidCard } from "@/components/ui/SolidCard";
import { QuoteCard } from "@/components/ui/QuoteCard";
import { FiArrowRight as ArrowRight, FiSearch as Search } from "react-icons/fi";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { usePrivy } from "@privy-io/react-auth";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { parseAndCreateIntent, Intent } from "@/lib/api";

export default function ConsumerDashboard() {
  const { ready, authenticated, getAccessToken } = usePrivy();
  const router = useRouter();

  const [prompt, setPrompt] = useState("Find a verified photographer for my event, max $150.");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [intent, setIntent] = useState<Intent | null>(null);

  useEffect(() => {
    if (ready && !authenticated) {
      router.push("/");
    }
  }, [ready, authenticated, router]);

  const handleAnalyzeIntent = async (inputPrompt: string) => {
    setIsAnalyzing(true);
    setIntent(null);

    try {
      const token = await getAccessToken();
      const result = await parseAndCreateIntent(inputPrompt, token || "");
      setIntent(result);
    } catch(err) {
      console.error(err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    async function initAnalysis() {
      setIsAnalyzing(true);
      try {
        const token = await getAccessToken();
        const result = await parseAndCreateIntent(prompt, token || "");
        if (!ignore) setIntent(result);
      } catch (err) {
        console.error(err);
      } finally {
        if (!ignore) setIsAnalyzing(false);
      }
    }
    initAnalysis();
    return () => {
      ignore = true;
    };
  }, [prompt, getAccessToken]);

  if (!ready || !authenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center text-text-muted font-mono text-xs bg-background">
        <div className="flex items-center gap-3 glass-panel px-5 py-3.5 rounded-md">
          <div className="w-3.5 h-3.5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
          <span>Authenticating Environment...</span>
        </div>
      </div>
    );
  }

  return (
    <main className="max-w-4xl mx-auto p-6 md:p-12 min-h-screen">
      {/* Header Bar */}
      <header className="mb-10 flex justify-between items-center pb-6 border-b border-white/10">
        <div>
          <span className="text-xs font-mono uppercase tracking-widest text-text-muted font-medium">Seeker Studio</span>
          <h1 className="font-display text-2xl md:text-3xl font-bold tracking-tight mt-1">Intent & Scope Engine</h1>
        </div>
      </header>

      {/* Interactive Intent Form */}
      <section className="mb-10">
        <SolidCard variant="glass" className="p-5 border border-white/10 rounded-lg">
          <label className="block text-xs font-mono uppercase tracking-wider text-text-muted mb-2.5 font-medium">
            Describe Service Requirement
          </label>
          <div className="relative">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Find a verified photographer for my event, max $150..."
              className="w-full bg-black/40 border border-white/10 rounded-md p-3.5 text-foreground placeholder:text-text-muted focus:outline-none focus:border-white/30 transition-all resize-none text-sm leading-relaxed font-sans"
              rows={3}
            />
            <div className="mt-3 flex flex-wrap justify-between items-center gap-3">
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => { setPrompt("Find a verified photographer for my event, max $150."); handleAnalyzeIntent("Find a verified photographer for my event, max $150."); }}
                  className="text-xs font-mono bg-white/5 hover:bg-white/10 px-3 py-1.5 rounded-md border border-white/10 text-text-muted hover:text-foreground transition-all cursor-pointer"
                >
                  Photographer ($150 Cap)
                </button>
                <button
                  type="button"
                  onClick={() => { setPrompt("Paint a 2-bedroom in Surulere under ₦180k this Saturday."); handleAnalyzeIntent("Paint a 2-bedroom in Surulere under ₦180k this Saturday."); }}
                  className="text-xs font-mono bg-white/5 hover:bg-white/10 px-3 py-1.5 rounded-md border border-white/10 text-text-muted hover:text-foreground transition-all cursor-pointer"
                >
                  Painter (₦180k Cap)
                </button>
              </div>

              <PrimaryButton 
                onClick={() => handleAnalyzeIntent(prompt)} 
                disabled={isAnalyzing || !prompt.trim()}
                className="px-5 py-2 text-xs flex items-center gap-2"
              >
                {isAnalyzing ? (
                  <>
                    <div className="w-3 h-3 border-2 border-black/20 border-t-black rounded-full animate-spin" />
                    <span>Parsing Rules...</span>
                  </>
                ) : (
                  <>
                    <Search className="w-3.5 h-3.5" />
                    <span>Analyze Intent</span>
                  </>
                )}
              </PrimaryButton>
            </div>
          </div>
        </SolidCard>
      </section>

      {/* AI Analysis & Provider Recommendations */}
      <AnimatePresence mode="wait">
        {intent && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ type: "spring", bounce: 0, duration: 0.35 }}
            className="space-y-6"
          >
            {/* Structured Intent Card */}
            <SolidCard variant="glass" className="p-5 rounded-lg border-l-2 border-l-white">
              <div className="flex justify-between items-center mb-3">
                <span className="text-xs font-mono uppercase tracking-widest text-text-muted font-semibold">
                  Deterministic Intent Schema
                </span>
                <span className="text-xs font-mono text-text-muted">Intent ID: {intent.id}</span>
              </div>
              
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 py-3 border-y border-white/10 font-mono text-xs">
                <div>
                  <span className="text-text-muted block mb-0.5">Service</span>
                  <span className="font-semibold text-foreground">{intent.service}</span>
                </div>
                <div>
                  <span className="text-text-muted block mb-0.5">Max Budget Cap</span>
                  <span className="font-bold text-success">${intent.maxUsd} USD</span>
                </div>
                <div>
                  <span className="text-text-muted block mb-0.5">Location</span>
                  <span className="text-foreground">{intent.city}</span>
                </div>
                <div>
                  <span className="text-text-muted block mb-0.5">Policy Gate</span>
                  <span className="text-xs px-2 py-0.5 rounded-sm bg-transparent text-success border border-success/50">Privy Mandate Bound</span>
                </div>
              </div>
            </SolidCard>

            {/* Provider Candidates */}
            <div>
              <h2 className="text-xs font-mono uppercase tracking-widest text-text-muted mb-3 font-semibold">
                Matched Providers (Ranked via The Graph Indexer)
              </h2>

              <div className="space-y-3">
                {intent.providers.map((provider) => (
                  <QuoteCard key={provider.id} provider={provider} intentId={intent.id} />
                ))}
              </div>
            </div>

            {/* Bottom CTA */}
            <div className="pt-2 flex justify-end">
              <Link href={`/intent/${intent.id}`}>
                <PrimaryButton variant="primary" className="px-6 py-3 text-xs flex items-center gap-2">
                  <span>Proceed to Quote & Escrow Hub</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </PrimaryButton>
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </main>
  );
}
