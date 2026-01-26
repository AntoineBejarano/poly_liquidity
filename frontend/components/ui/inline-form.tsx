'use client';

import { Label } from './label';
import { InfoTooltip } from './info-tooltip';
import { cn } from '@/lib/utils';

interface InlineFormProps {
  label: string;
  tooltip?: string;
  tooltipTitle?: string;
  input: React.ReactNode;
  error?: string;
  className?: string;
}

export function InlineForm({ label, tooltip, tooltipTitle, input, error, className }: InlineFormProps) {
  return (
    <div className={cn("space-y-1.5", className)}>
      <div className="flex items-center gap-1">
        <Label className="text-[13px]">{label}</Label>
        {tooltip && <InfoTooltip content={tooltip} title={tooltipTitle} />}
      </div>
      {input}
      {error && <p className="text-[11px] text-destructive">{error}</p>}
    </div>
  );
}

