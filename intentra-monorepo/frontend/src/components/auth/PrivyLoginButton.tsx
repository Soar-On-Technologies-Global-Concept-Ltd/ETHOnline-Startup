"use client";

import { useState, useRef, useEffect } from "react";
import { usePrivy } from "@privy-io/react-auth";
import { PrimaryButton } from "@/components/ui/PrimaryButton";
import { 
  FiLogOut, 
  FiCreditCard as Wallet, 
  FiChevronDown, 
  FiCopy, 
  FiCheck, 
  FiUser,
  FiExternalLink
} from "react-icons/fi";
import { toast } from "sonner";
import Link from "next/link";

interface PrivyLoginButtonProps {
  className?: string;
  variant?: 'primary' | 'secondary' | 'danger' | 'glass';
}

export function PrivyLoginButton({ className, variant = 'glass' }: PrivyLoginButtonProps) {
  const { login, logout, ready, authenticated, user } = usePrivy();
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const address = user?.wallet?.address;
  const truncatedAddress = address ? `${address.substring(0, 6)}...${address.substring(address.length - 4)}` : null;

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleCopyAddress = async () => {
    if (!address) {
      toast.error("No wallet address available");
      return;
    }
    try {
      await navigator.clipboard.writeText(address);
      setCopied(true);
      toast.success("Wallet address copied to clipboard!");
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      toast.error("Failed to copy address");
    }
  };

  if (!ready) {
    return (
      <PrimaryButton variant={variant} className={className} disabled>
        <span>Loading Auth...</span>
      </PrimaryButton>
    );
  }

  if (authenticated) {
    return (
      <div className="relative inline-block text-left" ref={dropdownRef}>
        {/* Wallet Trigger Pill */}
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-mono text-text-muted hover:text-foreground transition-all cursor-pointer select-none"
        >
          <Wallet className="w-3.5 h-3.5 text-success" />
          <span>{truncatedAddress || user?.email?.address || "Connected"}</span>
          <FiChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
        </button>

        {/* Dropdown Menu */}
        {isOpen && (
          <div className="absolute right-0 top-full mt-2 w-72 rounded-lg bg-zinc-900/95 border border-white/10 backdrop-blur-xl shadow-2xl z-50 p-3 text-xs font-mono">
            {/* User Info / Address Header */}
            <div className="p-2.5 rounded-md bg-white/5 border border-white/5 mb-2.5">
              <span className="text-[10px] uppercase tracking-wider text-text-muted block mb-1 font-semibold">
                Connected Wallet
              </span>
              <div className="text-foreground font-bold text-xs break-all leading-snug">
                {address || user?.email?.address || "No address found"}
              </div>
            </div>

            {/* Actions */}
            <div className="space-y-1">
              {/* Copy Address Button */}
              <button
                type="button"
                onClick={handleCopyAddress}
                className="w-full flex items-center justify-between px-2.5 py-2 rounded-md hover:bg-white/10 text-text-muted hover:text-foreground transition-colors cursor-pointer text-left"
              >
                <div className="flex items-center gap-2">
                  {copied ? (
                    <FiCheck className="w-3.5 h-3.5 text-success" />
                  ) : (
                    <FiCopy className="w-3.5 h-3.5 text-primary" />
                  )}
                  <span>{copied ? "Address Copied!" : "Copy Wallet Address"}</span>
                </div>
                {copied && <span className="text-[10px] text-success font-semibold">Copied</span>}
              </button>

              {/* View Profile */}
              <Link
                href="/profile"
                onClick={() => setIsOpen(false)}
                className="w-full flex items-center gap-2 px-2.5 py-2 rounded-md hover:bg-white/10 text-text-muted hover:text-foreground transition-colors"
              >
                <FiUser className="w-3.5 h-3.5 text-text-muted" />
                <span>Account Profile</span>
              </Link>

              {/* Block Explorer */}
              {address && (
                <a
                  href={`https://explorer.arc.network/address/${address}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={() => setIsOpen(false)}
                  className="w-full flex items-center justify-between px-2.5 py-2 rounded-md hover:bg-white/10 text-text-muted hover:text-foreground transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <FiExternalLink className="w-3.5 h-3.5 text-text-muted" />
                    <span>View on Explorer</span>
                  </div>
                </a>
              )}
            </div>

            <div className="h-px bg-white/10 my-2" />

            {/* Logout Button */}
            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
                logout();
              }}
              className="w-full flex items-center gap-2 px-2.5 py-2 rounded-md hover:bg-danger/10 text-danger/80 hover:text-danger transition-colors cursor-pointer text-left font-semibold"
            >
              <FiLogOut className="w-3.5 h-3.5" />
              <span>Disconnect Wallet</span>
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <PrimaryButton variant={variant} onClick={login} className={className}>
      <span>Connect Wallet</span>
    </PrimaryButton>
  );
}

