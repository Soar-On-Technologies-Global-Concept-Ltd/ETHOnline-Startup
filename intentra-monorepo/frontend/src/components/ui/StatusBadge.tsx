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
        "inline-flex items-center rounded-md px-2.5 py-1 text-xs font-mono font-medium border backdrop-blur-md transition-all bg-transparent",
        {
          "text-success border-success/50": status === 'verified' || status === 'completed',
          "text-foreground border-white/20": status === 'locked' || status === 'active',
          "text-warning border-warning/50": status === 'pending',
          "text-danger border-danger/50": status === 'danger' || status === 'disputed',
        },
        className
      )}
      {...props}
    >
      <span>{label}</span>
    </div>
  )
}
