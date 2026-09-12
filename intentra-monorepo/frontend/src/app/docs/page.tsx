"use client";

import React from 'react';
import Link from 'next/link';
import { useRouter } from "next/navigation";
import { BookOpen, ShieldCheck, Zap, Bot, ArrowRight } from 'lucide-react';
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
           <button onClick={() => router.push("/docs")} className="text-xs font-mono text-text-muted hover:text-foreground transition-colors">
             Docs
           </button>
           <button onClick={() => router.push("/")} className="text-xs font-mono bg-white/5 hover:bg-white/10 px-4 py-2 rounded-md border border-white/10 transition-all text-text-muted hover:text-foreground">
             Launch App
           </button>
        </div>
      </header>

      {/* Hero Section */}
      <div className="relative overflow-hidden pt-16 pb-24 lg:pt-32 lg:pb-32 border-b border-white/5">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(139,92,246,0.15),transparent_50%)]"></div>
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.div 
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-md bg-white/5 border border-white/10 text-[11px] font-mono text-text-muted mb-8"
          >
            <BookOpen className="w-3.5 h-3.5" />
            Product Documentation
          </motion.div>
          
          <motion.h1 
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="font-display text-4xl md:text-6xl lg:text-7xl font-extrabold tracking-tight mb-8 leading-[1.1]"
          >
            AI-Driven Escrow on <br className="hidden sm:block" />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-indigo-500">Arc Testnet</span>
          </motion.h1>
          
          <motion.p 
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.15 }}
            className="max-w-2xl mx-auto text-sm sm:text-base md:text-lg text-text-muted mb-10 leading-relaxed font-normal"
          >
            Intentra is a decentralized platform that matches your service intents with providers, secures payments on the blockchain, and uses autonomous AI agents to arbitrate disputes fairly and securely.
          </motion.p>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 w-full max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        
        {/* Core Concepts */}
        <section className="mb-20">
          <motion.h2 
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-2xl sm:text-3xl font-display font-bold mb-8 flex items-center gap-3 text-foreground"
          >
            <Zap className="w-6 h-6 sm:w-8 sm:h-8 text-yellow-500" />
            Core Concepts
          </motion.h2>
          
          <motion.div 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.25 }}
            className="grid sm:grid-cols-2 gap-4 sm:gap-6"
          >
            <SolidCard variant="glass" className="p-5 sm:p-6 rounded-xl">
              <span className="text-[10px] font-mono uppercase tracking-widest text-text-muted block mb-2 font-semibold">01 / Creation</span>
              <h3 className="font-display text-lg font-semibold mb-3 text-foreground">Intent Matching</h3>
              <p className="text-sm text-text-muted leading-relaxed font-sans">
                Users submit natural language &quot;Intents&quot; (e.g. &quot;I need a plumber tomorrow&quot;). Our AI engines instantly parse the requirements, budget, and location to find the perfect matched provider in our decentralized network.
              </p>
            </SolidCard>
            
            <SolidCard variant="glass" className="p-5 sm:p-6 rounded-xl">
              <span className="text-[10px] font-mono uppercase tracking-widest text-text-muted block mb-2 font-semibold">02 / Trust</span>
              <h3 className="font-display text-lg font-semibold mb-3 text-foreground">Immutable Escrow</h3>
              <p className="text-sm text-text-muted leading-relaxed font-sans">
                Funds are secured on the Arc Testnet using a trustless smart contract. Payments are locked in escrow and can only be released upon mutual agreement or an authoritative AI ruling.
              </p>
            </SolidCard>
            
            <SolidCard variant="glass" className="p-5 sm:p-6 rounded-xl">
              <span className="text-[10px] font-mono uppercase tracking-widest text-text-muted block mb-2 font-semibold">03 / Security</span>
              <h3 className="font-display text-lg font-semibold mb-3 text-foreground">EIP-712 Signatures</h3>
              <p className="text-sm text-text-muted leading-relaxed font-sans">
                Intentra utilizes gasless EIP-712 signature standards to execute intent mandates and resolution signatures, ensuring maximum security and a seamless Web2-like user experience.
              </p>
            </SolidCard>
            
            <SolidCard variant="glass" className="p-5 sm:p-6 rounded-xl">
              <span className="text-[10px] font-mono uppercase tracking-widest text-text-muted block mb-2 font-semibold">04 / Automation</span>
              <h3 className="font-display text-lg font-semibold mb-3 text-foreground">AI Arbitration</h3>
              <p className="text-sm text-text-muted leading-relaxed font-sans">
                Disputes are settled instantly by an unbiased AI Arbitrator trained on service industry standards. It reviews photographic evidence and conversation history to authorize fair fund splits on-chain.
              </p>
            </SolidCard>
          </motion.div>
        </section>

        {/* How it Works */}
        <section className="mb-20">
          <motion.h2 
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="text-2xl sm:text-3xl font-display font-bold mb-8 flex items-center gap-3 text-foreground"
          >
            <ShieldCheck className="w-6 h-6 sm:w-8 sm:h-8 text-green-500" />
            How the Protocol Works
          </motion.h2>
          
          <motion.div 
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.35 }}
            className="space-y-8 pl-2 sm:pl-0"
          >
            <div className="flex gap-4 sm:gap-6 relative">
              <div className="flex flex-col items-center">
                <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-white/5 border border-white/10 text-white flex items-center justify-center font-display font-bold z-10 shrink-0">1</div>
                <div className="absolute top-10 bottom-[-2rem] left-4 sm:left-5 w-px bg-white/10"></div>
              </div>
              <div className="pb-8">
                <h3 className="font-display text-lg sm:text-xl font-semibold mb-2 text-foreground">Intent Creation</h3>
                <p className="text-sm text-text-muted font-sans leading-relaxed">The user submits a natural language request. Our NVIDIA-powered LLMs parse the intent into a strict JSON schema, locking in the scope of work and budget parameters.</p>
              </div>
            </div>
            
            <div className="flex gap-4 sm:gap-6 relative">
              <div className="flex flex-col items-center">
                <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-white/5 border border-white/10 text-white flex items-center justify-center font-display font-bold z-10 shrink-0">2</div>
                <div className="absolute top-10 bottom-[-2rem] left-4 sm:left-5 w-px bg-white/10"></div>
              </div>
              <div className="pb-8">
                <h3 className="font-display text-lg sm:text-xl font-semibold mb-2 text-foreground">Smart Contract Funding</h3>
                <p className="text-sm text-text-muted font-sans leading-relaxed">The user signs a transaction authorizing the transfer of USDC into the `IntentraEscrow.sol` smart contract deployed on Arc Testnet, binding the parsed intent data to the on-chain agreement.</p>
              </div>
            </div>
            
            <div className="flex gap-4 sm:gap-6 relative">
              <div className="flex flex-col items-center">
                <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-white/5 border border-white/10 text-white flex items-center justify-center font-display font-bold z-10 shrink-0">3</div>
                <div className="absolute top-10 bottom-[-2rem] left-4 sm:left-5 w-px bg-white/10"></div>
              </div>
              <div className="pb-8">
                <h3 className="font-display text-lg sm:text-xl font-semibold mb-2 text-foreground">Service Delivery & Dispute (Optional)</h3>
                <p className="text-sm text-text-muted font-sans leading-relaxed">The provider delivers the service. If a disagreement arises, either party can upload photographic evidence and initiate a dispute through the platform UI.</p>
              </div>
            </div>
            
            <div className="flex gap-4 sm:gap-6 relative">
              <div className="flex flex-col items-center">
                <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-white/5 border border-white/10 text-white flex items-center justify-center font-display font-bold z-10 shrink-0">4</div>
              </div>
              <div>
                <h3 className="font-display text-lg sm:text-xl font-semibold mb-2 text-foreground">Resolution Execution</h3>
                <p className="text-sm text-text-muted font-sans leading-relaxed">The AI Arbitrator reviews evidence and renders a binding percentage split. The backend dynamically generates an EIP-712 payload representing the split, which the user signs. The backend then executes the smart contract release, natively distributing funds back to the user and provider wallets.</p>
              </div>
            </div>
          </motion.div>
        </section>
        
        {/* Call to Action */}
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="mt-12 p-8 sm:p-12 glass-card rounded-2xl text-center relative overflow-hidden"
        >
          <div className="absolute inset-0 bg-gradient-to-br from-purple-600/10 to-indigo-600/10 pointer-events-none"></div>
          <div className="relative z-10">
            <h2 className="font-display text-2xl sm:text-3xl font-bold mb-4 text-foreground">Ready to experience the future of service agreements?</h2>
            <p className="text-sm sm:text-base text-text-muted mb-8 max-w-lg mx-auto font-sans">Try our testnet demo today and see how AI and Web3 combine to create trustless, frictionless commerce.</p>
            <Link href="/">
              <PrimaryButton variant="primary" className="text-sm px-8 py-3.5 flex items-center justify-center gap-2 mx-auto">
                <span>Open App</span>
                <ArrowRight className="w-4 h-4" />
              </PrimaryButton>
            </Link>
          </div>
        </motion.div>

      </div>
    </div>
  );
}
