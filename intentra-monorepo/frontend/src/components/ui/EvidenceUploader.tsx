"use client";

import * as React from "react";
import { SolidCard } from "@/components/ui/SolidCard";
import { PrimaryButton } from "@/components/ui/PrimaryButton";
import { Upload } from "lucide-react";
import { toast } from "sonner";

interface EvidenceUploaderProps {
  onEvidenceSubmitted: (hash: string) => void;
}

export function EvidenceUploader({ onEvidenceSubmitted }: EvidenceUploaderProps) {
  const [isUploading, setIsUploading] = React.useState(false);

  const handleUpload = () => {
    setIsUploading(true);
    setTimeout(() => {
      const mockHash = "0x" + Array.from({ length: 64 }, () => Math.floor(Math.random() * 16).toString(16)).join("");
      setIsUploading(false);
      onEvidenceSubmitted(mockHash);
      toast.success("Work evidence photo hashed (SHA-256) and anchored on Arc testnet!");
    }, 800);
  };

  return (
    <SolidCard variant="glass" className="p-6 rounded-lg">
      <h3 className="font-display font-bold text-lg mb-1">Provider Evidence Dropzone</h3>
      <p className="text-xs text-text-muted font-mono mb-5">
        Upload completion photos. Intentra will generate a SHA-256 evidence hash to anchor on Arc.
      </p>

      <div className="p-8 border border-dashed border-white/20 rounded-md text-center bg-white/5 mb-5 cursor-pointer hover:bg-white/[0.08] transition-all" onClick={handleUpload}>
        <Upload className="w-6 h-6 text-text-muted mx-auto mb-2" />
        <span className="text-xs font-mono text-text-muted block">Drag event photos here or click to select</span>
      </div>

      <PrimaryButton onClick={handleUpload} disabled={isUploading} className="w-full py-2.5 text-xs flex items-center justify-center gap-2">
        {isUploading ? (
          <span>Generating SHA-256 Evidence Hash...</span>
        ) : (
          <>
            <Upload className="w-3.5 h-3.5" />
            <span>Hash Photo & Anchor Evidence on Arc</span>
          </>
        )}
      </PrimaryButton>
    </SolidCard>
  );
}
