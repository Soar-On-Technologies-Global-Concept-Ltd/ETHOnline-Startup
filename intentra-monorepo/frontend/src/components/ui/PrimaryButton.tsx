import * as React from "react"
import { cn } from "@/lib/utils"

export interface PrimaryButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger'
}

export const PrimaryButton = React.forwardRef<HTMLButtonElement, PrimaryButtonProps>(
  ({ className, variant = 'primary', ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center rounded-lg px-6 py-3 font-semibold text-white transition-all duration-200 ease-in-out hover:scale-[1.02] active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50",
          {
            "bg-primary hover:brightness-110": variant === 'primary',
            "bg-secondary hover:brightness-110": variant === 'secondary',
            "bg-danger hover:brightness-110": variant === 'danger',
          },
          className
        )}
        {...props}
      />
    )
  }
)
PrimaryButton.displayName = "PrimaryButton"
