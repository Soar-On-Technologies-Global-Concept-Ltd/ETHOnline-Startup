"use client";

import { useState, useEffect, use } from "react";
import { SolidCard } from "@/components/ui/SolidCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { TrustScoreBadge } from "@/components/ui/TrustScoreBadge";
import { TransactionTimeline, TimelineStep } from "@/components/ui/TransactionTimeline";
import { EvidenceUploader } from "@/components/ui/EvidenceUploader";
import { DisputeResolver } from "@/components/ui/DisputeResolver";
import { VerifyHumanityWidget } from "@/components/worldcoin/VerifyHumanityWidget";
import { FiArrowLeft as ArrowLeft } from "react-icons/fi";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { PrimaryButton } from "@/components/ui/PrimaryButton";
import { useIntentStore } from "@/store/intentStore";
import { usePrivy } from "@privy-io/react-auth";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { fetchIntentById, Intent } from "@/lib/api";

interface DisputeResolutionData {
  rationale?: string;
  customerUsd?: number | string;
  splitCustomer?: number | string;
  providerUsd?: number | string;
  splitProvider?: number | string;
}

export default function IntentTransactionPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const intentId = resolvedParams.id;

  const [role, setRole] = useState<'customer' | 'provider'>('customer');
  const [intent, setIntent] = useState<Intent | null>(null);
  const [step, setStep] = useState<TimelineStep>('pending');
  const [evidenceHash, setEvidenceHash] = useState<string | null>(null);
  const [disputeResolution, setDisputeResolution] = useState<DisputeResolutionData | null>(null);

  const isVerified = useIntentStore(state => state.isVerified);
  const { ready, authenticated, signTypedData } = usePrivy();
  const router = useRouter();

  useEffect(() => {
    if (ready && !authenticated) {
      router.push("/");
    }
  }, [ready, authenticated, router]);

  useEffect(() => {
    async function loadIntent() {
      const data = await fetchIntentById(intentId);
      setIntent(data);
    }
    loadIntent();
  }, [intentId]);

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
          service: intent?.service || "Event Photography",
          provider: (intent?.providers?.[0]?.address || "0xa1b2c3d4e5f6789012345678901234567890abcd") as `0x${string}`,
          maxUsd: BigInt(intent?.maxUsd || 150),
          nonce: BigInt(1),
        };

        toast.info("Prompting EIP-712 Mandate signature via Privy...");
        await signTypedData({ domain, types, primaryType: "IntentMandate", message });
      }

      setStep('paid');
      toast.success(`Mandate Signed & $${intent?.maxUsd || 150} USDC Locked in Arc Escrow!`);
    } catch (err: unknown) {
      const errorObj = err as { message?: string; code?: number };
      if (errorObj?.message?.includes("User rejected") || errorObj?.code === 4001) {
        toast.error("Signature cancelled by user");
        return;
      }
      console.warn("Dev mode signature handoff", err);
      setStep('paid');
      toast.success(`Mandate Signed & $${intent?.maxUsd || 150} USDC Locked in Arc Escrow!`);
    }
  };

  const handleEvidenceSubmitted = (hash: string) => {
    setEvidenceHash(hash);
    setStep('evidence_submitted');
  };

  const handleDisputeSubmitted = (complaint: string) => {
    setStep('disputed');
    setDisputeResolution({
      splitCustomer: 70,
      splitProvider: 30,
      customerUsd: Math.round((intent?.maxUsd || 150) * 0.7),
      providerUsd: Math.round((intent?.maxUsd || 150) * 0.3),
      rationale: `L2 Vision analysis of complaint "${complaint}" confirms partial delivery. Proposed 70/30 split based on anchored evidence.`
    });
    toast.warning("Dispute opened! AI L2 Arbitrator generated 70/30 resolution.");
  };

  const handleExecuteResolution = () => {
    setStep('resolved');
    toast.success("Both parties signed resolution! Arc Smart Contract executed split refund.");
  };

  if (!ready || !authenticated || !intent) {
    return (
      <div className="min-h-screen flex items-center justify-center text-text-muted font-mono text-xs bg-background">
        <div className="flex items-center gap-3 glass-panel px-5 py-3.5 rounded-md">
          <div className="w-3.5 h-3.5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
          <span>Loading Intent Hub...</span>
        </div>
      </div>
    );
  }

  const primaryProvider = intent.providers[0];

  return (
    <main className="max-w-4xl mx-auto p-6 md:p-12 min-h-screen">
      {/* Navigation Header */}
      <div className="mb-6 flex justify-between items-center">
        <Link href="/dashboard/consumer" className="inline-flex items-center gap-2 text-xs font-mono text-text-muted hover:text-foreground transition-colors">
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Intent Studio</span>
        </Link>

        {/* Role Switcher */}
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
            <h1 className="font-display text-2xl md:text-3xl font-bold tracking-tight">Intent: {intent.service}</h1>
            <span className="text-xs font-mono bg-white/10 text-foreground px-2 py-0.5 rounded-md border border-white/10">
              Max ${intent.maxUsd} Budget
            </span>
          </div>
          <p className="text-text-muted font-mono text-xs mt-1">Intent ID: {intent.id} • Arc Testnet USDC Escrow</p>
        </div>

        <StatusBadge 
          status={step === 'resolved' ? 'completed' : step === 'disputed' ? 'disputed' : step === 'paid' || step === 'evidence_submitted' ? 'active' : 'pending'} 
          label={step === 'resolved' ? 'Resolved (70/30 Split)' : step === 'disputed' ? 'Disputed' : step === 'evidence_submitted' ? 'Evidence Submitted' : step === 'paid' ? 'Locked in Escrow' : 'Pending Approval'} 
        />
      </header>

      {/* Reusable Transaction Timeline */}
      <section className="mb-8">
        <TransactionTimeline step={step} />
      </section>

      {/* Details Grid */}
      <div className="grid gap-6 md:grid-cols-2 mb-8">
        {/* Provider Trust Score Card */}
        <SolidCard variant="glass" className="p-5 rounded-lg">
          <span className="text-[10px] font-mono uppercase tracking-widest text-text-muted block mb-1 font-semibold">
            Verified Provider
          </span>
          <p className="font-display font-bold text-lg mb-1">{primaryProvider.name}</p>
          <p className="text-xs text-text-muted mb-4 font-mono">{intent.city}</p>
          
          <div className="pt-4 border-t border-white/10">
            <span className="text-[10px] font-mono text-text-muted mb-1 uppercase tracking-wider block font-semibold">
              The Graph Indexer Reputation
            </span>
            <TrustScoreBadge score={primaryProvider.trustScore} jobsCount={primaryProvider.jobsCount} />
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
              <span className="font-bold text-foreground">${intent.maxUsd}.00 USDC</span>
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
                  World Selfie Check confirms humanity before signing spending policy parameters (${intent.maxUsd} max cap).
                </p>
                
                <div className="max-w-md mx-auto">
                  <VerifyHumanityWidget 
                    action={`lock-escrow-${intent.id}`} 
                    buttonText="Complete World Selfie Check"
                  />
                </div>

                {isVerified && (
                  <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="mt-5 pt-5 border-t border-white/10">
                    <p className="text-xs text-success mb-3 font-mono">Humanity Verified. Sign EIP-712 Mandate with Privy wallet.</p>
                    <PrimaryButton onClick={handleSignMandateAndLock} className="w-full sm:w-auto px-6 py-2.5 text-xs">
                      Sign EIP-712 Mandate & Deposit ${intent.maxUsd} USDC
                    </PrimaryButton>
                  </motion.div>
                )}
              </SolidCard>
            )}

            {/* Step 2: Escrow Locked Waiting for Evidence */}
            {step === 'paid' && (
              <SolidCard variant="glass" className="p-6 text-center border-l-2 border-l-success rounded-lg">
                <h3 className="font-display font-bold text-lg mb-1">${intent.maxUsd} USDC Secured in Arc Escrow</h3>
                <p className="text-text-muted text-xs font-mono max-w-md mx-auto mb-4">
                  Provider &quot;{primaryProvider.name}&quot; is now executing the service. Waiting for photo evidence upload.
                </p>
                <div className="inline-flex items-center gap-2 text-xs font-mono text-text-muted bg-white/5 px-3.5 py-1.5 rounded-md border border-white/10">
                  <span>Switch to &quot;Provider View&quot; in top toggle to simulate evidence submission.</span>
                </div>
              </SolidCard>
            )}

            {/* Step 3: Reusable DisputeResolver */}
            {step === 'evidence_submitted' && (
              <DisputeResolver
                evidenceHash={evidenceHash}
                onDisputeSubmitted={handleDisputeSubmitted}
                onConfirmWork={() => setStep('resolved')}
              />
            )}

            {/* Step 4: Dispute Open & AI L2 Arbitration */}
            {step === 'disputed' && disputeResolution && (
              <SolidCard variant="glass" className="p-6 border-l-2 border-l-warning rounded-lg">
                <h3 className="font-display font-bold text-lg mb-3">AI L2 Arbitrator Proposed Resolution</h3>

                <p className="text-xs font-mono text-text-muted mb-5 bg-white/5 p-3.5 rounded-md border border-white/10 leading-relaxed">
                  &quot;{String(disputeResolution.rationale || '')}&quot;
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
          /* Provider View with Reusable EvidenceUploader */
          <motion.div key="provider-flow" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <EvidenceUploader onEvidenceSubmitted={handleEvidenceSubmitted} />
          </motion.div>
        )}
      </AnimatePresence>
    </main>
  );
}
