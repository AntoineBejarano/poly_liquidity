'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { SupportGraph } from '@/types/strategy';
import { cn } from '@/lib/utils';

interface StrategyDataFlowDiagramProps {
  supportGraphs: SupportGraph[];
  defaultExpanded?: boolean;
}

function formatTrigger(sg: SupportGraph): string {
  const t = sg?.trigger;
  if (!t || typeof t !== 'object') return '—';
  switch (t.type) {
    case 'timer':
      return t.interval_seconds ? `timer ${t.interval_seconds}s` : 'timer';
    case 'event_state_change':
      return 'on change';
    case 'external':
      return 'external';
    case 'always':
    default:
      return 'always';
  }
}

export function StrategyDataFlowDiagram({
  supportGraphs,
  defaultExpanded = true,
}: StrategyDataFlowDiagramProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const count = supportGraphs?.length ?? 0;

  const flowSummary =
    count > 0
      ? `${count} External Data Module${count === 1 ? '' : 's'} write to State Cache. Decision Graph reads cache and emits execution intents.`
      : 'Decision Graph reads cache and emits execution intents.';

  return (
    <div className="space-y-3">
      <button
        type="button"
        onClick={() => setExpanded((e) => !e)}
        className="flex items-center gap-2 text-foreground hover:text-foreground/90 transition-colors w-full text-left"
        aria-expanded={expanded}
      >
        {expanded ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
        )}
        <span className="text-h3">Data Flow</span>
      </button>

      {expanded && (
        <div className="space-y-4 pt-2">
          {/* Flow Summary — one sentence, reduces cognitive load */}
          <p className="text-body text-muted-foreground max-w-2xl">{flowSummary}</p>

          {/* Diagram — no outer box, more air */}
          <div className="flex flex-col gap-6 py-4">
            {/* Row 1: External Data Modules as floating pills */}
            {count > 0 && (
              <div className="flex flex-wrap gap-3 items-start">
                {supportGraphs.map((sg, i) => (
                  <div
                    key={i}
                    className="flex flex-col items-center gap-1"
                  >
                    <div className="px-3 py-1.5 rounded-full bg-muted/60 text-muted-foreground text-[13px] font-medium">
                      {sg.name}
                    </div>
                    <span className="text-helper text-[11px]">
                      {formatTrigger(sg)}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* Row 2: State Cache — infrastructure bar (no border, no shadow) */}
            <div className="flex flex-col gap-2">
              {count > 0 && (
                <div className="flex justify-center">
                  <svg width="120" height="24" className="opacity-40" style={{ color: 'hsl(var(--foreground-helper))' }}>
                    <path
                      d="M 0 12 L 60 12 M 60 12 L 120 12"
                      stroke="currentColor"
                      strokeWidth="1"
                      strokeDasharray="4 2"
                      fill="none"
                    />
                  </svg>
                </div>
              )}
              <div
                className={cn(
                  'w-full py-3 px-4 rounded-[var(--radius)]',
                  'bg-muted/30 text-center',
                  'border-0 shadow-none'
                )}
              >
                <span className="text-body text-muted-foreground">State Cache</span>
              </div>
            </div>

            {/* Row 3: Decision Graph — dominant block */}
            <div className="flex flex-col gap-2">
              <div className="flex justify-center">
                <svg width="120" height="24" className="opacity-40" style={{ color: 'hsl(var(--foreground-helper))' }}>
                  <path
                    d="M 0 12 L 60 12 M 60 12 L 120 12"
                    stroke="currentColor"
                    strokeWidth="1"
                    strokeDasharray="4 2"
                    fill="none"
                  />
                </svg>
              </div>
              <div
                className={cn(
                  'w-full py-4 px-4 rounded-[var(--radius)]',
                  'bg-muted/50',
                  'text-h2 text-foreground font-semibold text-center'
                )}
              >
                Decision Graph
              </div>
            </div>

            {/* Legend */}
            <p className="text-helper text-[11px]">dashed = data flow</p>
          </div>
        </div>
      )}
    </div>
  );
}
