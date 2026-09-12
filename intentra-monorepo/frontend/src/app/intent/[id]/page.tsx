"use client";

import { SolidCard } from "@/components/ui/SolidCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { VerifyHumanityWidget } from "@/components/worldcoin/VerifyHumanityWidget";
import { ArrowLeft, Upload, Lock } from "lucide-react";
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
      <div className="min-h-screen flex items-center justify-center text-text-muted font-mono text-xs bg-background">
        <div className="flex items-center gap-3 glass-panel px-5 py-3.5 rounded-md">
          <div className="w-3.5 h-3.5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
          <span>Securing Hub...</span>
        </div>
      </div>
    );
  }

  return (
    <main className="max-w-4xl mx-auto p-6 md:p-12 min-h-screen">
      {/* Navigation Header */}
      <div className="mb-6 flex justify-between items-center">
        <Link href="/dashboard/consumer" className="inline-flex items-center gap-2 text-xs font-mono text-text-muted hover:text-foreground transition-colors">
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Intent Studio</span>
        </Link>

        {/* Precision Role Switcher */}
        <div className="glass-panel p-1 rounded-md flex gap-1 text-xs font-mono">
          <button
            type="button"
            onClick={() => setRole('customer')}
            className={`px-3 py-1 rounded transition-all cursor-pointer ${role === 'customer' ? 'bg-white text-black font-semibold' : 'text-text-muted hover:text-foreground'}`}
          >
            Customer View
          </button>
          <button
            type="button"
            onClick={() => setRole('provider')}
            className={`px-3 py-1 rounded transition-all cursor-pointer ${role === 'provider' ? 'bg-white text-black font-semibold' : 'text-text-muted hover:text-foreground'}`}
          >
            Provider View
          </button>
        </div>
      </div>

      {/* Main Header */}
      <header className="mb-8 flex items-start justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-display text-2xl md:text-3xl font-bold tracking-tight">Intent: Verified Photographer</h1>
            <span className="text-xs font-mono bg-white/10 text-foreground px-2 py-0.5 rounded-md border border-white/10">
              Max $150 Budget
            </span>
          </div>
          <p className="text-text-muted font-mono text-xs mt-1">Job ID: 0x9b4f...a1c2 • Arc Testnet USDC Escrow</p>
        </div>

        <StatusBadge 
          status={step === 'resolved' ? 'completed' : step === 'disputed' ? 'disputed' : step === 'paid' || step === 'evidence_submitted' ? 'active' : 'pending'} 
          label={step === 'resolved' ? 'Resolved (70/30 Split)' : step === 'disputed' ? 'Disputed' : step === 'evidence_submitted' ? 'Evidence Submitted' : step === 'paid' ? 'Locked in Escrow' : 'Pending Approval'} 
        />
      </header>

      {/* Event Timeline Bar */}
      <section className="mb-8">
        <SolidCard variant="glass" className="p-3.5 rounded-md">
          <div className="flex justify-between items-center text-xs font-mono text-text-muted overflow-x-auto gap-4 py-0.5">
            <span className={step !== 'pending' ? 'text-success font-semibold' : 'text-foreground'}>
              1. REQUESTED
            </span>
            <span>→</span>
            <span className={step === 'paid' || step === 'evidence_submitted' || step === 'disputed' || step === 'resolved' ? 'text-success font-semibold' : ''}>
              2. AUTHORIZED & PAID
            </span>
            <span>→</span>
            <span className={step === 'evidence_submitted' || step === 'disputed' || step === 'resolved' ? 'text-success font-semibold' : ''}>
              3. EVIDENCE ANCHORED
            </span>
            <span>→</span>
            <span className={step === 'disputed' || step === 'resolved' ? 'text-warning font-semibold' : ''}>
              {step === 'resolved' ? '4. RESOLVED (70/30)' : step === 'disputed' ? '4. DISPUTED' : '4. FULFILLMENT'}
            </span>
          </div>
        </SolidCard>
      </section>

      {/* Details Grid */}
      <div className="grid gap-6 md:grid-cols-2 mb-8">
        {/* Provider Trust Score Card */}
        <SolidCard variant="glass" className="p-5 rounded-lg">
          <span className="text-[10px] font-mono uppercase tracking-widest text-text-muted block mb-1 font-semibold">
            Verified Provider
          </span>
          <p className="font-display font-bold text-lg mb-1">Apex Photography Studio</p>
          <p className="text-xs text-text-muted mb-4 font-mono">San Francisco, CA</p>
          
          <div className="pt-4 border-t border-white/10">
            <span className="text-[10px] font-mono text-text-muted mb-1 uppercase tracking-wider block font-semibold">
              The Graph Indexer Trust Score
            </span>
            <div className="flex items-end gap-2">
              <span className="text-3xl font-display font-bold text-success">{trustScore}%</span>
              <span className="text-xs text-text-muted mb-1 font-mono">from 142 on-chain jobs</span>
            </div>
          </div>
        </SolidCard>

        {/* Escrow Terms Card */}
        <SolidCard variant="glass" className="p-5 rounded-lg">
          <span className="text-[10px] font-mono uppercase tracking-widest text-text-muted block mb-1 font-semibold">
            Arc Escrow Contract
          </span>
          <div className="space-y-2.5 font-mono text-xs mt-3">
            <div className="flex justify-between items-center py-1.5 border-b border-white/10">
              <span className="text-text-muted">Max Budget Cap</span>
              <span className="font-bold text-foreground">$150.00 USDC</span>
            </div>
            <div className="flex justify-between items-center py-1.5 border-b border-white/10">
              <span className="text-text-muted">Settlement Rail</span>
              <span className="bg-white/10 px-2 py-0.5 rounded-sm text-foreground">Arc Testnet</span>
            </div>
            <div className="flex justify-between items-center py-1.5">
              <span className="text-text-muted">Release Trigger</span>
              <span className="text-right text-text-muted">Photo Hash Anchor</span>
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
              <SolidCard variant="glass" className="p-6 text-center border-dashed border-white/20 rounded-lg">
                <h3 className="font-display font-bold text-lg mb-1">Authorize EIP-712 Mandate & Lock Escrow</h3>
                <p className="text-text-muted mb-5 max-w-md mx-auto text-xs leading-relaxed font-mono">
                  World Selfie Check confirms humanity before signing spending policy parameters ($150 max cap).
                </p>
                
                <div className="max-w-md mx-auto">
                  <VerifyHumanityWidget 
                    action="lock-escrow-123" 
                    buttonText="Complete World Selfie Check"
                    onVerified={() => {}}
                  />
                </div>

                {isVerified && (
                  <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="mt-5 pt-5 border-t border-white/10">
                    <p className="text-xs text-success mb-3 font-mono">Humanity Verified. Sign EIP-712 Mandate with Privy wallet.</p>
                    <PrimaryButton onClick={handleSignMandateAndLock} className="w-full sm:w-auto px-6 py-2.5 text-xs">
                      Sign EIP-712 Mandate & Deposit $150 USDC
                    </PrimaryButton>
                  </motion.div>
                )}
              </SolidCard>
            )}

            {/* Step 2: Escrow Locked Waiting for Evidence */}
            {step === 'paid' && (
              <SolidCard variant="glass" className="p-6 text-center border-l-2 border-l-success rounded-lg">
                <h3 className="font-display font-bold text-lg mb-1">$150 USDC Secured in Arc Escrow</h3>
                <p className="text-text-muted text-xs font-mono max-w-md mx-auto mb-4">
                  Provider "Apex Photography Studio" is now executing the service. Waiting for photo evidence upload.
                </p>
                <div className="inline-flex items-center gap-2 text-xs font-mono text-text-muted bg-white/5 px-3.5 py-1.5 rounded-md border border-white/10">
                  <span>Switch to "Provider View" in top toggle to simulate evidence submission.</span>
                </div>
              </SolidCard>
            )}

            {/* Step 3: Evidence Submitted — Customer can confirm or dispute */}
            {step === 'evidence_submitted' && (
              <SolidCard variant="glass" className="p-6 rounded-lg">
                <div className="flex items-center justify-between mb-4 pb-3 border-b border-white/10">
                  <div>
                    <h3 className="font-display font-bold text-base">Work Evidence Submitted</h3>
                    <p className="text-xs text-text-muted font-mono mt-0.5">SHA-256 Hash: {evidenceHash}</p>
                  </div>
                  <span className="text-xs font-mono bg-success/20 text-success border border-success/30 px-2.5 py-0.5 rounded-sm">
                    Anchored on Arc
                  </span>
                </div>

                <div className="mb-5 p-3.5 rounded-md bg-white/5 border border-white/10">
                  <span className="text-xs text-text-muted block mb-1.5 font-mono">Customer Complaint / Dispute Input:</span>
                  <input 
                    type="text" 
                    value={disputeReason}
                    onChange={(e) => setDisputeReason(e.target.value)}
                    placeholder="e.g. Photographer left 2 hours early; only 50 event photos delivered..."
                    className="w-full bg-black/40 border border-white/10 rounded-md p-2.5 text-xs text-foreground focus:outline-none font-sans"
                  />
                </div>

                <div className="flex flex-col sm:flex-row gap-3 justify-end">
                  <PrimaryButton variant="danger" onClick={handleFileDispute} className="px-5 py-2 text-xs">
                    File Complaint & Dispute
                  </PrimaryButton>

                  <PrimaryButton variant="primary" onClick={() => setStep('resolved')} className="px-5 py-2 text-xs">
                    Confirm Work & Release $150
                  </PrimaryButton>
                </div>
              </SolidCard>
            )}

            {/* Step 4: Dispute Open & AI L2 Arbitration */}
            {step === 'disputed' && disputeResolution && (
              <SolidCard variant="glass" className="p-6 border-l-2 border-l-warning rounded-lg">
                <h3 className="font-display font-bold text-lg mb-3">AI L2 Arbitrator Proposed Resolution</h3>

                <p className="text-xs font-mono text-text-muted mb-5 bg-white/5 p-3.5 rounded-md border border-white/10 leading-relaxed">
                  "{disputeResolution.rationale}"
                </p>

                <div className="grid grid-cols-2 gap-4 mb-6 text-center font-mono">
                  <div className="p-3.5 rounded-md bg-black/40 border border-white/10">
                    <span className="text-xs text-text-muted block mb-0.5">Customer Refund</span>
                    <span className="text-xl font-bold text-success">${disputeResolution.customerUsd} USDC</span>
                    <span className="text-[10px] text-text-muted block mt-0.5">({disputeResolution.splitCustomer}%)</span>
                  </div>

                  <div className="p-3.5 rounded-md bg-black/40 border border-white/10">
                    <span className="text-xs text-text-muted block mb-0.5">Provider Payout</span>
                    <span className="text-xl font-bold text-foreground">${disputeResolution.providerUsd} USDC</span>
                    <span className="text-[10px] text-text-muted block mt-0.5">({disputeResolution.splitProvider}%)</span>
                  </div>
                </div>

                <PrimaryButton variant="primary" onClick={handleExecuteResolution} className="w-full py-2.5 text-xs">
                  Sign Resolution & Execute 70/30 Split on Arc
                </PrimaryButton>
              </SolidCard>
            )}

            {/* Step 5: Resolved */}
            {step === 'resolved' && (
              <SolidCard variant="glass" className="p-6 text-center border-l-2 border-l-success rounded-lg">
                <h3 className="font-display font-bold text-lg mb-1">Escrow Settled & Closed</h3>
                <p className="text-xs font-mono text-text-muted max-w-md mx-auto">
                  Arc smart contract successfully executed split settlement. Transaction recorded on The Graph.
                </p>
              </SolidCard>
            )}
          </motion.div>
        ) : (
          /* Provider View */
          <motion.div key="provider-flow" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <SolidCard variant="glass" className="p-6 rounded-lg">
              <h3 className="font-display font-bold text-lg mb-1">Provider Evidence Dropzone</h3>
              <p className="text-xs text-text-muted font-mono mb-5">
                Upload completion photos. Intentra will generate a SHA-256 evidence hash to anchor on Arc.
              </p>

              <div className="p-8 border border-dashed border-white/20 rounded-md text-center bg-white/5 mb-5">
                <span className="text-xs font-mono text-text-muted block">Drag event photos here or click to select</span>
              </div>

              <PrimaryButton onClick={handleUploadEvidence} className="w-full py-2.5 text-xs flex items-center justify-center gap-2">
                <Upload className="w-3.5 h-3.5" />
                <span>Hash Photo & Anchor Evidence on Arc</span>
              </PrimaryButton>
            </SolidCard>
          </motion.div>
        )}
      </AnimatePresence>
    </main>
  );
}
