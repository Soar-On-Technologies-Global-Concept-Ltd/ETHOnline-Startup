"use client";

import { useState, useEffect } from "react";
import { IDKitRequestWidget, orbLegacy, type RpContext } from "@worldcoin/idkit";
import { PrimaryButton } from "@/components/ui/PrimaryButton";
import { toast } from "sonner";
import { useIntentStore } from "@/store/intentStore";
import { ShieldCheck, UserCheck } from "lucide-react";

interface VerifyHumanityWidgetProps {
  action: string;
  buttonText?: string;
  onVerified?: () => void;
}

export function VerifyHumanityWidget({ 
  action, 
  buttonText = "Verify Humanity (World Selfie Check)",
  onVerified 
}: VerifyHumanityWidgetProps) {
  const [rpContext, setRpContext] = useState<RpContext | null>(null);
  const [open, setOpen] = useState(false);
  const setVerified = useIntentStore(state => state.setVerified);
  const isVerified = useIntentStore(state => state.isVerified);

  useEffect(() => {
    async function fetchSig() {
      try {
        const rpSig = await fetch("/api/rp-signature", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ action }),
        }).then((r) => r.json());

        if (rpSig.error) {
          console.error("RP Signature error:", rpSig.error);
          return;
        }

        setRpContext({
          rp_id: process.env.NEXT_PUBLIC_WORLD_ID_RP_ID || "rp_staging_default",
          nonce: rpSig.nonce || "nonce_default",
          created_at: rpSig.created_at || Math.floor(Date.now() / 1000),
          expires_at: rpSig.expires_at || Math.floor(Date.now() / 1000) + 3600,
          signature: rpSig.sig || "0x_mock_signature",
        });
      } catch (err) {
        console.error("Failed to fetch RP signature", err);
      }
    }
    fetchSig();
  }, [action]);

  const handleVerify = async (result: any) => {
    const response = await fetch("/api/verify-proof", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        rp_id: rpContext?.rp_id,
        idkitResponse: result,
      }),
    });

    if (!response.ok) {
      throw new Error("Backend verification failed");
    }
  };

  const onSuccess = () => {
    toast.success("World Selfie Check Verified!");
    setVerified(true);
    if (onVerified) onVerified();
  };

  const handleDevBypass = () => {
    toast.success("Selfie Check Verified (Dev Sandbox)");
    setVerified(true);
    if (onVerified) onVerified();
  };

  if (isVerified) {
    return (
      <div className="flex items-center justify-center gap-2 p-3 bg-success/10 border border-success/30 rounded-xl text-success font-medium text-sm">
        <ShieldCheck className="w-5 h-5" />
        <span>Verified Human (World ID)</span>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <PrimaryButton onClick={() => setOpen(true)} className="w-full flex items-center justify-center gap-2">
        <UserCheck className="w-4 h-4" />
        {buttonText}
      </PrimaryButton>

      {/* Dev fallback button for seamless hackathon testing */}
      <button
        type="button"
        onClick={handleDevBypass}
        className="text-xs text-text-muted hover:text-foreground underline w-full text-center block pt-1"
      >
        [Dev Sandbox] Bypass World Selfie Check
      </button>

      {process.env.NEXT_PUBLIC_WORLD_ID_APP_ID && rpContext && (
        <IDKitRequestWidget
          open={open}
          onOpenChange={setOpen}
          app_id={(process.env.NEXT_PUBLIC_WORLD_ID_APP_ID || "app_staging_default") as `app_${string}`}
          action={action}
          rp_context={rpContext}
          allow_legacy_proofs={true}
          preset={orbLegacy()}
          handleVerify={handleVerify}
          onSuccess={onSuccess}
        />
      )}
    </div>
  );
}
