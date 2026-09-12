import * as React from "react"
import { cn } from "@/lib/utils"

export interface StatusBadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  status: 'verified' | 'locked' | 'pending' | 'danger' | 'completed' | 'active' | 'disputed'
  label: string
}

export function StatusBadge({ status, label, className, ...props }: StatusBadgeProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center rounded-md px-2.5 py-1 text-xs font-mono font-medium border backdrop-blur-md transition-all",
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
      <span>{label}</span>
    </div>
  )
}
