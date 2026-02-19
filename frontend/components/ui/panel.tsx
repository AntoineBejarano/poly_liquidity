import * as React from "react"

import { cn } from "@/lib/utils"

const Panel = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "rounded-[var(--radius-lg)] bg-card text-card-foreground shadow-premium-sm p-4",
      "border border-[hsl(var(--border-subtle,var(--border)))]/60",
      className
    )}
    {...props}
  />
))
Panel.displayName = "Panel"

export { Panel }

