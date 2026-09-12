"use client";

import { PrimaryButton } from "@/components/ui/PrimaryButton";
import { SolidCard } from "@/components/ui/SolidCard";
import { Bot, User, ArrowRight } from "lucide-react";
import Link from "next/link";
import { TypingEffect } from "@/components/ui/TypingEffect";
import { motion } from "framer-motion";
import { usePrivy } from "@privy-io/react-auth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function ConsumerDashboard() {
  const { ready, authenticated } = usePrivy();
  const router = useRouter();

  useEffect(() => {
    if (ready && !authenticated) {
      router.push("/");
    }
  }, [ready, authenticated, router]);

  if (!ready || !authenticated) {
    return <div className="min-h-screen flex items-center justify-center text-text-muted">Loading Secure Environment...</div>;
  }

  return (
    <main className="max-w-4xl mx-auto p-6 md:p-12 min-h-screen">
      <header className="mb-12">
        <h1 className="font-display text-4xl font-bold mb-4">What do you need done?</h1>
        <p className="text-text-muted text-lg">Intentra AI will find the best provider, negotiate the terms, and secure the funds.</p>
      </header>

      <div className="space-y-6 mb-8">
        {/* User Intent Bubble */}
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="flex gap-4 max-w-2xl"
        >
          <div className="w-8 h-8 rounded-full bg-secondary/20 flex items-center justify-center shrink-0">
            <User className="w-5 h-5 text-secondary" />
          </div>
          <SolidCard className="bg-primary text-primary-foreground p-4 flex-1">
            <p className="text-sm">Paint a 2-bedroom in Surulere under ₦180k this Saturday.</p>
          </SolidCard>
        </motion.div>

        {/* AI Response Bubble */}
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.3 }}
          className="flex gap-4 max-w-2xl ml-auto flex-row-reverse"
        >
          <div className="w-8 h-8 rounded-full bg-surface border border-border flex items-center justify-center shrink-0">
            <Bot className="w-5 h-5 text-foreground" />
          </div>
          <SolidCard className="bg-surface p-4 flex-1">
            <p className="text-sm text-foreground">
              <TypingEffect text="I found 3 highly-rated painters in Surulere. 'Tunde Paints' has a 98% on-chain trust score and agreed to ₦160k for this Saturday." speed={15} />
            </p>
          </SolidCard>
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, delay: 2.5 }}
      >
        <Link href="/intent/123">
          <PrimaryButton className="w-full sm:w-auto">
            Review Quote & Escrow <ArrowRight className="w-4 h-4 ml-2" />
          </PrimaryButton>
        </Link>
      </motion.div>
    </main>
  );
}
