"use client";

import { useEffect } from "react";
import { SolidCard } from "@/components/ui/SolidCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { TrustScoreBadge } from "@/components/ui/TrustScoreBadge";
import { PrimaryButton } from "@/components/ui/PrimaryButton";
import Link from "next/link";
import { usePrivy } from "@privy-io/react-auth";
import { useRouter } from "next/navigation";

export default function ProviderDashboard() {
  const { ready, authenticated, user } = usePrivy();
  const router = useRouter();

  useEffect(() => {
    if (ready && !authenticated) {
      router.push("/");
    }
  }, [ready, authenticated, router]);

  const assignedJobs = [
    {
      id: "intent_123",
      service: "Event Photography",
      customer: "0x891a...4321",
      budgetUsd: 150,
      escrowStatus: "paid",
      window: "This Saturday",
    },
    {
      id: "intent_456",
      service: "Commercial Studio Shoot",
      customer: "0x7654...1098",
      budgetUsd: 300,
      escrowStatus: "completed",
      window: "Last Weekend",
    }
  ];

  if (!ready || !authenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center text-text-muted font-mono text-xs">
        Loading Provider Studio...
      </div>
    );
  }

  return (
    <main className="max-w-4xl mx-auto p-6 md:p-12 min-h-screen">
      <header className="mb-10 flex justify-between items-center pb-6 border-b border-white/10">
        <div>
          <span className="text-xs font-mono uppercase tracking-widest text-text-muted font-medium">Offerer Studio</span>
          <h1 className="font-display text-2xl md:text-3xl font-bold tracking-tight mt-1">Provider Dashboard</h1>
        </div>
        <div className="flex items-center gap-2">
          <TrustScoreBadge score={98} jobsCount={142} />
        </div>
      </header>

      {/* Provider Profile Summary */}
      <SolidCard variant="glass" className="p-6 mb-8 rounded-lg">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <span className="text-xs font-mono uppercase tracking-widest text-text-muted block mb-1">Registered Service Identity</span>
            <h2 className="font-display font-bold text-xl">Apex Photography Studio</h2>
            <p className="text-xs font-mono text-text-muted mt-1">Verified Address: {user?.wallet?.address || "0xa1b2c3d4...abcd"}</p>
          </div>
          <div className="text-right font-mono">
            <span className="text-xs text-text-muted block mb-0.5">Total Escrow Earned</span>
            <span className="text-2xl font-bold text-success">$1,450.00 USDC</span>
          </div>
        </div>
      </SolidCard>

      {/* Assigned Jobs List */}
      <section>
        <h2 className="text-xs font-mono uppercase tracking-widest text-text-muted mb-4 font-semibold">
          Active Jobs & Work Orders
        </h2>

        <div className="space-y-4">
          {assignedJobs.map((job) => (
            <SolidCard key={job.id} variant="glass" className="p-5 rounded-lg">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                  <div className="flex items-center gap-3">
                    <h3 className="font-display font-bold text-base">{job.service}</h3>
                    <StatusBadge 
                      status={job.escrowStatus === 'completed' ? 'completed' : 'active'} 
                      label={job.escrowStatus === 'completed' ? 'Settled' : 'USDC Locked'} 
                    />
                  </div>
                  <div className="flex items-center gap-4 mt-2 text-xs font-mono text-text-muted">
                    <span>Customer: {job.customer}</span>
                    <span>Timeline: {job.window}</span>
                  </div>
                </div>

                <div className="flex items-center gap-4 w-full sm:w-auto justify-between sm:justify-end">
                  <div className="text-right font-mono">
                    <span className="text-[10px] text-text-muted block">Escrow Amount</span>
                    <span className="text-base font-bold text-foreground">${job.budgetUsd} USDC</span>
                  </div>

                  <Link href={`/intent/${job.id}`}>
                    <PrimaryButton variant="primary" className="px-4 py-2 text-xs">
                      Open Job & Upload Evidence
                    </PrimaryButton>
                  </Link>
                </div>
              </div>
            </SolidCard>
          ))}
        </div>
      </section>
    </main>
  );
}
