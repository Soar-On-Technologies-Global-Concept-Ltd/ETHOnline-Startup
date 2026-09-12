"use client";

import { useState, useEffect } from "react";
import { IDKitRequestWidget, orbLegacy, type RpContext } from "@worldcoin/idkit";
import { PrimaryButton } from "@/components/ui/PrimaryButton";
import { toast } from "sonner";
import { useIntentStore } from "@/store/intentStore";

export function VerifyHumanityWidget({ action }: { action: string }) {
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
          rp_id: process.env.NEXT_PUBLIC_WORLD_ID_RP_ID || "",
          nonce: rpSig.nonce,
          created_at: rpSig.created_at,
          expires_at: rpSig.expires_at,
          signature: rpSig.sig,
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
    toast.success("Humanity Verified Successfully!");
    setVerified(true);
  };

  if (isVerified) {
    return (
      <PrimaryButton variant="secondary" className="w-full" disabled>
        ✓ Humanity Verified
      </PrimaryButton>
    );
  }

  // If env vars or RP context is missing, show a fallback or disabled state
  if (!process.env.NEXT_PUBLIC_WORLD_ID_APP_ID || !rpContext) {
    return (
      <PrimaryButton disabled className="w-full opacity-50 cursor-not-allowed">
        Loading Verification...
      </PrimaryButton>
    );
  }

  return (
    <>
      <PrimaryButton onClick={() => setOpen(true)} className="w-full">
        Verify Humanity
      </PrimaryButton>
      <IDKitRequestWidget
        open={open}
        onOpenChange={setOpen}
        app_id={process.env.NEXT_PUBLIC_WORLD_ID_APP_ID}
        action={action}
        rp_context={rpContext}
        allow_legacy_proofs={true}
        preset={orbLegacy()}
        handleVerify={handleVerify}
        onSuccess={onSuccess}
      />
    </>
  );
}
