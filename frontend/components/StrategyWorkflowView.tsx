'use client';

import { MessageSquare, Search, Shield, Zap, CheckCircle2 } from 'lucide-react';
import { STRATEGY_WORKFLOWS, type WorkflowStep } from '@/lib/strategyWorkflows';
import { cn } from '@/lib/utils';

const STEP_ICONS = [MessageSquare, Search, Shield, Zap, CheckCircle2] as const;

function StepIcon({ index }: { index: number }) {
  const Icon = STEP_ICONS[index % STEP_ICONS.length];
  return (
    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
      <Icon className="h-4 w-4" />
    </span>
  );
}

function WorkflowStepItem({
  step,
  index,
  isLast,
}: {
  step: WorkflowStep;
  index: number;
  isLast: boolean;
}) {
  return (
    <div className="flex gap-4">
      <div className="flex flex-col items-center">
        <StepIcon index={index} />
        {!isLast && <div className="w-px min-h-[28px] mt-1 bg-border" aria-hidden />}
      </div>
      <div className={cn('flex-1', !isLast && 'pb-4')}>
        <p className="text-sm font-medium text-foreground">{step.title}</p>
        <p className="text-xs text-muted-foreground mt-0.5">{step.description}</p>
      </div>
    </div>
  );
}

interface StrategyWorkflowViewProps {
  templateId: string;
  className?: string;
}

export function StrategyWorkflowView({ templateId, className }: StrategyWorkflowViewProps) {
  const steps = STRATEGY_WORKFLOWS[templateId];
  if (!steps || steps.length === 0) return null;

  return (
    <div className={cn('rounded-lg border border-border bg-card/50 p-4', className)}>
      <h3 className="text-sm font-semibold text-foreground mb-4">¿Cómo funciona esta estrategia?</h3>
      <div className="space-y-0">
        {steps.map((step, idx) => (
          <WorkflowStepItem
            key={idx}
            step={step}
            index={idx}
            isLast={idx === steps.length - 1}
          />
        ))}
      </div>
    </div>
  );
}
