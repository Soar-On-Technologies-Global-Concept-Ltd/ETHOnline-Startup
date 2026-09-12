"use client";

import * as React from "react";
import { SolidCard } from "@/components/ui/SolidCard";
import { PrimaryButton } from "@/components/ui/PrimaryButton";
import { toast } from "sonner";

interface DisputeResolverProps {
  evidenceHash: string | null;
  onDisputeSubmitted: (rationale: string) => void;
  onConfirmWork: () => void;
}

export function DisputeResolver({ evidenceHash, onDisputeSubmitted, onConfirmWork }: DisputeResolverProps) {
  const [complaint, setComplaint] = React.useState("");

  const handleFileDispute = () => {
    if (!complaint.trim()) {
      toast.error("Please describe your complaint");
      return;
    }
    onDisputeSubmitted(complaint);
  };

  return (
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
          value={complaint}
          onChange={(e) => setComplaint(e.target.value)}
          placeholder="e.g. Photographer left 2 hours early; only 50 event photos delivered..."
          className="w-full bg-black/40 border border-white/10 rounded-md p-2.5 text-xs text-foreground focus:outline-none font-sans"
        />
      </div>

      <div className="flex flex-col sm:flex-row gap-3 justify-end">
        <PrimaryButton variant="danger" onClick={handleFileDispute} className="px-5 py-2 text-xs">
          File Complaint & Dispute
        </PrimaryButton>

        <PrimaryButton variant="primary" onClick={onConfirmWork} className="px-5 py-2 text-xs">
          Confirm Work & Release $150
        </PrimaryButton>
      </div>
    </SolidCard>
  );
}
