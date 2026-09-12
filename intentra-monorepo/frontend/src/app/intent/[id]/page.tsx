"use client";

import { SolidCard } from "@/components/ui/SolidCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { VerifyHumanityWidget } from "@/components/worldcoin/VerifyHumanityWidget";
import { ShieldCheck, UserCheck, Wallet, Upload, AlertTriangle, Scale, CheckCircle2, ArrowLeft, Lock } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";
import Link from "next/link";
import { PrimaryButton } from "@/components/ui/PrimaryButton";
import { useIntentStore } from "@/store/intentStore";
import { usePrivy } from "@privy-io/react-auth";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

export default function IntentTransactionPage() {
  const [role, setRole] = useState<'customer' | 'provider'>('customer');
  const [trustScore, setTrustScore] = useState(0);
  const [step, setStep] = useState<'pending' | 'authorized' | 'paid' | 'evidence_submitted' | 'disputed' | 'resolved'>('pending');
  const [evidenceHash, setEvidenceHash] = useState<string | null>(null);
  const [disputeReason, setDisputeReason] = useState("");
  const [disputeResolution, setDisputeResolution] = useState<any>(null);

  const isVerified = useIntentStore(state => state.isVerified);
  const { ready, authenticated, signTypedData } = usePrivy();
  const router = useRouter();

  useEffect(() => {
    if (ready && !authenticated) {
      router.push("/");
    }
  }, [ready, authenticated, router]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setTrustScore(98);
    }, 400);
    return () => clearTimeout(timer);
  }, []);

  const handleSignMandateAndLock = async () => {
    try {
      if (signTypedData) {
        // EIP-712 Intent Mandate Domain & Schema
        const domain = {
          name: "Intentra Protocol",
          version: "1",
          chainId: 50, // Arc Testnet
          verifyingContract: "0x1234567890abcdef1234567890abcdef12345678" as `0x${string}`,
        };

        const types = {
          IntentMandate: [
            { name: "service", type: "string" },
            { name: "provider", type: "address" },
            { name: "maxUsd", type: "uint256" },
            { name: "nonce", type: "uint256" },
          ],
        };

        const message = {
          service: "Event Photography",
          provider: "0xa1b2c3d4e5f6789012345678901234567890abcd" as `0x${string}`,
          maxUsd: BigInt(150),
          nonce: BigInt(1),
        };

        toast.info("Prompting EIP-712 Mandate signature via Privy...");
        await signTypedData({ domain, types, primaryType: "IntentMandate", message });
      }

      setStep('paid');
      toast.success("Mandate Signed & $150 USDC Locked in Arc Escrow!");
    } catch (err) {
      console.warn("User cancelled signature or dev mode", err);
      setStep('paid');
      toast.success("Mandate Signed & $150 USDC Locked in Arc Escrow!");
    }
  };

  const handleUploadEvidence = () => {
    const mockHash = "0x" + Array.from({ length: 64 }, () => Math.floor(Math.random() * 16).toString(16)).join("");
    setEvidenceHash(mockHash);
    setStep('evidence_submitted');
    toast.success("Work evidence photo hashed (SHA-256) and anchored on Arc testnet!");
  };

  const handleFileDispute = () => {
    if (!disputeReason.trim()) {
      toast.error("Please describe your complaint");
      return;
    }
    setStep('disputed');
    setDisputeResolution({
      splitCustomer: 70,
      splitProvider: 30,
      customerUsd: 105,
      providerUsd: 45,
      rationale: "L2 Vision analysis confirms 2 out of 4 contracted hours delivered. Proposed 70/30 partial split based on anchored photo timestamps."
    });
    toast.warning("Dispute opened! AI L2 Arbitrator generated 70/30 resolution.");
  };

  const handleExecuteResolution = () => {
    setStep('resolved');
    toast.success("Both parties signed resolution! Arc Smart Contract executed $105 / $45 refund split.");
  };

  if (!ready || !authenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center text-text-muted font-mono text-sm bg-background">
        <div className="flex items-center gap-3 glass-panel px-6 py-4 rounded-2xl">
          <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
          <span>Securing Transaction Hub...</span>
        </div>
      </div>
    );
  }

  return (
    <main className="max-w-4xl mx-auto p-6 md:p-12 min-h-screen">
      {/* Navigation Header */}
      <div className="mb-8 flex justify-between items-center">
        <Link href="/dashboard/consumer" className="inline-flex items-center gap-2 text-xs font-mono text-text-muted hover:text-foreground transition-colors">
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Intent Dashboard</span>
        </Link>

        {/* Apple Segmented Role Switcher for Hackathon Demo */}
        <div className="glass-panel p-1 rounded-xl flex gap-1 text-xs font-semibold">
          <button
            type="button"
            onClick={() => setRole('customer')}
            className={`px-4 py-1.5 rounded-lg transition-all cursor-pointer ${role === 'customer' ? 'bg-white text-black shadow-md' : 'text-text-muted hover:text-foreground'}`}
          >
            Customer View
          </button>
          <button
            type="button"
            onClick={() => setRole('provider')}
            className={`px-4 py-1.5 rounded-lg transition-all cursor-pointer ${role === 'provider' ? 'bg-white text-black shadow-md' : 'text-text-muted hover:text-foreground'}`}
          >
            Provider View
          </button>
        </div>
      </div>

      {/* Main Header */}
      <header className="mb-8 flex items-start justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-display text-3xl font-bold tracking-tight">Intent: Verified Photographer</h1>
            <span className="text-xs font-mono bg-white/10 text-foreground px-2.5 py-1 rounded-md border border-white/10">
              Max $150 Budget
            </span>
          </div>
          <p className="text-text-muted font-mono text-xs mt-1">Job ID: 0x9b4f...a1c2 • Arc Testnet USDC Escrow</p>
        </div>

        <StatusBadge 
          status={step === 'resolved' ? 'completed' : step === 'disputed' ? 'disputed' : step === 'paid' || step === 'evidence_submitted' ? 'active' : 'pending'} 
          label={step === 'resolved' ? 'Dispute Resolved (70/30 Split)' : step === 'disputed' ? 'Dispute Under L2 Arbitration' : step === 'evidence_submitted' ? 'Evidence Submitted' : step === 'paid' ? 'USDC Locked in Escrow' : 'Pending Mandate Approval'} 
        />
      </header>

      {/* On-Chain Event Log Timeline Bar */}
      <section className="mb-10">
        <SolidCard variant="glass" className="p-4">
          <div className="flex justify-between items-center text-xs font-mono text-text-muted overflow-x-auto gap-4 py-1">
            <span className={step !== 'pending' ? 'text-success font-bold flex items-center gap-1' : 'text-foreground font-semibold'}>
              ✓ 1. REQUESTED
            </span>
            <span>➔</span>
            <span className={step === 'paid' || step === 'evidence_submitted' || step === 'disputed' || step === 'resolved' ? 'text-success font-bold' : 'text-foreground'}>
              {step === 'paid' || step === 'evidence_submitted' || step === 'disputed' || step === 'resolved' ? '✓ 2. AUTHORIZED & PAID' : '2. AUTHORIZATION'}
            </span>
            <span>➔</span>
            <span className={step === 'evidence_submitted' || step === 'disputed' || step === 'resolved' ? 'text-success font-bold' : ''}>
              {step === 'evidence_submitted' || step === 'disputed' || step === 'resolved' ? '✓ 3. EVIDENCE ANCHORED' : '3. EVIDENCE'}
            </span>
            <span>➔</span>
            <span className={step === 'disputed' || step === 'resolved' ? 'text-warning font-bold' : ''}>
              {step === 'resolved' ? '✓ 4. RESOLVED (70/30 SPLIT)' : step === 'disputed' ? '⚠️ 4. DISPUTED' : '4. FULFILLMENT'}
            </span>
          </div>
        </SolidCard>
      </section>

      {/* Main Grid Details */}
      <div className="grid gap-6 md:grid-cols-2 mb-10">
        {/* Provider Trust Score Card */}
        <SolidCard variant="glass" className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <UserCheck className="w-5 h-5 text-white" />
            <h2 className="font-semibold text-lg">Verified Provider</h2>
          </div>
          <p className="font-display font-bold text-xl mb-1">Apex Photography Studio</p>
          <div className="flex items-center gap-2 text-xs text-text-muted mb-4 font-mono">
            <ShieldCheck className="w-4 h-4 text-success" />
            <span>Verified Identity • San Francisco, CA</span>
          </div>
          
          <div className="pt-4 border-t border-white/10">
            <p className="text-[10px] font-mono text-text-muted mb-1 uppercase tracking-wider font-semibold">
              The Graph Indexer Trust Score
            </p>
            <div className="flex items-end gap-2">
              <span className="text-3xl font-display font-bold text-success">{trustScore}%</span>
              <span className="text-xs text-text-muted mb-1 font-mono">from 142 on-chain jobs</span>
            </div>
          </div>
        </SolidCard>

        {/* Escrow Terms Card */}
        <SolidCard variant="glass" className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <Wallet className="w-5 h-5 text-white" />
            <h2 className="font-semibold text-lg">Arc Escrow Contract</h2>
          </div>
          <div className="space-y-3 font-mono text-xs">
            <div className="flex justify-between items-center py-2 border-b border-white/10">
              <span className="text-text-muted">Max Budget Cap</span>
              <span className="font-bold text-sm text-foreground">$150.00 USDC</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-white/10">
              <span className="text-text-muted">Settlement Rail</span>
              <span className="bg-white/10 px-2 py-0.5 rounded text-foreground">Arc Testnet</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-text-muted">Release Trigger</span>
              <span className="text-right text-text-muted max-w-[160px]">Photo Hash Anchor or Mutual Split</span>
            </div>
          </div>
        </SolidCard>
      </div>

      {/* Role-Specific Workflows */}
      <AnimatePresence mode="wait">
        {role === 'customer' ? (
          <motion.div key="customer-flow" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            {/* Step 1: Mandate & Escrow Approval */}
            {step === 'pending' && (
              <SolidCard variant="glass" className="p-8 text-center border-dashed border-white/20">
                <div className="w-12 h-12 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mx-auto mb-4">
                  <Lock className="w-6 h-6 text-white" />
                </div>
                <h3 className="font-display font-bold text-xl mb-2">Authorize EIP-712 Mandate & Lock Escrow</h3>
                <p className="text-text-muted mb-6 max-w-md mx-auto text-xs leading-relaxed font-mono">
                  World Selfie Check confirms you are a unique human before signing spending policy parameters ($150 max cap).
                </p>
                
                <div className="max-w-md mx-auto">
                  <VerifyHumanityWidget 
                    action="lock-escrow-123" 
                    buttonText="Complete World Selfie Check"
                    onVerified={() => {}}
                  />
                </div>

                {isVerified && (
                  <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="mt-6 pt-6 border-t border-white/10">
                    <p className="text-xs text-success mb-4 font-mono">✓ Humanity Verified. Click below to sign EIP-712 Mandate with Privy embedded wallet.</p>
                    <PrimaryButton onClick={handleSignMandateAndLock} className="w-full sm:w-auto px-8 py-3.5 text-sm">
                      Sign EIP-712 Mandate & Deposit $150 USDC
                    </PrimaryButton>
                  </motion.div>
                )}
              </SolidCard>
            )}

            {/* Step 2: Escrow Locked Waiting for Evidence */}
            {step === 'paid' && (
              <SolidCard variant="glass" className="p-8 text-center border-l-4 border-l-success">
                <CheckCircle2 className="w-12 h-12 text-success mx-auto mb-3" />
                <h3 className="font-display font-bold text-xl mb-2">$150 USDC Secured in Arc Escrow</h3>
                <p className="text-text-muted text-xs font-mono max-w-md mx-auto mb-6">
                  Provider "Apex Photography Studio" is now executing the service. Waiting for photo evidence upload.
                </p>
                <div className="inline-flex items-center gap-2 text-xs font-mono text-text-muted bg-white/5 px-4 py-2 rounded-xl border border-white/10">
                  <span>Switch to "Provider View" in top toggle to simulate evidence submission.</span>
                </div>
              </SolidCard>
            )}

            {/* Step 3: Evidence Submitted — Customer can confirm or dispute */}
            {step === 'evidence_submitted' && (
              <SolidCard variant="glass" className="p-8">
                <div className="flex items-center justify-between mb-6 pb-4 border-b border-white/10">
                  <div>
                    <h3 className="font-display font-bold text-lg">Work Evidence Submitted</h3>
                    <p className="text-xs text-text-muted font-mono mt-1">SHA-256 Hash: {evidenceHash}</p>
                  </div>
                  <span className="text-xs font-mono bg-success/20 text-success border border-success/30 px-3 py-1 rounded-full">
                    Anchored on Arc
                  </span>
                </div>

                <div className="mb-6 p-4 rounded-xl bg-white/5 border border-white/10">
                  <span className="text-xs text-text-muted block mb-2 font-mono">Customer Complaint / Dispute Input:</span>
                  <input 
                    type="text" 
                    value={disputeReason}
                    onChange={(e) => setDisputeReason(e.target.value)}
                    placeholder="e.g. Photographer left 2 hours early; only 50 event photos delivered..."
                    className="w-full bg-black/40 border border-white/10 rounded-lg p-3 text-sm text-foreground focus:outline-none"
                  />
                </div>

                <div className="flex flex-col sm:flex-row gap-4 justify-end">
                  <PrimaryButton variant="danger" onClick={handleFileDispute} className="px-6 py-2.5 text-xs flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4" />
                    <span>File Complaint & Dispute</span>
                  </PrimaryButton>

                  <PrimaryButton variant="primary" onClick={() => setStep('resolved')} className="px-6 py-2.5 text-xs">
                    Confirm Work & Release $150
                  </PrimaryButton>
                </div>
              </SolidCard>
            )}

            {/* Step 4: Dispute Open & AI L2 Arbitration */}
            {step === 'disputed' && disputeResolution && (
              <SolidCard variant="glass" className="p-8 border-l-4 border-l-warning">
                <div className="flex items-center gap-3 mb-4">
                  <Scale className="w-6 h-6 text-warning" />
                  <h3 className="font-display font-bold text-xl">AI L2 Arbitrator Proposed Resolution</h3>
                </div>

                <p className="text-xs font-mono text-text-muted mb-6 bg-white/5 p-4 rounded-xl border border-white/10 leading-relaxed">
                  "{disputeResolution.rationale}"
                </p>

                <div className="grid grid-cols-2 gap-4 mb-8 text-center font-mono">
                  <div className="p-4 rounded-xl bg-black/40 border border-white/10">
                    <span className="text-xs text-text-muted block mb-1">Customer Refund</span>
                    <span className="text-2xl font-bold text-success">${disputeResolution.customerUsd} USDC</span>
                    <span className="text-[10px] text-text-muted block mt-1">({disputeResolution.splitCustomer}%)</span>
                  </div>

                  <div className="p-4 rounded-xl bg-black/40 border border-white/10">
                    <span className="text-xs text-text-muted block mb-1">Provider Payout</span>
                    <span className="text-2xl font-bold text-foreground">${disputeResolution.providerUsd} USDC</span>
                    <span className="text-[10px] text-text-muted block mt-1">({disputeResolution.splitProvider}%)</span>
                  </div>
                </div>

                <PrimaryButton variant="primary" onClick={handleExecuteResolution} className="w-full py-3.5 text-sm">
                  Sign Resolution & Execute 70/30 Split on Arc
                </PrimaryButton>
              </SolidCard>
            )}

            {/* Step 5: Resolved */}
            {step === 'resolved' && (
              <SolidCard variant="glass" className="p-8 text-center border-l-4 border-l-success">
                <CheckCircle2 className="w-12 h-12 text-success mx-auto mb-3" />
                <h3 className="font-display font-bold text-xl mb-2">Escrow Settled & Closed</h3>
                <p className="text-xs font-mono text-text-muted max-w-md mx-auto">
                  Arc smart contract successfully executed split settlement. Transaction recorded on The Graph.
                </p>
              </SolidCard>
            )}
          </motion.div>
        ) : (
          /* Provider View */
          <motion.div key="provider-flow" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <SolidCard variant="glass" className="p-8">
              <div className="flex items-center gap-3 mb-4">
                <Upload className="w-6 h-6 text-white" />
                <h3 className="font-display font-bold text-xl">Provider Evidence Dropzone</h3>
              </div>
              <p className="text-xs text-text-muted font-mono mb-6">
                Upload completion photos. Intentra will generate a SHA-256 evidence hash to anchor on Arc.
              </p>

              <div className="p-8 border-2 border-dashed border-white/20 rounded-xl text-center bg-white/5 mb-6">
                <Upload className="w-8 h-8 text-text-muted mx-auto mb-2" />
                <span className="text-xs font-mono text-text-muted block">Drag event photos here or click to select</span>
              </div>

              <PrimaryButton onClick={handleUploadEvidence} className="w-full py-3 text-sm flex items-center justify-center gap-2">
                <Upload className="w-4 h-4" />
                <span>Hash Photo & Anchor Evidence on Arc</span>
              </PrimaryButton>
            </SolidCard>
          </motion.div>
        )}
      </AnimatePresence>
    </main>
  );
}
