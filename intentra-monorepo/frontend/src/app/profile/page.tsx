"use client";

import { SolidCard } from "@/components/ui/SolidCard";
import { PrimaryButton } from "@/components/ui/PrimaryButton";
import { PrivyLoginButton } from "@/components/auth/PrivyLoginButton";
import { FiCheck } from "react-icons/fi";
import { usePrivy } from "@privy-io/react-auth";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { fetchMyProviderProfile, onboardProvider, ProviderProfile } from "@/lib/api";

export default function UserProfilePage() {
  const { ready, authenticated, user, getAccessToken } = usePrivy();
  const router = useRouter();

  const [providerProfile, setProviderProfile] = useState<ProviderProfile | null>(null);
  const [isLoadingProfile, setIsLoadingProfile] = useState(true);

  // Form State
  const [trade, setTrade] = useState("");
  const [areas, setAreas] = useState("");
  const [rate, setRate] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (ready && !authenticated) {
      router.push("/");
    }
  }, [ready, authenticated, router]);

  useEffect(() => {
    async function loadProfile() {
      if (ready && authenticated) {
        try {
          const token = await getAccessToken();
          if (token) {
            const profile = await fetchMyProviderProfile(token);
            setProviderProfile(profile);
          }
        } catch (e) {
          console.error(e);
        } finally {
          setIsLoadingProfile(false);
        }
      }
    }
    loadProfile();
  }, [ready, authenticated, getAccessToken]);

  const handleOnboard = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const token = await getAccessToken();
      if (!token) return;
      const data = {
        trade,
        areas: areas.split(",").map(a => a.trim()).filter(Boolean),
        base_rate_minor: Math.floor(parseFloat(rate) * 100) // Convert to cents/kobo
      };
      const newProfile = await onboardProvider(token, data);
      if (newProfile) {
        setProviderProfile(newProfile);
      }
    } catch(err) {
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!ready || !authenticated || isLoadingProfile) {
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
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-success/10 text-success border border-success/30 font-semibold text-xs">
                <FiCheck className="w-3.5 h-3.5" />
                <span>World Selfie Check Verified</span>
              </span>
            </div>
          </div>
        </SolidCard>

        {/* Provider Profile Section */}
        {providerProfile ? (
          <SolidCard variant="glass" className="p-6 rounded-lg border-primary/20">
            <h2 className="text-sm uppercase tracking-widest text-text-muted mb-4 font-semibold text-primary">Provider Profile (Active)</h2>
            <div className="space-y-3 text-xs">
              <div className="flex justify-between items-center py-2 border-b border-white/10">
                <span className="text-text-muted">Primary Trade / Service</span>
                <span className="font-bold">{providerProfile.trade}</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-white/10">
                <span className="text-text-muted">Service Locations</span>
                <span className="font-bold">{providerProfile.areas.join(", ") || "Global"}</span>
              </div>
              <div className="flex justify-between items-center py-2">
                <span className="text-text-muted">Base Hourly Rate</span>
                <span className="font-bold text-success">${(providerProfile.base_rate_minor / 100).toFixed(2)}</span>
              </div>
            </div>
          </SolidCard>
        ) : (
          <SolidCard variant="glass" className="p-6 rounded-lg">
            <h2 className="text-sm uppercase tracking-widest text-text-muted mb-4 font-semibold">Become a Provider</h2>
            <p className="text-xs text-text-muted mb-6">Register your service identity to start accepting smart-contract escrows.</p>
            
            <form onSubmit={handleOnboard} className="space-y-4">
              <div>
                <label className="block text-xs text-text-muted mb-1">Primary Trade (e.g. Photography, Plumbing)</label>
                <input 
                  type="text" 
                  value={trade}
                  onChange={e => setTrade(e.target.value)}
                  className="w-full bg-background border border-border rounded px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary"
                  required
                />
              </div>
              <div>
                <label className="block text-xs text-text-muted mb-1">Service Locations (Comma separated)</label>
                <input 
                  type="text" 
                  value={areas}
                  onChange={e => setAreas(e.target.value)}
                  placeholder="San Francisco, New York"
                  className="w-full bg-background border border-border rounded px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary"
                  required
                />
              </div>
              <div>
                <label className="block text-xs text-text-muted mb-1">Base Hourly Rate (USD)</label>
                <input 
                  type="number" 
                  step="0.01"
                  value={rate}
                  onChange={e => setRate(e.target.value)}
                  placeholder="150.00"
                  className="w-full bg-background border border-border rounded px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary"
                  required
                />
              </div>
              <div className="pt-2">
                <PrimaryButton type="submit" disabled={isSubmitting} className="w-full justify-center">
                  {isSubmitting ? "Registering on Ledger..." : "Register Service Identity"}
                </PrimaryButton>
              </div>
            </form>
          </SolidCard>
        )}

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
