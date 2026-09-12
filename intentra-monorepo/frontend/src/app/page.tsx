import Link from 'next/link';
import { PrimaryButton } from '@/components/ui/PrimaryButton';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <nav className="border-b border-border bg-surface px-6 py-4 flex justify-between items-center">
        <div className="text-xl font-display font-bold text-foreground tracking-tight">Intentra</div>
        <Link href="/dashboard/consumer">
          <PrimaryButton variant="secondary" className="px-4 py-2 text-sm">
            Connect
          </PrimaryButton>
        </Link>
      </nav>

      <main className="flex-1 flex flex-col items-center justify-center text-center px-6 py-20">
        <h1 className="max-w-4xl font-display text-5xl md:text-7xl font-bold tracking-tight text-foreground mb-6">
          AI can find a provider. <br className="hidden md:block"/> It cannot create authority.
        </h1>
        <p className="max-w-2xl text-lg md:text-xl text-text-muted mb-10">
          An AI-mediated service marketplace secured by cryptographic escrow and human verification.
        </p>
        <Link href="/dashboard/consumer">
          <PrimaryButton variant="primary" className="text-lg px-8 py-4">
            Start a Transaction
          </PrimaryButton>
        </Link>
      </main>
    </div>
  );
}
