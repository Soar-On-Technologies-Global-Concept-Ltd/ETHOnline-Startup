"use client";

import { useEffect } from "react";
import { PrimaryButton } from "@/components/ui/PrimaryButton";
import { FiAlertTriangle as AlertTriangle } from "react-icons/fi";
import { useRouter } from "next/navigation";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const router = useRouter();

  useEffect(() => {
    // Log the error to an error reporting service
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6 text-center">
      <AlertTriangle className="w-16 h-16 text-danger mb-6" />
      <h1 className="font-display text-4xl font-bold text-foreground mb-4">System Error</h1>
      <p className="text-text-muted max-w-md mb-8">
        An unexpected error occurred while processing your request. Please try again or return to the dashboard.
      </p>
      <div className="flex gap-4">
        <button 
          onClick={() => reset()}
          className="px-6 py-2 border border-border text-foreground rounded-md hover:bg-surface-hover transition-colors font-medium cursor-pointer"
        >
          Try Again
        </button>
        <PrimaryButton onClick={() => router.push('/')}>
          Return Home
        </PrimaryButton>
      </div>
    </div>
  );
}
