import * as React from "react";
import { SolidCard } from "@/components/ui/SolidCard";
import { cn } from "@/lib/utils";

export type TimelineStep = 'pending' | 'authorized' | 'paid' | 'evidence_submitted' | 'disputed' | 'resolved';

interface TransactionTimelineProps {
  step: TimelineStep;
  className?: string;
}

export function TransactionTimeline({ step, className }: TransactionTimelineProps) {
  const isPaidOrBeyond = step === 'paid' || step === 'evidence_submitted' || step === 'disputed' || step === 'resolved';
  const isEvidenceOrBeyond = step === 'evidence_submitted' || step === 'disputed' || step === 'resolved';
  const isDisputedOrResolved = step === 'disputed' || step === 'resolved';

  return (
    <SolidCard variant="glass" className={cn("p-3.5 rounded-md", className)}>
      <div className="flex justify-between items-center text-xs font-mono text-text-muted overflow-x-auto gap-4 py-0.5">
        <span className={step !== 'pending' ? 'text-success font-semibold' : 'text-foreground font-semibold'}>
          1. REQUESTED
        </span>
        <span>→</span>
        <span className={isPaidOrBeyond ? 'text-success font-semibold' : ''}>
          {isPaidOrBeyond ? '2. AUTHORIZED & PAID' : '2. AUTHORIZATION'}
        </span>
        <span>→</span>
        <span className={isEvidenceOrBeyond ? 'text-success font-semibold' : ''}>
          {isEvidenceOrBeyond ? '3. EVIDENCE ANCHORED' : '3. EVIDENCE'}
        </span>
        <span>→</span>
        <span className={isDisputedOrResolved ? 'text-warning font-semibold' : ''}>
          {step === 'resolved' ? '4. RESOLVED (70/30)' : step === 'disputed' ? '4. DISPUTED' : '4. FULFILLMENT'}
        </span>
      </div>
    </SolidCard>
  );
}
