import * as React from "react"

import { cn } from "@/lib/utils"

const Panel = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "rounded-xl border bg-card text-card-foreground shadow-sm p-3",
      className
    )}
    {...props}
  />
))
Panel.displayName = "Panel"

export { Panel }

