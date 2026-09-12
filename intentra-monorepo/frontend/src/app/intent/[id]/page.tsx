"use client";

import { SolidCard } from "@/components/ui/SolidCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { VerifyHumanityWidget } from "@/components/worldcoin/VerifyHumanityWidget";
import { ShieldCheck, UserCheck, Wallet } from "lucide-react";
import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import Link from "next/link";
import { PrimaryButton } from "@/components/ui/PrimaryButton";
import { useIntentStore } from "@/store/intentStore";
import { usePrivy } from "@privy-io/react-auth";
import { useRouter } from "next/navigation";

export default function IntentTransactionPage() {
  const [trustScore, setTrustScore] = useState(0);
  const isVerified = useIntentStore(state => state.isVerified);
  
  const { ready, authenticated } = usePrivy();
  const router = useRouter();

  useEffect(() => {
    if (ready && !authenticated) {
      router.push("/");
    }
  }, [ready, authenticated, router]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setTrustScore(98);
    }, 500);
    return () => clearTimeout(timer);
  }, []);

  if (!ready || !authenticated) {
    return <div className="min-h-screen flex items-center justify-center text-text-muted">Loading Transaction Securely...</div>;
  }

  return (
    <main className="max-w-3xl mx-auto p-6 md:p-12">
      <header className="mb-10 flex items-start justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold mb-2">Intent: Paint 2-Bedroom</h1>
          <p className="text-text-muted font-mono text-sm">ID: 0x9b4f...a1c2</p>
        </div>
        <StatusBadge status="pending" label="Pending Escrow" />
      </header>

      <div className="grid gap-6 md:grid-cols-2 mb-10">
        <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>
          <SolidCard className="p-6 h-full border border-border">
            <div className="flex items-center gap-3 mb-4">
              <UserCheck className="w-6 h-6 text-primary" />
              <h2 className="font-semibold text-lg">Provider</h2>
            </div>
            <p className="font-medium text-lg mb-1">Tunde Paints Ltd.</p>
            <div className="flex items-center gap-2 text-sm text-text-muted mb-4">
              <ShieldCheck className="w-4 h-4 text-success" />
              <span>Verified Identity</span>
            </div>
            
            <div className="pt-4 border-t border-border">
              <p className="text-xs text-text-muted mb-1 uppercase tracking-wider font-semibold">On-Chain Trust Score</p>
              <div className="flex items-end gap-2">
                <span className="text-3xl font-display font-bold text-success">{trustScore}%</span>
                <span className="text-xs text-text-muted mb-1">from 142 jobs</span>
              </div>
            </div>
          </SolidCard>
        </motion.div>

        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }}>
          <SolidCard className="p-6 h-full border border-border bg-surface">
            <div className="flex items-center gap-3 mb-4">
              <Wallet className="w-6 h-6 text-foreground" />
              <h2 className="font-semibold text-lg">Escrow Terms</h2>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between items-center py-2 border-b border-border/50">
                <span className="text-text-muted">Amount</span>
                <span className="font-bold">₦ 160,000</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-border/50">
                <span className="text-text-muted">Network</span>
                <span className="font-mono text-sm bg-surface-hover px-2 py-1 rounded">Arc Testnet</span>
              </div>
              <div className="flex justify-between items-center py-2">
                <span className="text-text-muted">Condition</span>
                <span className="text-sm font-medium text-right max-w-[140px]">Release on photo confirmation</span>
              </div>
            </div>
          </SolidCard>
        </motion.div>
      </div>

      <motion.div 
        initial={{ opacity: 0, y: 20 }} 
        animate={{ opacity: 1, y: 0 }} 
        transition={{ delay: 0.3 }}
        className="p-8 border-2 border-dashed border-border rounded-xl text-center bg-surface-hover"
      >
        <h3 className="font-display font-bold text-xl mb-3">Lock Funds & Approve</h3>
        <p className="text-text-muted mb-6 max-w-md mx-auto text-sm">
          Before cryptographically signing the EIP-712 Mandate to lock funds, you must verify you are a unique human to prevent bot abuse.
        </p>
        
        <div className="max-w-sm mx-auto">
          <VerifyHumanityWidget action="lock-escrow-123" />
        </div>

        {isVerified && (
          <motion.div 
            initial={{ opacity: 0, height: 0 }} 
            animate={{ opacity: 1, height: 'auto' }} 
            className="mt-6 pt-6 border-t border-border"
          >
            <p className="text-sm text-text-muted mb-4">Humanity verified successfully. You may now sign the mandate.</p>
            <Link href="/dashboard/consumer">
              <PrimaryButton className="w-full">
                Sign Mandate & Lock Funds
              </PrimaryButton>
            </Link>
          </motion.div>
        )}
      </motion.div>
    </main>
  );
}
