"use client";

import { SolidCard } from "@/components/ui/SolidCard";
import { PrimaryButton } from "@/components/ui/PrimaryButton";
import { PrivyLoginButton } from "@/components/auth/PrivyLoginButton";
import { usePrivy } from "@privy-io/react-auth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function UserProfilePage() {
  const { ready, authenticated, user } = usePrivy();
  const router = useRouter();

  useEffect(() => {
    if (ready && !authenticated) {
      router.push("/");
    }
  }, [ready, authenticated, router]);

  if (!ready || !authenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center text-text-muted font-mono text-xs">
        Loading Profile...
      </div>
    );
  }

  return (
    <main className="max-w-3xl mx-auto p-6 md:p-12 min-h-screen">
      <header className="mb-10 pb-6 border-b border-white/10">
        <span className="text-xs font-mono uppercase tracking-widest text-text-muted font-medium">Account Settings</span>
        <h1 className="font-display text-2xl md:text-3xl font-bold tracking-tight mt-1">User Profile</h1>
      </header>

      <div className="space-y-6 font-mono">
        {/* Wallet & Auth Details */}
        <SolidCard variant="glass" className="p-6 rounded-lg">
          <h2 className="text-sm uppercase tracking-widest text-text-muted mb-4 font-semibold">Embedded Wallet & Authentication</h2>
          
          <div className="space-y-4 text-xs">
            <div className="py-2 border-b border-white/10">
              <span className="text-text-muted block mb-1">Email Account</span>
              <span className="font-bold text-foreground text-sm">{user?.email?.address || "Connected via Privy"}</span>
            </div>

            <div className="py-2 border-b border-white/10">
              <span className="text-text-muted block mb-1">Privy Embedded Wallet Address</span>
              <span className="font-bold text-foreground text-xs break-all bg-white/5 p-2 rounded block">
                {user?.wallet?.address || "0x1234567890abcdef1234567890abcdef12345678"}
              </span>
            </div>

            <div className="py-2">
              <span className="text-text-muted block mb-1">World ID Verification Status</span>
              <span className="inline-block px-2.5 py-1 rounded bg-success/10 text-success border border-success/30 font-semibold text-xs">
                ✓ World Selfie Check Verified
              </span>
            </div>
          </div>
        </SolidCard>

        {/* Security & Spending Policy Limits */}
        <SolidCard variant="glass" className="p-6 rounded-lg">
          <h2 className="text-sm uppercase tracking-widest text-text-muted mb-4 font-semibold">EIP-712 Spending Policy Bounds</h2>
          
          <div className="space-y-3 text-xs">
            <div className="flex justify-between items-center py-2 border-b border-white/10">
              <span className="text-text-muted">Maximum Single Transaction Cap</span>
              <span className="font-bold text-success">$150.00 USDC</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-white/10">
              <span className="text-text-muted">Network Rail</span>
              <span className="font-bold">Arc Testnet (Chain ID 50)</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-text-muted">Agent Authority Mode</span>
              <span className="font-bold text-warning">Strict Human Authorization Required</span>
            </div>
          </div>
        </SolidCard>

        {/* Sign Out Action */}
        <div className="pt-4 flex justify-end">
          <PrivyLoginButton variant="danger" />
        </div>
      </div>
    </main>
  );
}
