import * as React from "react"

import { cn } from "@/lib/utils"

const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.ComponentProps<"textarea">
>(({ className, ...props }, ref) => {
  return (
    <textarea
      className={cn(
        "flex min-h-[80px] w-full rounded-[var(--radius)] border border-[hsl(var(--input))] bg-background px-3 py-2 text-[13px] transition-colors placeholder:text-muted-foreground hover:border-[hsl(var(--border))] focus-visible:outline-none focus-visible:ring-[1px] focus-visible:ring-ring focus-visible:ring-offset-0 focus-visible:shadow-[0_0_0_3px_hsl(var(--ring)/0.12)] disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      ref={ref}
      {...props}
    />
  )
})
Textarea.displayName = "Textarea"

export { Textarea }
