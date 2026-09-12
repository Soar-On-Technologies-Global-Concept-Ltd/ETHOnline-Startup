"use client";

import { usePrivy } from "@privy-io/react-auth";
import { useRouter } from "next/navigation";
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { SolidCard } from '@/components/ui/SolidCard';
import { FiArrowRight as ArrowRight } from "react-icons/fi";
import { motion } from "framer-motion";

export default function LandingPage() {
  const { login, ready, authenticated } = usePrivy();
  const router = useRouter();


  return (
    <div className="min-h-screen bg-background flex flex-col selection:bg-white/20 selection:text-white">
      {/* Landing Header */}
      <header className="h-16 flex items-center justify-between px-6 border-b border-white/5 bg-background/80 backdrop-blur-md sticky top-0 z-50">
        <div className="flex items-center gap-2.5 group cursor-pointer" onClick={() => router.push("/")}>
          <div className="w-7 h-7 rounded-md bg-white text-black font-display font-extrabold flex items-center justify-center text-sm shadow-sm group-hover:scale-105 transition-transform">
            I
          </div>
          <span className="text-lg font-display font-bold tracking-tight text-foreground hidden sm:inline">Intentra</span>
        </div>
        <div className="flex items-center gap-4">
           {authenticated ? (
             <button onClick={() => router.push("/dashboard/consumer")} className="text-xs font-mono bg-white/5 hover:bg-white/10 px-4 py-2 rounded-md border border-white/10 transition-all text-text-muted hover:text-foreground">
               Dashboard
             </button>
           ) : (
             <button onClick={login} disabled={!ready} className="text-xs font-mono bg-white/5 hover:bg-white/10 px-4 py-2 rounded-md border border-white/10 transition-all text-text-muted hover:text-foreground">
               Sign In
             </button>
           )}
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 w-full max-w-5xl mx-auto flex flex-col items-center justify-center px-4 sm:px-6 py-12 sm:py-0 text-center">
        {/* Simple Text Tag */}
        <motion.div 
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="inline-flex items-center gap-2 px-3 py-1 rounded-md bg-white/5 border border-white/10 text-[11px] font-mono text-text-muted mb-6"
        >
          <span>ETHOnline 2026 • AI Commerce Protocol</span>
        </motion.div>

        {/* Hero Headline */}
        <motion.h1 
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="font-display text-3xl sm:text-5xl md:text-6xl font-bold tracking-tight text-foreground leading-[1.1] sm:leading-[1.08] mb-4 max-w-4xl"
        >
          Hire verified professionals. <br className="hidden sm:inline"/>
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-white via-white/80 to-white/40">
            Let AI handle the negotiation.
          </span>
        </motion.h1>

        {/* Subtitle */}
        <motion.p 
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.15 }}
          className="max-w-xl text-xs sm:text-sm text-text-muted mb-8 leading-relaxed font-normal px-2"
        >
          A decentralized service marketplace where AI finds the perfect provider, World ID verifies their humanity, and Arc USDC escrows your funds.
        </motion.p>

        {/* Action Button */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ type: "spring", bounce: 0, duration: 0.35, delay: 0.2 }}
          className="flex flex-col sm:flex-row gap-3 mb-12 sm:mb-16 w-full sm:w-auto"
        >
          <PrimaryButton variant="primary" className="text-xs px-6 py-3.5 sm:py-3 flex items-center justify-center gap-2 w-full sm:w-auto" onClick={() => authenticated ? router.push("/dashboard/consumer") : login()} disabled={!ready}>
            <span>{authenticated ? "Go to Dashboard" : "Start Accountable Transaction"}</span>
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
          <SolidCard variant="glass" className="p-4 sm:p-5 rounded-lg">
            <span className="text-[10px] font-mono uppercase tracking-widest text-text-muted block mb-1.5 font-semibold">01 / Discovery</span>
            <h3 className="font-display font-semibold text-sm mb-1.5">AI-Driven Matching</h3>
            <p className="text-[11px] text-text-muted leading-relaxed font-sans">
              Describe your need and budget. Our AI instantly parses your intent and finds the perfect provider, secured by EIP-712 mandates.
            </p>
          </SolidCard>

          <SolidCard variant="glass" className="p-4 sm:p-5 rounded-lg">
            <span className="text-[10px] font-mono uppercase tracking-widest text-text-muted block mb-1.5 font-semibold">02 / Trust</span>
            <h3 className="font-display font-semibold text-sm mb-1.5">World ID Verification</h3>
            <p className="text-[11px] text-text-muted leading-relaxed font-sans">
              Zero bots, zero scams. Every provider proves their humanity cryptographically via World Selfie Check.
            </p>
          </SolidCard>

          <SolidCard variant="glass" className="p-4 sm:p-5 rounded-lg">
            <span className="text-[10px] font-mono uppercase tracking-widest text-text-muted block mb-1.5 font-semibold">03 / Security</span>
            <h3 className="font-display font-semibold text-sm mb-1.5">Arc Testnet Escrow</h3>
            <p className="text-[11px] text-text-muted leading-relaxed font-sans">
              Your USDC funds are securely locked in a smart contract escrow until the job is completed and approved.
            </p>
          </SolidCard>
        </motion.div>
      </main>
    </div>
  );
}
