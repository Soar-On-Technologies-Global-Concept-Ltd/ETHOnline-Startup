"use client";

import React from 'react';
import { useRouter } from "next/navigation";
import { FiBookOpen as BookOpen, FiShield as ShieldCheck, FiZap as Zap, FiArrowRight as ArrowRight } from 'react-icons/fi';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { SolidCard } from '@/components/ui/SolidCard';
import { motion } from "framer-motion";

export default function DocsPage() {
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
           <button onClick={() => router.push("/")} className="text-xs font-mono text-text-muted hover:text-foreground transition-colors">
             Home
           </button>
           <button onClick={() => router.push("/dashboard/consumer")} className="text-xs font-mono bg-white/5 hover:bg-white/10 px-4 py-2 rounded-md border border-white/10 transition-all text-text-muted hover:text-foreground">
             Dashboard
           </button>
        </div>
      </header>

      {/* Main Content Container */}
      <main className="flex-1 w-full max-w-5xl mx-auto flex flex-col items-center px-4 sm:px-6 py-16 sm:py-24 text-center">
        
        {/* Simple Text Tag */}
        <motion.div 
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="inline-flex items-center gap-2 px-3 py-1 rounded-md bg-white/5 border border-white/10 text-[11px] font-mono text-text-muted mb-8"
        >
          <BookOpen className="w-3.5 h-3.5" />
          <span>Technical Documentation</span>
        </motion.div>
        
        {/* Hero Headline */}
        <motion.h1 
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="font-display text-3xl sm:text-5xl md:text-6xl font-bold tracking-tight text-foreground leading-[1.1] sm:leading-[1.08] mb-6 max-w-4xl"
        >
          AI-Driven Escrow. <br className="hidden sm:inline"/>
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-white via-white/80 to-white/40">
            Powered by Arc Testnet.
          </span>
        </motion.h1>
        
        {/* Subtitle */}
        <motion.p 
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.15 }}
          className="max-w-xl text-xs sm:text-sm text-text-muted mb-16 leading-relaxed font-normal px-2"
        >
          Intentra is a decentralized platform that matches your service intents with providers, secures payments on the blockchain, and uses autonomous AI agents to arbitrate disputes fairly and securely.
        </motion.p>

        {/* Section: Core Concepts */}
        <div className="w-full text-left mt-8 mb-20">
          <motion.div 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="flex items-center gap-3 mb-8 px-2"
          >
            <Zap className="w-5 h-5 text-foreground" />
            <h2 className="text-xl sm:text-2xl font-display font-bold text-foreground tracking-tight">Core Concepts</h2>
          </motion.div>
          
          <motion.div 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.25 }}
            className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 sm:gap-4 w-full"
          >
            <SolidCard variant="glass" className="p-4 sm:p-5 rounded-lg">
              <span className="text-[10px] font-mono uppercase tracking-widest text-text-muted block mb-1.5 font-semibold">01 / Creation</span>
              <h3 className="font-display font-semibold text-sm mb-1.5">Intent Matching</h3>
              <p className="text-[11px] text-text-muted leading-relaxed font-sans">
                Users submit natural language Intents (e.g. &quot;I need a plumber tomorrow&quot;). Our AI engines parse the requirements, budget, and location to find the perfect match.
              </p>
            </SolidCard>
            
            <SolidCard variant="glass" className="p-4 sm:p-5 rounded-lg">
              <span className="text-[10px] font-mono uppercase tracking-widest text-text-muted block mb-1.5 font-semibold">02 / Trust</span>
              <h3 className="font-display font-semibold text-sm mb-1.5">Immutable Escrow</h3>
              <p className="text-[11px] text-text-muted leading-relaxed font-sans">
                Funds are secured on the Arc Testnet using a trustless smart contract. Payments are locked in escrow and released upon mutual agreement or AI ruling.
              </p>
            </SolidCard>
            
            <SolidCard variant="glass" className="p-4 sm:p-5 rounded-lg">
              <span className="text-[10px] font-mono uppercase tracking-widest text-text-muted block mb-1.5 font-semibold">03 / Security</span>
              <h3 className="font-display font-semibold text-sm mb-1.5">EIP-712 Signatures</h3>
              <p className="text-[11px] text-text-muted leading-relaxed font-sans">
                Intentra utilizes gasless EIP-712 signature standards to execute intent mandates and resolution signatures, ensuring maximum security and a Web2-like UX.
              </p>
            </SolidCard>
            
            <SolidCard variant="glass" className="p-4 sm:p-5 rounded-lg">
              <span className="text-[10px] font-mono uppercase tracking-widest text-text-muted block mb-1.5 font-semibold">04 / Automation</span>
              <h3 className="font-display font-semibold text-sm mb-1.5">AI Arbitration</h3>
              <p className="text-[11px] text-text-muted leading-relaxed font-sans">
                Disputes are settled instantly by an unbiased AI Arbitrator trained on service industry standards. It reviews photographic evidence and authorizes fair fund splits on-chain.
              </p>
            </SolidCard>
          </motion.div>
        </div>

        {/* Section: How it Works */}
        <div className="w-full text-left mb-24">
          <motion.div 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="flex items-center gap-3 mb-8 px-2"
          >
            <ShieldCheck className="w-5 h-5 text-foreground" />
            <h2 className="text-xl sm:text-2xl font-display font-bold text-foreground tracking-tight">How the Protocol Works</h2>
          </motion.div>
          
          <motion.div 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.35 }}
            className="space-y-6 sm:space-y-8 pl-1 sm:pl-2"
          >
            <div className="flex gap-4 sm:gap-6 relative">
              <div className="flex flex-col items-center">
                <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-white/5 border border-white/10 text-text-muted flex items-center justify-center font-mono text-[10px] font-bold z-10 shrink-0">01</div>
                <div className="absolute top-8 bottom-[-1.5rem] left-3.5 sm:left-4 w-px bg-white/10"></div>
              </div>
              <div className="pb-6">
                <h3 className="font-display text-sm sm:text-base font-semibold mb-1.5 text-foreground">Intent Creation</h3>
                <p className="text-[11px] sm:text-xs text-text-muted font-sans leading-relaxed max-w-3xl">The user submits a natural language request. Our NVIDIA-powered LLMs parse the intent into a strict JSON schema, locking in the scope of work and budget parameters.</p>
              </div>
            </div>
            
            <div className="flex gap-4 sm:gap-6 relative">
              <div className="flex flex-col items-center">
                <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-white/5 border border-white/10 text-text-muted flex items-center justify-center font-mono text-[10px] font-bold z-10 shrink-0">02</div>
                <div className="absolute top-8 bottom-[-1.5rem] left-3.5 sm:left-4 w-px bg-white/10"></div>
              </div>
              <div className="pb-6">
                <h3 className="font-display text-sm sm:text-base font-semibold mb-1.5 text-foreground">Smart Contract Funding</h3>
                <p className="text-[11px] sm:text-xs text-text-muted font-sans leading-relaxed max-w-3xl">The user signs a transaction authorizing the transfer of USDC into the `IntentraEscrow.sol` smart contract deployed on Arc Testnet, binding the parsed intent data to the on-chain agreement.</p>
              </div>
            </div>
            
            <div className="flex gap-4 sm:gap-6 relative">
              <div className="flex flex-col items-center">
                <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-white/5 border border-white/10 text-text-muted flex items-center justify-center font-mono text-[10px] font-bold z-10 shrink-0">03</div>
                <div className="absolute top-8 bottom-[-1.5rem] left-3.5 sm:left-4 w-px bg-white/10"></div>
              </div>
              <div className="pb-6">
                <h3 className="font-display text-sm sm:text-base font-semibold mb-1.5 text-foreground">Service Delivery & Dispute (Optional)</h3>
                <p className="text-[11px] sm:text-xs text-text-muted font-sans leading-relaxed max-w-3xl">The provider delivers the service. If a disagreement arises, either party can upload photographic evidence and initiate a dispute through the platform UI.</p>
              </div>
            </div>
            
            <div className="flex gap-4 sm:gap-6 relative">
              <div className="flex flex-col items-center">
                <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-white/5 border border-white/10 text-text-muted flex items-center justify-center font-mono text-[10px] font-bold z-10 shrink-0">04</div>
              </div>
              <div>
                <h3 className="font-display text-sm sm:text-base font-semibold mb-1.5 text-foreground">Resolution Execution</h3>
                <p className="text-[11px] sm:text-xs text-text-muted font-sans leading-relaxed max-w-3xl">The AI Arbitrator reviews evidence and renders a binding percentage split. The backend dynamically generates an EIP-712 payload representing the split, which the user signs. The backend then executes the smart contract release, natively distributing funds back to the user and provider wallets.</p>
              </div>
            </div>
          </motion.div>
        </div>
        
        {/* Call to Action */}
        <motion.div 
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="w-full max-w-xl mx-auto flex flex-col items-center justify-center text-center mt-8 mb-12"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-md bg-white/5 border border-white/10 text-[10px] font-mono uppercase tracking-widest text-text-muted mb-6 font-semibold">
            Testnet Alpha
          </div>
          <h2 className="font-display text-xl sm:text-2xl font-bold mb-3 text-foreground">Ready to experience the future of service agreements?</h2>
          <p className="text-xs sm:text-sm text-text-muted mb-8 font-sans leading-relaxed">Try our testnet demo today and see how AI and Web3 combine to create trustless, frictionless commerce.</p>
          <PrimaryButton variant="primary" className="text-xs px-6 py-3.5 flex items-center justify-center gap-2 w-full sm:w-auto" onClick={() => router.push("/")}>
            <span>Return Home</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </PrimaryButton>
        </motion.div>

      </main>
    </div>
  );
}
