import * as React from "react"
import { cn } from "@/lib/utils"
import { CheckCircle2, AlertCircle, Lock } from "lucide-react"

export interface StatusBadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  status: 'verified' | 'locked' | 'pending' | 'danger'
  label: string
}

export function StatusBadge({ status, label, className, ...props }: StatusBadgeProps) {
  const Icon = status === 'verified' ? CheckCircle2 : status === 'locked' ? Lock : AlertCircle

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium",
        {
          "bg-success/10 text-success": status === 'verified',
          "bg-warning/10 text-warning": status === 'locked' || status === 'pending',
          "bg-danger/10 text-danger": status === 'danger',
        },
        className
      )}
      {...props}
    >
      <Icon className="h-4 w-4" />
      {label}
    </div>
  )
}
