import * as React from "react"
import { cn } from "@/lib/utils"

export interface SolidCardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'solid' | 'glass' | 'interactive';
}

export function SolidCard({ className, variant = 'glass', ...props }: SolidCardProps) {
  return (
    <div
      className={cn(
        "rounded-lg transition-all duration-200",
        {
          "glass-card p-6 text-foreground": variant === 'glass',
          "bg-surface border border-border p-6 text-foreground": variant === 'solid',
          "glass-card p-6 text-foreground hover:border-white/20 hover:shadow-lg cursor-pointer active:scale-[0.99]": variant === 'interactive',
        },
        className
      )}
      {...props}
    />
  )
}
