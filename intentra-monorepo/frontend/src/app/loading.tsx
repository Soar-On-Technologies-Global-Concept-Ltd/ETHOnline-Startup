import { Loader2 } from "lucide-react";

export default function Loading() {
  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6">
      <Loader2 className="w-8 h-8 text-foreground animate-spin mb-4" />
      <p className="text-text-muted font-mono text-sm uppercase tracking-widest">Processing</p>
    </div>
  );
}
