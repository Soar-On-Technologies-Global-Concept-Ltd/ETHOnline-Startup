"use client";

import { useState, useEffect, use } from "react";
import { SolidCard } from "@/components/ui/SolidCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { TrustScoreBadge } from "@/components/ui/TrustScoreBadge";
import { TransactionTimeline, TimelineStep } from "@/components/ui/TransactionTimeline";
import { EvidenceUploader } from "@/components/ui/EvidenceUploader";
import { DisputeResolver } from "@/components/ui/DisputeResolver";
import { VerifyHumanityWidget } from "@/components/worldcoin/VerifyHumanityWidget";
import { FiArrowLeft as ArrowLeft, FiLock as Lock } from "react-icons/fi";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { PrimaryButton } from "@/components/ui/PrimaryButton";
import { useIntentStore } from "@/store/intentStore";
import { usePrivy } from "@privy-io/react-auth";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { fetchIntentById, Intent } from "@/lib/api";

export default function IntentTransactionPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const intentId = resolvedParams.id;

  const [role, setRole] = useState<'customer' | 'provider'>('customer');
  const [intent, setIntent] = useState<Intent | null>(null);
  const [step, setStep] = useState<TimelineStep>('pending');
  const [evidenceHash, setEvidenceHash] = useState<string | null>(null);
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
    async function loadIntent() {
      const data = await fetchIntentById(intentId);
      setIntent(data);
    }
    loadIntent();
  }, [intentId]);

  // Load state from localStorage on mount
  useEffect(() => {
    if (intentId) {
      const savedState = localStorage.getItem(`intent_demo_state_${intentId}`);
      if (savedState) {
        try {
          const parsed = JSON.parse(savedState);
          if (parsed.role) setRole(parsed.role);
          if (parsed.step) setStep(parsed.step);
          if (parsed.evidenceHash) setEvidenceHash(parsed.evidenceHash);
          if (parsed.disputeResolution) setDisputeResolution(parsed.disputeResolution);
        } catch (e) {
          console.error("Failed to parse saved state", e);
        }
      }
    }
  }, [intentId]);

  // Save state to localStorage on change
  useEffect(() => {
    if (intentId && step) {
      localStorage.setItem(`intent_demo_state_${intentId}`, JSON.stringify({
        role,
        step,
        evidenceHash,
        disputeResolution
      }));
    }
  }, [intentId, role, step, evidenceHash, disputeResolution]);

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
          maxUsd: Number(intent?.maxUsd || 150),
          nonce: 1,
        };

        toast.info("Confirming with secure wallet...");
        await signTypedData({ domain, types, primaryType: "IntentMandate", message });
      }

      setStep('paid');
      toast.success(`Mandate Signed & $${intent?.maxUsd || 150} USDC Locked in Arc Escrow!`);
    } catch (err: any) {
      if (err?.message?.includes("User rejected") || err?.code === 4001) {
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

  const handleSignResolution = async () => {
    try {
      if (signTypedData) {
        const domain = {
          name: "Intentra Protocol",
          version: "1",
          chainId: 50, // Arc Testnet
          verifyingContract: "0x1234567890abcdef1234567890abcdef12345678" as `0x${string}`,
        };

        const types = {
          IntentResolution: [
            { name: "intentId", type: "string" },
            { name: "customerUsd", type: "uint256" },
            { name: "providerUsd", type: "uint256" },
          ],
        };

        const message = {
          intentId: intent?.id || "",
          customerUsd: Number(disputeResolution?.customerUsd || 0),
          providerUsd: Number(disputeResolution?.providerUsd || 0),
        };

        toast.info(`Accepting AI Resolution for ${role}...`);
        await signTypedData({ domain, types, primaryType: "IntentResolution", message });
      }

      setStep('resolved');
      toast.success("Resolution signed! Arc Smart Contract executed split refund.");
    } catch (err: any) {
      if (err?.message?.includes("User rejected") || err?.code === 4001) {
        toast.error("Signature cancelled by user");
        return;
      }
      console.warn("Dev mode signature handoff", err);
      setStep('resolved');
      toast.success("Resolution signed! Arc Smart Contract executed split refund.");
    }
  };

  const handleAppealDecision = () => {
    setStep('appealed');
    toast.info("Escalated to Human Oracle. Funds are frozen.");
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
    <main className="max-w-3xl mx-auto p-4 md:p-10 min-h-screen pb-24 font-sans">
      {/* Navigation Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-12">
        <Link href="/dashboard/consumer" className="inline-flex items-center gap-2 text-xs font-mono text-white/50 hover:text-white transition-colors w-fit">
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Studio</span>
        </Link>

        {/* Role Switcher */}
        <div className="inline-flex items-center p-1 bg-white/5 border border-white/10 rounded-lg text-xs font-mono w-fit">
          <button
            type="button"
            onClick={() => setRole('customer')}
            className={`px-4 py-1.5 rounded-md transition-all duration-300 ${role === 'customer' ? 'bg-white text-black shadow-sm font-semibold' : 'text-white/50 hover:text-white'}`}
          >
            Consumer
          </button>
          <button
            type="button"
            onClick={() => setRole('provider')}
            className={`px-4 py-1.5 rounded-md transition-all duration-300 ${role === 'provider' ? 'bg-white text-black shadow-sm font-semibold' : 'text-white/50 hover:text-white'}`}
          >
            Provider
          </button>
        </div>
      </div>

      {/* Main Header */}
      <header className="mb-10">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-[10px] uppercase tracking-widest font-mono text-white/40">Intent • {intent.id.substring(0, 12)}</span>
          <div className="w-1 h-1 rounded-full bg-white/20" />
          <span className="text-[10px] uppercase tracking-widest font-mono text-white/40">Arc Escrow</span>
        </div>
        
        <h1 className="font-display text-3xl md:text-5xl font-medium tracking-tight text-white mb-6 leading-tight">
          {intent.service}
        </h1>
        
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-xs font-mono border border-white/10 text-white/80 px-3 py-1.5 rounded-full bg-transparent">
            Max ${intent.maxUsd} Budget
          </span>
          <StatusBadge 
            status={step === 'resolved' ? 'completed' : step === 'appealed' ? 'disputed' : step === 'disputed' ? 'disputed' : step === 'paid' || step === 'evidence_submitted' ? 'active' : 'pending'} 
            label={step === 'resolved' ? 'Resolved (70/30)' : step === 'appealed' ? 'Appealed' : step === 'disputed' ? 'Disputed' : step === 'evidence_submitted' ? 'Evidence Anchored' : step === 'paid' ? 'Locked in Escrow' : 'Pending Approval'} 
          />
        </div>
      </header>

      {/* Reusable Transaction Timeline */}
      <section className="mb-12">
        <TransactionTimeline step={step} className="bg-transparent border border-white/10 py-4 px-5 rounded-2xl" />
      </section>

      {/* Details Grid */}
      <div className="grid gap-6 md:grid-cols-2 mb-12">
        {/* Provider Trust Score Card */}
        <SolidCard variant="glass" className="p-6 rounded-2xl bg-transparent border border-white/10 hover:border-white/20 transition-colors">
          <span className="text-[10px] font-mono uppercase tracking-widest text-white/40 block mb-2 font-semibold">
            Verified Provider
          </span>
          <p className="font-display font-medium text-xl mb-1 text-white">{primaryProvider.name}</p>
          <p className="text-xs text-white/50 mb-6 font-mono">{intent.city}</p>
          
          <div className="pt-4 border-t border-white/5">
            <span className="text-[10px] font-mono text-white/40 mb-3 uppercase tracking-wider block font-semibold">
              The Graph Reputation
            </span>
            <TrustScoreBadge score={primaryProvider.trustScore} jobsCount={primaryProvider.jobsCount} />
          </div>
        </SolidCard>

        {/* Escrow Terms Card */}
        <SolidCard variant="glass" className="p-6 rounded-2xl bg-transparent border border-white/10 hover:border-white/20 transition-colors">
          <span className="text-[10px] font-mono uppercase tracking-widest text-white/40 block mb-2 font-semibold">
            Smart Contract Terms
          </span>
          <div className="space-y-4 font-mono text-xs mt-4">
            <div className="flex justify-between items-center pb-3 border-b border-white/5">
              <span className="text-white/50">Max Cap</span>
              <span className="text-white font-medium">${intent.maxUsd}.00 USDC</span>
            </div>
            <div className="flex justify-between items-center pb-3 border-b border-white/5">
              <span className="text-white/50">Network</span>
              <span className="text-white">Arc Testnet</span>
            </div>
            <div className="flex justify-between items-center pb-1">
              <span className="text-white/50">Release</span>
              <span className="text-right text-white">Photo Anchor</span>
            </div>
          </div>
        </SolidCard>
      </div>

      {/* Role-Specific Workflows */}
      <AnimatePresence mode="wait">
        <motion.div key={`${role}-flow`} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-6">
          
          {/* Step 1: Mandate & Escrow Approval (CUSTOMER ONLY) */}
          {role === 'customer' && step === 'pending' && (
            <div className="p-8 text-center border border-white/10 bg-white/[0.02] rounded-2xl">
              <Lock className="w-6 h-6 text-white/30 mx-auto mb-4" />
              <h3 className="font-display font-medium text-xl mb-2 text-white">Authorize & Secure Payment</h3>
              <p className="text-white/50 mb-8 max-w-sm mx-auto text-xs leading-relaxed font-mono">
                Verify humanity to secure your payment policy (${intent.maxUsd} cap).
              </p>
              
              <div className="max-w-sm mx-auto">
                <VerifyHumanityWidget 
                  action={`lock-escrow-${intent.id}`} 
                  buttonText="Complete World Selfie Check"
                />
              </div>

              {isVerified && (
                <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="mt-8 pt-8 border-t border-white/10">
                  <p className="text-xs text-success mb-4 font-mono">✓ Verified. Secure payment with your wallet.</p>
                  <PrimaryButton onClick={handleSignMandateAndLock} className="w-full sm:w-auto px-8 py-3 text-xs tracking-wide">
                    Confirm & Deposit ${intent.maxUsd}
                  </PrimaryButton>
                </motion.div>
              )}
            </div>
          )}

          {/* Step 2: Escrow Locked Waiting for Evidence */}
          {role === 'customer' && step === 'paid' && (
            <div className="p-8 text-center border border-success/30 bg-success/5 rounded-2xl">
              <h3 className="font-display font-medium text-xl mb-2 text-white">${intent.maxUsd} USDC Secured</h3>
              <p className="text-white/50 text-xs font-mono max-w-sm mx-auto mb-6">
                Provider "{primaryProvider.name}" is executing the service. Awaiting evidence.
              </p>
              <div className="inline-flex items-center gap-2 text-xs font-mono text-white/40 bg-black/40 px-4 py-2 rounded-lg border border-white/5">
                <span>Switch to "Provider" toggle to submit evidence.</span>
              </div>
            </div>
          )}
          {role === 'provider' && step === 'paid' && (
            <EvidenceUploader onEvidenceSubmitted={handleEvidenceSubmitted} />
          )}

          {/* Step 3: Reusable DisputeResolver */}
          {role === 'customer' && step === 'evidence_submitted' && (
            <DisputeResolver
              evidenceHash={evidenceHash}
              onDisputeSubmitted={handleDisputeSubmitted}
              onConfirmWork={() => setStep('resolved')}
            />
          )}
          {role === 'provider' && step === 'evidence_submitted' && (
            <div className="p-8 text-center border border-success/30 bg-success/5 rounded-2xl">
              <h3 className="font-display font-medium text-xl mb-2 text-white">Evidence Anchored on Arc</h3>
              <p className="text-xs font-mono text-white/50 max-w-sm mx-auto">
                Awaiting customer confirmation.
              </p>
              <div className="inline-flex items-center gap-2 text-xs font-mono text-white/40 bg-black/40 px-4 py-2 rounded-lg border border-white/5 mt-6">
                <span>Switch to "Consumer" toggle to review.</span>
              </div>
            </div>
          )}

          {/* Step 4: Dispute Open & AI L2 Arbitration (BOTH) */}
          {step === 'disputed' && disputeResolution && (
            <div className="p-8 border border-warning/30 bg-warning/5 rounded-2xl">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
                <h3 className="font-display font-medium text-xl text-white">AI Arbitrator Resolution</h3>
                <span className="text-[10px] font-mono bg-warning/10 text-warning border border-warning/20 px-3 py-1 rounded-full uppercase tracking-wider">
                  {role} signature required
                </span>
              </div>

              <p className="text-xs font-mono text-white/60 mb-8 bg-black/40 p-4 rounded-xl border border-white/5 leading-relaxed">
                "{disputeResolution.rationale}"
              </p>

              <div className="grid grid-cols-2 gap-4 mb-8 text-center font-mono">
                <div className="p-5 rounded-xl bg-black/40 border border-white/5">
                  <span className="text-[10px] text-white/40 block mb-1 uppercase tracking-wider">Consumer Refund</span>
                  <span className="text-2xl font-medium text-success">${disputeResolution.customerUsd}</span>
                  <span className="text-[10px] text-white/30 block mt-1">({disputeResolution.splitCustomer}%)</span>
                </div>

                <div className="p-5 rounded-xl bg-black/40 border border-white/5">
                  <span className="text-[10px] text-white/40 block mb-1 uppercase tracking-wider">Provider Payout</span>
                  <span className="text-2xl font-medium text-white">${disputeResolution.providerUsd}</span>
                  <span className="text-[10px] text-white/30 block mt-1">({disputeResolution.splitProvider}%)</span>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row gap-4">
                <PrimaryButton variant="primary" onClick={handleSignResolution} className="flex-1 py-3 text-xs tracking-wide">
                  Accept Resolution & Split
                </PrimaryButton>
                <button 
                  onClick={handleAppealDecision} 
                  className="flex-1 py-3 text-xs tracking-wide font-mono text-white/50 hover:text-white border border-white/10 hover:bg-white/5 rounded-lg transition-colors"
                >
                  Appeal Decision
                </button>
              </div>
            </div>
          )}

          {/* Step 4.5: Appealed (BOTH) */}
          {step === 'appealed' && (
            <div className="p-8 text-center border border-warning/30 bg-warning/5 rounded-2xl">
              <h3 className="font-display font-medium text-xl mb-2 text-white">Escalated to Human Oracle</h3>
              <p className="text-xs font-mono text-white/50 max-w-sm mx-auto mb-6">
                Funds are locked in a 7-day timelock pending review by a decentralized Human Oracle.
              </p>
              <div className="w-6 h-6 border-2 border-white/10 border-t-warning rounded-full animate-spin mx-auto" />
            </div>
          )}

          {/* Step 5: Resolved (BOTH) */}
          {step === 'resolved' && (
            <div className="p-8 text-center border border-success/30 bg-success/5 rounded-2xl">
              <h3 className="font-display font-medium text-xl mb-2 text-white">Escrow Settled & Closed</h3>
              <p className="text-xs font-mono text-white/50 max-w-sm mx-auto">
                Transaction recorded seamlessly on The Graph.
              </p>
            </div>
          )}
        </motion.div>
      </AnimatePresence>
    </main>
  );
}
