"use client";

import { SolidCard } from "@/components/ui/SolidCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { PrimaryButton } from "@/components/ui/PrimaryButton";
import Link from "next/link";
import { usePrivy } from "@privy-io/react-auth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function IntentHistoryPage() {
  const { ready, authenticated } = usePrivy();
  const router = useRouter();

  useEffect(() => {
    if (ready && !authenticated) {
      router.push("/");
    }
  }, [ready, authenticated, router]);

  const history = [
    {
      id: "intent_123",
      service: "Verified Event Photography",
      provider: "Apex Photography Studio",
      maxUsd: 150,
      status: "active",
      date: "Today",
    },
    {
      id: "intent_789",
      service: "Residential Painting (Surulere)",
      provider: "Tunde Paints Ltd",
      maxUsd: 180,
      status: "completed",
      date: "3 days ago",
    },
    {
      id: "intent_999",
      service: "Catering & Event Setup",
      provider: "Lagos Culinary Services",
      maxUsd: 250,
      status: "disputed",
      date: "1 week ago",
    }
  ];

  if (!ready || !authenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center text-text-muted font-mono text-xs">
        Loading History...
      </div>
    );
  }

  return (
    <main className="max-w-4xl mx-auto p-6 md:p-12 min-h-screen">
      <header className="mb-10 pb-6 border-b border-white/10">
        <span className="text-xs font-mono uppercase tracking-widest text-text-muted font-medium">On-Chain Audit Trail</span>
        <h1 className="font-display text-2xl md:text-3xl font-bold tracking-tight mt-1">Intent & Transaction History</h1>
      </header>

      <div className="space-y-4">
        {history.map((item) => (
          <SolidCard key={item.id} variant="glass" className="p-5 rounded-lg">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 font-mono">
              <div>
                <div className="flex items-center gap-3 mb-1">
                  <h3 className="font-display font-bold text-base">{item.service}</h3>
                  <StatusBadge 
                    status={item.status === 'completed' ? 'completed' : item.status === 'disputed' ? 'disputed' : 'active'} 
                    label={item.status === 'completed' ? 'Settled' : item.status === 'disputed' ? 'Disputed (70/30)' : 'USDC Locked'} 
                  />
                </div>
                <div className="flex items-center gap-4 text-xs text-text-muted">
                  <span>Provider: {item.provider}</span>
                  <span>Date: {item.date}</span>
                </div>
              </div>

              <div className="flex items-center gap-4 w-full sm:w-auto justify-between sm:justify-end">
                <div className="text-right">
                  <span className="text-[10px] text-text-muted block">Budget Cap</span>
                  <span className="text-base font-bold text-foreground">${item.maxUsd} USDC</span>
                </div>

                <Link href={`/intent/${item.id}`}>
                  <PrimaryButton variant="secondary" className="px-4 py-2 text-xs">
                    View Audit Log
                  </PrimaryButton>
                </Link>
              </div>
            </div>
          </SolidCard>
        ))}
      </div>
    </main>
  );
}
