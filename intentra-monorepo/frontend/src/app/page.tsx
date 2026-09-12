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
    <div className="min-h-[calc(100vh-4rem)] md:h-[calc(100vh-4rem)] md:max-h-[calc(100vh-4rem)] md:overflow-hidden bg-background flex flex-col justify-center items-center px-4 sm:px-6 py-6 sm:py-0 selection:bg-white/20 selection:text-white">
      <main className="w-full max-w-5xl mx-auto flex flex-col items-center text-center justify-center py-2">
        {/* Simple Text Tag */}
        <motion.div 
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="inline-flex items-center gap-2 px-3 py-1 rounded-md bg-white/5 border border-white/10 text-[11px] font-mono text-text-muted mb-4"
        >
          <span>ETHOnline 2026 • AI Commerce Protocol</span>
        </motion.div>

        {/* Hero Headline */}
        <motion.h1 
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="font-display text-3xl sm:text-5xl md:text-6xl font-bold tracking-tight text-foreground leading-[1.1] sm:leading-[1.08] mb-4 max-w-3xl"
        >
          AI prepares. <br className="hidden sm:inline"/>
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-white via-white/80 to-white/40">
            Humans authorize.
          </span>
        </motion.h1>

        {/* Subtitle */}
        <motion.p 
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.15 }}
          className="max-w-xl text-xs sm:text-sm text-text-muted mb-6 leading-relaxed font-normal px-2"
        >
          An AI-mediated service marketplace secured by EIP-712 spending mandates, World ID human verification, and Arc USDC escrow.
        </motion.p>

        {/* Action Button */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ type: "spring", bounce: 0, duration: 0.35, delay: 0.2 }}
          className="flex flex-col sm:flex-row gap-3 mb-8 sm:mb-10 w-full sm:w-auto"
        >
          <PrimaryButton variant="primary" className="text-xs px-6 py-3 sm:py-2.5 flex items-center justify-center gap-2 w-full sm:w-auto" onClick={login} disabled={!ready}>
            <span>Start Accountable Transaction</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </PrimaryButton>
        </motion.div>

        {/* Feature Cards Grid */}
        <motion.div 
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.25 }}
          className="grid grid-cols-1 sm:grid-cols-3 gap-3.5 sm:gap-4 text-left w-full max-w-4xl"
        >
          <SolidCard variant="glass" className="p-4 sm:p-4.5 rounded-lg">
            <span className="text-[10px] font-mono uppercase tracking-widest text-text-muted block mb-1 font-semibold">01 / Authority</span>
            <h3 className="font-display font-semibold text-sm mb-1">EIP-712 Mandates</h3>
            <p className="text-[11px] text-text-muted leading-relaxed font-sans">
              Explicit cryptographic signatures enforce strict budget caps (max $150).
            </p>
          </SolidCard>

          <SolidCard variant="glass" className="p-4 sm:p-4.5 rounded-lg">
            <span className="text-[10px] font-mono uppercase tracking-widest text-text-muted block mb-1 font-semibold">02 / Identity</span>
            <h3 className="font-display font-semibold text-sm mb-1">World Selfie Check</h3>
            <p className="text-[11px] text-text-muted leading-relaxed font-sans">
              Biometric proof of humanity at funding & dispute steps prevents bot drain.
            </p>
          </SolidCard>

          <SolidCard variant="glass" className="p-4 sm:p-4.5 rounded-lg">
            <span className="text-[10px] font-mono uppercase tracking-widest text-text-muted block mb-1 font-semibold">03 / Settlement</span>
            <h3 className="font-display font-semibold text-sm mb-1">Arc Testnet Escrow</h3>
            <p className="text-[11px] text-text-muted leading-relaxed font-sans">
              USDC locked in smart contract until photo evidence or AI split resolution.
            </p>
          </SolidCard>
        </motion.div>
      </main>
    </div>
  );
}
