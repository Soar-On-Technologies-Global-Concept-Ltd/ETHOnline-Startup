"use client";

import { useState, useEffect } from "react";
import { IDKitRequestWidget, VerificationLevel, type RpContext } from "@worldcoin/idkit";
import { PrimaryButton } from "@/components/ui/PrimaryButton";
import { toast } from "sonner";
import { useIntentStore } from "@/store/intentStore";

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

  const hasRealWorldAppId = 
    process.env.NEXT_PUBLIC_WORLD_ID_APP_ID && 
    !process.env.NEXT_PUBLIC_WORLD_ID_APP_ID.includes("staging_default");

  const handleClick = () => {
    if (hasRealWorldAppId && rpContext) {
      setOpen(true);
    } else {
      // Dev Sandbox mode: auto-verify on click so it works out of the box without requiring external API keys
      toast.success("World Selfie Check Verified (Dev Sandbox Mode)");
      setVerified(true);
      if (onVerified) onVerified();
    }
  };

  if (isVerified) {
    return (
      <div className="flex items-center justify-center gap-2 p-2.5 bg-success/10 border border-success/30 rounded-md text-success font-medium text-xs">
        <span>✓ Verified Human (World ID)</span>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <PrimaryButton onClick={handleClick} className="w-full text-xs py-2.5">
        {buttonText}
      </PrimaryButton>

      {hasRealWorldAppId && rpContext && (
        <IDKitRequestWidget
          open={open}
          onOpenChange={setOpen}
          app_id={(process.env.NEXT_PUBLIC_WORLD_ID_APP_ID) as `app_${string}`}
          action={action}
          rp_context={rpContext}
          verification_level={VerificationLevel.Device}
          handleVerify={handleVerify}
          onSuccess={onSuccess}
        />
      )}
    </div>
  );
}
