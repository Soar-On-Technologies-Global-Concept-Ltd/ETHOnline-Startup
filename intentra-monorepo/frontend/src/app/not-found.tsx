import Link from 'next/link';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { ShieldAlert } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6 text-center">
      <ShieldAlert className="w-16 h-16 text-text-muted mb-6" />
      <h1 className="font-display text-6xl font-bold text-foreground mb-4">404</h1>
      <h2 className="text-2xl font-medium text-foreground mb-4">Intent Not Found</h2>
      <p className="text-text-muted max-w-md mb-8">
        The page or transaction you are looking for does not exist or has been moved.
      </p>
      <Link href="/">
        <PrimaryButton>Return to Hub</PrimaryButton>
      </Link>
    </div>
  );
}
