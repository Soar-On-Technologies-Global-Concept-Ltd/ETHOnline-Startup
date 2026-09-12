"use client";

import { usePrivy } from "@privy-io/react-auth";
import { PrimaryButton } from "@/components/ui/PrimaryButton";
import { LogOut, Wallet } from "lucide-react";

interface PrivyLoginButtonProps {
  className?: string;
  variant?: 'primary' | 'secondary' | 'danger' | 'glass';
}

export function PrivyLoginButton({ className, variant = 'glass' }: PrivyLoginButtonProps) {
  const { login, logout, ready, authenticated, user } = usePrivy();

  if (!ready) {
    return (
      <PrimaryButton variant={variant} className={className} disabled>
        <span>Loading Auth...</span>
      </PrimaryButton>
    );
  }

  if (authenticated) {
    const address = user?.wallet?.address;
    const truncatedAddress = address ? `${address.substring(0, 6)}...${address.substring(address.length - 4)}` : null;

    return (
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white/5 border border-white/10 text-xs font-mono text-text-muted">
          <Wallet className="w-3.5 h-3.5 text-success" />
          <span>{truncatedAddress || user?.email?.address || "Connected"}</span>
        </div>
        <button
          type="button"
          onClick={logout}
          title="Sign Out"
          className="p-2 rounded-md bg-white/5 hover:bg-white/10 text-text-muted hover:text-danger border border-white/10 transition-all cursor-pointer"
        >
          <LogOut className="w-3.5 h-3.5" />
        </button>
      </div>
    );
  }

  return (
    <PrimaryButton variant={variant} onClick={login} className={className}>
      <span>Connect Wallet</span>
    </PrimaryButton>
  );
}
