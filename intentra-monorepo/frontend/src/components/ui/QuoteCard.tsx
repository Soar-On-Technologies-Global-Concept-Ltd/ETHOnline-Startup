import * as React from "react";
import { SolidCard } from "@/components/ui/SolidCard";
import { PrimaryButton } from "@/components/ui/PrimaryButton";
import { TrustScoreBadge } from "@/components/ui/TrustScoreBadge";
import Link from "next/link";
import { ProviderQuote } from "@/lib/api";

interface QuoteCardProps {
  provider: ProviderQuote;
  intentId: string;
}

export function QuoteCard({ provider, intentId }: QuoteCardProps) {
  return (
    <SolidCard
      variant={provider.isRecommended ? "glass" : "solid"}
      className={`p-5 rounded-lg transition-all ${
        provider.isRecommended ? 'border-white/30 bg-white/[0.06]' : 'opacity-80'
      }`}
    >
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-display font-bold text-base">{provider.name}</h3>
            {provider.isRecommended && (
              <span className="text-[10px] font-mono uppercase tracking-wider bg-white text-black px-2 py-0.5 rounded-sm font-semibold">
                AI Pick #1
              </span>
            )}
          </div>
          <div className="mt-1.5">
            <TrustScoreBadge score={provider.trustScore} jobsCount={provider.jobsCount} />
          </div>
        </div>

        <div className="flex items-center gap-4 w-full sm:w-auto justify-between sm:justify-end">
          <div className="text-right">
            <span className="text-[10px] font-mono text-text-muted block">Quoted Price</span>
            <span className="text-lg font-display font-bold">${provider.quoteUsd} USD</span>
          </div>

          <Link href={`/intent/${intentId}`}>
            <PrimaryButton variant={provider.isRecommended ? "primary" : "secondary"} className="px-4 py-2 text-xs">
              Select & Lock Escrow
            </PrimaryButton>
          </Link>
        </div>
      </div>
    </SolidCard>
  );
}
