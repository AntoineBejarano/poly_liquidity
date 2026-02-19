import * as React from "react"

import { cn } from "@/lib/utils"

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-8 w-full rounded-[var(--radius)] border border-[hsl(var(--input))] bg-background px-3 py-1.5 text-[13px] tabular-nums transition-colors",
          "placeholder:text-muted-foreground",
          "hover:border-[hsl(var(--border))]",
          "focus-visible:outline-none focus-visible:ring-[1px] focus-visible:ring-[hsl(var(--ring))] focus-visible:ring-offset-0 focus-visible:shadow-[0_0_0_3px_hsl(var(--ring)/0.12)]",
          "disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:border-[hsl(var(--input))]",
          "aria-[invalid=true]:border-[hsl(var(--error))] aria-[invalid=true]:focus-visible:ring-[hsl(var(--error))]",
          "file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

export { Input }
