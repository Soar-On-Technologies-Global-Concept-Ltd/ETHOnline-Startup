import { SolidCard } from '@/components/ui/SolidCard';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { ShieldCheck, UserCheck } from 'lucide-react';
import Link from 'next/link';

export default function TransactionHub() {
  return (
    <div className="min-h-screen bg-background py-12 px-4 sm:px-6">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-2xl font-display font-bold text-foreground">Transaction Hub</h1>
          <Link href="/dashboard/consumer" className="text-sm text-primary hover:underline flex items-center gap-1">
            Back to Chat
          </Link>
        </div>

        <div className="space-y-6">
          {/* Top Card: The Quote */}
          <SolidCard>
            <div className="flex justify-between items-start mb-4">
              <div>
                <h2 className="text-lg font-semibold text-foreground">Interior Painting (2 Bedroom)</h2>
                <p className="text-sm text-text-muted mt-1">Provider: Tunde</p>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-primary">₦180,000</div>
                <div className="text-xs text-text-muted mt-1">~ 112.50 USDC</div>
              </div>
            </div>
            <div className="p-3 bg-surface-hover rounded-lg border border-border">
              <p className="text-sm text-text-muted">
                <strong>Scope:</strong> Full interior painting of a 2-bedroom apartment in Surulere. Work to be completed this Saturday.
              </p>
            </div>
          </SolidCard>

          {/* Middle Card: Trust Score */}
          <SolidCard className="border-secondary/30">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-full border-4 border-secondary flex items-center justify-center shrink-0">
                <span className="font-display font-bold text-xl text-secondary">98%</span>
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-foreground flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-secondary" />
                  The Graph Trust Score
                </h3>
                <p className="text-sm text-text-muted mt-1">
                  Based on 42 verifiable on-chain deliveries via Arc Testnet.
                </p>
              </div>
            </div>
          </SolidCard>

          {/* Bottom Card: Action Area */}
          <SolidCard className="bg-surface-hover text-center py-8">
            <h3 className="text-lg font-semibold text-foreground mb-2">Ready to proceed?</h3>
            <p className="text-sm text-text-muted mb-6 max-w-md mx-auto">
              Your funds will be locked in a secure smart contract. They will not be released until the work is confirmed or an AI-mediated dispute resolution is signed.
            </p>
            
            <div className="flex flex-col items-center gap-4">
              <PrimaryButton variant="secondary" className="w-full max-w-sm gap-2">
                <UserCheck className="w-5 h-5" />
                Verify Humanity & Approve
              </PrimaryButton>
              <div className="flex items-center gap-2 text-xs text-text-muted mt-2">
                <StatusBadge status="locked" label="Escrow Lock Pending" />
              </div>
            </div>
          </SolidCard>
        </div>
      </div>
    </div>
  );
}
