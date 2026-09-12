import Link from 'next/link';
import { SolidCard } from '@/components/ui/SolidCard';
import { PrimaryButton } from '@/components/ui/PrimaryButton';
import { Bot, User, Send } from 'lucide-react';

export default function ConsumerDashboard() {
  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar - 25% */}
      <aside className="w-1/4 border-r border-border bg-surface flex flex-col">
        <div className="p-4 border-b border-border">
          <h2 className="font-display font-semibold text-foreground text-lg">Active Jobs</h2>
        </div>
        <div className="p-4 flex-1 overflow-y-auto">
          <div className="p-3 mb-2 rounded-lg bg-surface-hover border border-border cursor-pointer">
            <h3 className="font-medium text-foreground text-sm">Painter in Surulere</h3>
            <p className="text-xs text-text-muted mt-1">Pending AI negotiation</p>
          </div>
        </div>
      </aside>

      {/* Main Chat Area - 75% */}
      <main className="flex-1 flex flex-col">
        <header className="p-4 border-b border-border bg-surface">
          <h1 className="font-display font-semibold text-foreground">New Intent</h1>
        </header>

        <div className="flex-1 p-6 overflow-y-auto space-y-6">
          <div className="flex items-start gap-4 max-w-3xl mx-auto w-full">
            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
              <Bot className="w-5 h-5 text-primary" />
            </div>
            <SolidCard className="bg-surface p-4 flex-1">
              <p className="text-sm">Hello. What service do you need today?</p>
            </SolidCard>
          </div>

          <div className="flex items-start gap-4 max-w-3xl mx-auto w-full flex-row-reverse">
            <div className="w-8 h-8 rounded-full bg-secondary/20 flex items-center justify-center shrink-0">
              <User className="w-5 h-5 text-secondary" />
            </div>
            <SolidCard className="bg-primary text-white p-4 flex-1">
              <p className="text-sm">Paint a 2-bedroom in Surulere under ₦180k this Saturday.</p>
            </SolidCard>
          </div>

          <div className="flex items-start gap-4 max-w-3xl mx-auto w-full">
            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
              <Bot className="w-5 h-5 text-primary" />
            </div>
            <SolidCard className="bg-surface p-4 flex-1 border-primary/20">
              <p className="text-sm mb-4">I found 3 painters. The best match is Tunde (Trust Score: 98%). The quote is ₦180k.</p>
              <Link href="/intent/123">
                <PrimaryButton variant="primary" className="w-full sm:w-auto text-sm">
                  View Contract & Fund Escrow
                </PrimaryButton>
              </Link>
            </SolidCard>
          </div>
        </div>

        <div className="p-4 bg-surface border-t border-border">
          <div className="max-w-3xl mx-auto relative">
            <input 
              type="text" 
              placeholder="Type your intent here..."
              className="w-full bg-background border border-border rounded-lg pl-4 pr-12 py-3 text-foreground placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
            <button className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-primary hover:bg-primary/10 rounded-md transition-colors">
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
