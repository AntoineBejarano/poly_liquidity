'use client';

import { useState } from 'react';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { ChevronDown, ChevronRight } from 'lucide-react';

interface Tag {
  tag_id: string;
  name: string;
}

interface Event {
  event_id: string;
  polymarket_event_id: string;
  market_id: string;
  market_name: string;
  start_time: string | null;
  end_time: string | null;
  state: 'UPCOMING' | 'ACTIVE' | 'FINISHED';
}

interface MarketCardProps {
  market_id: string;
  polymarket_id: string;
  name: string;
  category: string | null;
  enabled: boolean;
  tags: Tag[];
  events_count: number;
  events?: Event[];
  isConnected: boolean;
  toggling?: boolean;
  onToggle: (marketId: string, currentEnabled: boolean) => void;
  showEvents?: boolean;
}

export function MarketCard({
  market_id,
  name,
  category,
  enabled,
  tags,
  events_count,
  events = [],
  isConnected,
  toggling = false,
  onToggle,
  showEvents = false,
}: MarketCardProps) {
  const [expanded, setExpanded] = useState(false);

  const getStateColor = (state: string) => {
    switch (state) {
      case 'ACTIVE':
        return 'bg-green-100 text-green-700 border-green-200';
      case 'UPCOMING':
        return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'FINISHED':
        return 'bg-slate-100 text-slate-600 border-slate-200';
      default:
        return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  };

  return (
    <Card className="p-4 border-border">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-medium text-foreground truncate">{name}</h3>
            {category && (
              <Badge variant="outline" className="text-xs">
                {category}
              </Badge>
            )}
          </div>
          
          {tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {tags.map((tag) => (
                <Badge key={tag.tag_id} variant="secondary" className="text-xs">
                  {tag.name}
                </Badge>
              ))}
            </div>
          )}

          {showEvents && events.length > 0 && (
            <div className="mt-3">
              <button
                onClick={() => setExpanded(!expanded)}
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                {expanded ? (
                  <ChevronDown className="w-3 h-3" />
                ) : (
                  <ChevronRight className="w-3 h-3" />
                )}
                <span>{events.length} events</span>
              </button>

              {expanded && (
                <div className="mt-2 space-y-1 pl-4 border-l-2 border-border">
                  {events.map((event) => (
                    <div
                      key={event.event_id}
                      className="text-xs py-1 flex items-center justify-between"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="text-muted-foreground font-mono truncate">
                          {event.polymarket_event_id.substring(0, 20)}...
                        </div>
                        {event.start_time && event.end_time && (
                          <div className="text-muted-foreground mt-0.5">
                            {new Date(event.start_time).toLocaleString('es-ES', {
                              day: '2-digit',
                              month: '2-digit',
                              hour: '2-digit',
                              minute: '2-digit',
                            })}{' '}
                            -{' '}
                            {new Date(event.end_time).toLocaleString('es-ES', {
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </div>
                        )}
                      </div>
                      <Badge
                        variant="outline"
                        className={`ml-2 text-xs ${getStateColor(event.state)}`}
                      >
                        {event.state}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {!showEvents && events_count > 0 && (
            <div className="mt-2 text-xs text-muted-foreground">
              {events_count} events
            </div>
          )}
        </div>

        <div className="flex items-center gap-3 flex-shrink-0">
          <div className="flex flex-col items-end gap-1">
            <Switch
              checked={enabled}
              onCheckedChange={() => onToggle(market_id, enabled)}
              disabled={!isConnected || toggling}
            />
            <span className="text-xs text-muted-foreground">
              {enabled ? 'Activo' : 'Inactivo'}
            </span>
          </div>
        </div>
      </div>
    </Card>
  );
}

