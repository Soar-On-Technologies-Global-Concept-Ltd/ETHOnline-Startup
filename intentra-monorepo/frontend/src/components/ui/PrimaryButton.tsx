import * as React from "react"
import { cn } from "@/lib/utils"

export interface PrimaryButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'glass'
}

export const PrimaryButton = React.forwardRef<HTMLButtonElement, PrimaryButtonProps>(
  ({ className, variant = 'primary', ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center rounded-md px-5 py-2.5 font-medium text-xs tracking-wide transition-all duration-150 cubic-bezier(0.16, 1, 0.3, 1) active:scale-[0.98] disabled:pointer-events-none disabled:opacity-40 cursor-pointer select-none",
          {
            "bg-primary text-primary-foreground shadow-sm hover:bg-white/90": variant === 'primary',
            "bg-secondary text-foreground border border-white/10 hover:bg-surface-hover": variant === 'secondary',
            "bg-danger/90 text-white border border-danger/30 hover:bg-danger": variant === 'danger',
            "bg-white/10 text-foreground backdrop-blur-md border border-white/15 hover:bg-white/15": variant === 'glass',
          },
          className
        )}
        {...props}
      />
    )
  }
)
PrimaryButton.displayName = "PrimaryButton"
