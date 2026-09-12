"use client";

import { usePrivy } from "@privy-io/react-auth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { SolidCard } from '@/components/ui/SolidCard';
import { ArrowRight } from "lucide-react";
import { motion } from "framer-motion";

export default function LandingPage() {
  const { login, ready, authenticated } = usePrivy();
  const router = useRouter();

  useEffect(() => {
    if (ready && authenticated) {
      router.push("/dashboard/consumer");
    }
  }, [ready, authenticated, router]);

  return (
    <div className="min-h-screen bg-background flex flex-col selection:bg-white/20 selection:text-white">
      <main className="flex-1 flex flex-col items-center justify-center text-center px-6 pt-24 pb-20 max-w-5xl mx-auto">
        {/* Simple Text Tag */}
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="inline-flex items-center gap-2 px-3 py-1 rounded-md bg-white/5 border border-white/10 text-xs font-mono text-text-muted mb-8"
        >
          <span>ETHOnline 2026 • AI Commerce Protocol</span>
        </motion.div>

        {/* Hero Headline */}
        <motion.h1 
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="font-display text-5xl sm:text-6xl md:text-7xl font-bold tracking-tight text-foreground leading-[1.08] mb-6 max-w-4xl"
        >
          AI prepares. <br/>
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-white via-white/80 to-white/40">
            Humans authorize.
          </span>
        </motion.h1>

        {/* Subtitle */}
        <motion.p 
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="max-w-2xl text-base md:text-lg text-text-muted mb-10 leading-relaxed font-normal"
        >
          An AI-mediated service marketplace secured by EIP-712 spending mandates, World ID human verification, and Arc USDC escrow.
        </motion.p>

        {/* Action Button */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ type: "spring", bounce: 0, duration: 0.4, delay: 0.3 }}
          className="flex flex-col sm:flex-row gap-4 w-full sm:w-auto"
        >
          <PrimaryButton variant="primary" className="text-sm px-7 py-3 flex items-center justify-center gap-2" onClick={login} disabled={!ready}>
            <span>Start Accountable Transaction</span>
            <ArrowRight className="w-4 h-4" />
          </PrimaryButton>
        </motion.div>

        {/* Feature Cards Grid */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="grid sm:grid-cols-3 gap-6 mt-20 text-left w-full"
        >
          <SolidCard variant="glass" className="p-6">
            <span className="text-xs font-mono uppercase tracking-widest text-text-muted block mb-2 font-semibold">01 / Authority</span>
            <h3 className="font-display font-semibold text-base mb-2">EIP-712 Mandates</h3>
            <p className="text-xs text-text-muted leading-relaxed font-sans">
              Agent proposes terms, but explicit cryptographic signatures enforce strict budget caps (e.g. max $150).
            </p>
          </SolidCard>

          <SolidCard variant="glass" className="p-6">
            <span className="text-xs font-mono uppercase tracking-widest text-text-muted block mb-2 font-semibold">02 / Identity</span>
            <h3 className="font-display font-semibold text-base mb-2">World Selfie Check</h3>
            <p className="text-xs text-text-muted leading-relaxed font-sans">
              Biometric proof of humanity at funding & dispute steps prevents malicious bot drain.
            </p>
          </SolidCard>

          <SolidCard variant="glass" className="p-6">
            <span className="text-xs font-mono uppercase tracking-widest text-text-muted block mb-2 font-semibold">03 / Settlement</span>
            <h3 className="font-display font-semibold text-base mb-2">Arc Testnet Escrow</h3>
            <p className="text-xs text-text-muted leading-relaxed font-sans">
              Funds stay locked in USDC smart contract until evidence is anchored or AI arbitrator resolves dispute.
            </p>
          </SolidCard>
        </motion.div>
      </main>
    </div>
  );
}
