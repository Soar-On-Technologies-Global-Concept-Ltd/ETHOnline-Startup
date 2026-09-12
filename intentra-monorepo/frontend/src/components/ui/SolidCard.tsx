import * as React from "react"
import { cn } from "@/lib/utils"

export interface SolidCardProps extends React.HTMLAttributes<HTMLDivElement> {}

export function SolidCard({ className, ...props }: SolidCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-surface p-6 text-foreground shadow-sm",
        className
      )}
      {...props}
    />
  )
}
