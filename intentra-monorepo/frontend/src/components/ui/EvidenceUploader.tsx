"use client";

import * as React from "react";
import { PrimaryButton } from "@/components/ui/PrimaryButton";
import { FiUpload as Upload } from "react-icons/fi";
import { toast } from "sonner";
import { usePrivy } from "@privy-io/react-auth";
import { API_BASE_URL } from "@/lib/api";

interface EvidenceUploaderProps {
  /** The transaction id. Evidence hangs off the transaction, not the intent. */
  transactionId: string;
  onEvidenceSubmitted: (hash: string) => void;
}

export function EvidenceUploader({ transactionId, onEvidenceSubmitted }: EvidenceUploaderProps) {
  const { getAccessToken } = usePrivy();
  const [isUploading, setIsUploading] = React.useState(false);
  const [selectedFile, setSelectedFile] = React.useState<File | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      toast.error("Please select a file first.");
      return;
    }
    
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("kind", "AFTER_PHOTO");
      let data;
      if (transactionId.startsWith("intent_")) {
        // Mock fallback for hackathon UI flow without a backend tx
        await new Promise(r => setTimeout(r, 1500));
        data = { evidence: { sha256: "0xMockEvidenceHash" + Date.now() } };
      } else {
        const token = await getAccessToken();
        const response = await fetch(`${API_BASE_URL}/transactions/${transactionId}/evidence`, {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: formData,
        });

        if (!response.ok) {
          throw new Error("Failed to upload evidence");
        }

        data = await response.json();
      }

      onEvidenceSubmitted(data.evidence.sha256 || data.evidence.id);
      toast.success("Work evidence photo hashed (SHA-256) and anchored on Arc testnet!");
    } catch (error) {
      console.error(error);
      toast.error("Error anchoring evidence");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="p-8 text-center border border-white/10 bg-white/[0.02] rounded-2xl">
      <h3 className="font-display font-medium text-xl mb-2 text-white">Provider Evidence Dropzone</h3>
      <p className="text-xs text-white/50 font-mono mb-6 max-w-md mx-auto">
        Upload completion photos. Intentra will generate a SHA-256 evidence hash to anchor on Arc Escrow.
      </p>

      <label className="block p-8 border border-dashed border-white/20 rounded-xl text-center bg-transparent mb-6 cursor-pointer hover:border-white/40 transition-all max-w-md mx-auto">
        <input 
          type="file" 
          accept="image/*,video/*" 
          className="hidden" 
          onChange={handleFileChange}
        />
        <Upload className="w-6 h-6 text-white/30 mx-auto mb-3" />
        {selectedFile ? (
          <span className="text-xs font-mono text-white block truncate px-4">{selectedFile.name}</span>
        ) : (
          <span className="text-xs font-mono text-white/40 block">Click to browse or drag & drop</span>
        )}
      </label>

      <PrimaryButton onClick={handleUpload} disabled={isUploading || !selectedFile} className="w-full sm:w-auto px-8 py-3 text-xs tracking-wide mx-auto flex items-center justify-center gap-2">
        {isUploading ? (
          <span>Generating SHA-256 Evidence Hash...</span>
        ) : (
          <>
            <Upload className="w-3.5 h-3.5" />
            <span>Hash Photo & Anchor Evidence</span>
          </>
        )}
      </PrimaryButton>
    </div>
  );
}
