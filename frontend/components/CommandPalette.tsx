'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from 'next-themes';
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';
import {
  LineChart,
  Activity,
  TrendingUp,
  PlusCircle,
  BarChart3,
  Target,
  Settings,
  Sun,
  Moon,
  Monitor,
  Wallet,
  Shield,
  FileText,
} from 'lucide-react';

export function CommandPalette() {
  const [open, setOpen] = React.useState(false);
  const router = useRouter();
  const { setTheme } = useTheme();

  // Listen for Cmd+K or Ctrl+K
  React.useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };

    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, []);

  const runCommand = React.useCallback((command: () => void) => {
    setOpen(false);
    command();
  }, []);

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Type a command or search..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>

        <CommandGroup heading="Navigation">
          <CommandItem
            onSelect={() => runCommand(() => router.push('/dashboard/capital'))}
          >
            <LineChart className="mr-2 h-4 w-4" />
            <span>Capital Dashboard</span>
            <CommandShortcut>⌘C</CommandShortcut>
          </CommandItem>
          <CommandItem
            onSelect={() => runCommand(() => router.push('/dashboard/operations'))}
          >
            <Activity className="mr-2 h-4 w-4" />
            <span>Operations Dashboard</span>
            <CommandShortcut>⌘O</CommandShortcut>
          </CommandItem>
          <CommandItem
            onSelect={() => runCommand(() => router.push('/strategies'))}
          >
            <TrendingUp className="mr-2 h-4 w-4" />
            <span>My Strategies</span>
            <CommandShortcut>⌘S</CommandShortcut>
          </CommandItem>
          <CommandItem
            onSelect={() => runCommand(() => router.push('/markets'))}
          >
            <BarChart3 className="mr-2 h-4 w-4" />
            <span>Markets</span>
          </CommandItem>
          <CommandItem
            onSelect={() => runCommand(() => router.push('/decision-traces'))}
          >
            <FileText className="mr-2 h-4 w-4" />
            <span>Decision Traces</span>
          </CommandItem>
        </CommandGroup>

        <CommandSeparator />

        <CommandGroup heading="Actions">
          <CommandItem
            onSelect={() => runCommand(() => router.push('/strategies/new'))}
          >
            <PlusCircle className="mr-2 h-4 w-4" />
            <span>Create New Strategy</span>
            <CommandShortcut>⌘N</CommandShortcut>
          </CommandItem>
        </CommandGroup>

        <CommandSeparator />

        <CommandGroup heading="Settings">
          <CommandItem
            onSelect={() => runCommand(() => router.push('/settings/config'))}
          >
            <Settings className="mr-2 h-4 w-4" />
            <span>System Settings</span>
          </CommandItem>
          <CommandItem
            onSelect={() => runCommand(() => router.push('/risk'))}
          >
            <Shield className="mr-2 h-4 w-4" />
            <span>Risk Management</span>
          </CommandItem>
          <CommandItem
            onSelect={() => runCommand(() => router.push('/settings/wallets'))}
          >
            <Wallet className="mr-2 h-4 w-4" />
            <span>Wallets</span>
          </CommandItem>
        </CommandGroup>

        <CommandSeparator />

        <CommandGroup heading="Theme">
          <CommandItem onSelect={() => runCommand(() => setTheme('light'))}>
            <Sun className="mr-2 h-4 w-4" />
            <span>Light</span>
          </CommandItem>
          <CommandItem onSelect={() => runCommand(() => setTheme('dark'))}>
            <Moon className="mr-2 h-4 w-4" />
            <span>Dark</span>
          </CommandItem>
          <CommandItem onSelect={() => runCommand(() => setTheme('black'))}>
            <Monitor className="mr-2 h-4 w-4" />
            <span>Black (OLED)</span>
          </CommandItem>
          <CommandItem onSelect={() => runCommand(() => setTheme('system'))}>
            <Monitor className="mr-2 h-4 w-4" />
            <span>System</span>
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}

function CommandShortcut({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <span className="ml-auto text-xs text-muted-foreground">
      {children}
    </span>
  );
}
