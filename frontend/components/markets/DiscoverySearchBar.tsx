'use client';

import { useState, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import { Search } from 'lucide-react';

const SEARCH_DEBOUNCE_MS = 300;

interface DiscoverySearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

export function DiscoverySearchBar({
  value,
  onChange,
  placeholder = 'Buscar (btc, bitcoin, nfl...)',
  className,
}: DiscoverySearchBarProps) {
  const [localValue, setLocalValue] = useState(value);

  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  useEffect(() => {
    const t = setTimeout(() => {
      onChange(localValue);
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [localValue, onChange]);

  return (
    <div className={`relative ${className ?? ''}`}>
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
      <Input
        type="search"
        placeholder={placeholder}
        value={localValue}
        onChange={(e) => setLocalValue(e.target.value)}
        className="pl-9"
        aria-label="Buscar mercados"
      />
    </div>
  );
}
