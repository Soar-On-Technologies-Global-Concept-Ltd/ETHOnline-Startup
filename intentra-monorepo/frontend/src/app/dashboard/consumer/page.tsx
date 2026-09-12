"use client";

import { PrimaryButton } from "@/components/ui/PrimaryButton";
import { SolidCard } from "@/components/ui/SolidCard";
import { ArrowRight, Search } from "lucide-react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { usePrivy } from "@privy-io/react-auth";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function ConsumerDashboard() {
  const { ready, authenticated, user } = usePrivy();
  const router = useRouter();

  const [prompt, setPrompt] = useState("Find a verified photographer for my event, max $150.");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [parsedResult, setParsedResult] = useState<any>(null);

  useEffect(() => {
    if (ready && !authenticated) {
      router.push("/");
    }
  }, [ready, authenticated, router]);

  const handleAnalyzeIntent = (inputPrompt: string) => {
    setIsAnalyzing(true);
    setParsedResult(null);

    setTimeout(() => {
      setIsAnalyzing(false);
      setParsedResult({
        service: "Event Photography",
        city: "San Francisco / Remote Event",
        maxUsd: 150,
        window: "This Saturday",
        providers: [
          { id: "p1", name: "Apex Photography Studio", trustScore: 98, jobs: 142, quote: 145, recommended: true },
          { id: "p2", name: "FocusCraft Media", trustScore: 94, jobs: 89, quote: 150, recommended: false },
          { id: "p3", name: "Lumina Event Shots", trustScore: 91, jobs: 54, quote: 135, recommended: false },
        ]
      });
    }, 1000);
  };

  useEffect(() => {
    handleAnalyzeIntent(prompt);
  }, []);

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
          <span className="text-xs font-mono uppercase tracking-widest text-text-muted font-medium">Consumer Studio</span>
          <h1 className="font-display text-2xl md:text-3xl font-bold tracking-tight mt-1">Intent & Scope Engine</h1>
        </div>
        <div className="flex items-center gap-2 px-3 py-1 rounded-md bg-white/5 border border-white/10 text-xs font-mono">
          <span className="w-1.5 h-1.5 rounded-full bg-success" />
          <span className="text-text-muted">{user?.email?.address || "Privy User"}</span>
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
        {parsedResult && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ type: "spring", bounce: 0, duration: 0.35 }}
            className="space-y-6"
          >
            {/* Structured Intent Card */}
            <SolidCard variant="glass" className="p-5 rounded-lg border-l-2 border-l-white">
              <span className="text-xs font-mono uppercase tracking-widest text-text-muted block mb-3 font-semibold">
                Deterministic Intent Schema
              </span>
              
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 py-3 border-y border-white/10 font-mono text-xs">
                <div>
                  <span className="text-text-muted block mb-0.5">Service</span>
                  <span className="font-semibold text-foreground">{parsedResult.service}</span>
                </div>
                <div>
                  <span className="text-text-muted block mb-0.5">Max Budget Cap</span>
                  <span className="font-bold text-success">${parsedResult.maxUsd} USD</span>
                </div>
                <div>
                  <span className="text-text-muted block mb-0.5">Timeline</span>
                  <span className="text-foreground">{parsedResult.window}</span>
                </div>
                <div>
                  <span className="text-text-muted block mb-0.5">Policy Gate</span>
                  <span className="text-xs px-2 py-0.5 rounded-sm bg-success/20 text-success border border-success/30">Privy Mandate Bound</span>
                </div>
              </div>
            </SolidCard>

            {/* Provider Candidates */}
            <div>
              <h2 className="text-xs font-mono uppercase tracking-widest text-text-muted mb-3 font-semibold">
                Matched Providers (Ranked via The Graph Indexer)
              </h2>

              <div className="space-y-3">
                {parsedResult.providers.map((provider: any) => (
                  <SolidCard 
                    key={provider.id}
                    variant={provider.recommended ? "glass" : "solid"}
                    className={`p-5 rounded-lg transition-all ${provider.recommended ? 'border-white/30 bg-white/[0.06]' : 'opacity-80'}`}
                  >
                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-display font-bold text-base">{provider.name}</h3>
                          {provider.recommended && (
                            <span className="text-[10px] font-mono uppercase tracking-wider bg-white text-black px-2 py-0.5 rounded-sm font-semibold">
                              AI Pick #1
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 mt-1.5 text-xs text-text-muted font-mono">
                          <span className="text-success font-semibold">
                            {provider.trustScore}% Trust Score
                          </span>
                          <span>({provider.jobs} Jobs Indexed on The Graph)</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-4 w-full sm:w-auto justify-between sm:justify-end">
                        <div className="text-right">
                          <span className="text-[10px] font-mono text-text-muted block">Quoted Price</span>
                          <span className="text-lg font-display font-bold">${provider.quote} USD</span>
                        </div>

                        <Link href="/intent/123">
                          <PrimaryButton variant={provider.recommended ? "primary" : "secondary"} className="px-4 py-2 text-xs">
                            Select & Lock Escrow
                          </PrimaryButton>
                        </Link>
                      </div>
                    </div>
                  </SolidCard>
                ))}
              </div>
            </div>

            {/* Bottom CTA */}
            <div className="pt-2 flex justify-end">
              <Link href="/intent/123">
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
