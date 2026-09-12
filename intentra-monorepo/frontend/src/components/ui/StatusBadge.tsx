import * as React from "react"
import { cn } from "@/lib/utils"
import { CheckCircle2, AlertCircle, Lock, ShieldAlert, Sparkles } from "lucide-react"

export interface StatusBadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  status: 'verified' | 'locked' | 'pending' | 'danger' | 'completed' | 'active' | 'disputed'
  label: string
}

export function StatusBadge({ status, label, className, ...props }: StatusBadgeProps) {
  const Icon = (status === 'verified' || status === 'completed') 
    ? CheckCircle2 
    : (status === 'locked' || status === 'active') 
    ? Lock 
    : status === 'disputed' || status === 'danger' 
    ? ShieldAlert 
    : AlertCircle

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-3.5 py-1 text-xs font-mono font-medium border backdrop-blur-md transition-all",
        {
          "bg-success/10 text-success border-success/30": status === 'verified' || status === 'completed',
          "bg-white/10 text-foreground border-white/20": status === 'locked' || status === 'active',
          "bg-warning/10 text-warning border-warning/30": status === 'pending',
          "bg-danger/10 text-danger border-danger/30": status === 'danger' || status === 'disputed',
        },
        className
      )}
      {...props}
    >
      <Icon className="h-3.5 w-3.5" />
      <span>{label}</span>
    </div>
  )
}
