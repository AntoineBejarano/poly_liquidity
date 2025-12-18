'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Info, AlertTriangle, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ActivityLogItem {
  id: string;
  timestamp: string;
  type: 'INFO' | 'WARNING' | 'ERROR';
  message: string;
}

interface ActivityLogProps {
  logs: ActivityLogItem[];
}

export function ActivityLog({ logs }: ActivityLogProps) {
  const getIcon = (type: ActivityLogItem['type']) => {
    switch (type) {
      case 'INFO':
        return <Info className="h-4 w-4 text-blue-600" />;
      case 'WARNING':
        return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
      case 'ERROR':
        return <XCircle className="h-4 w-4 text-red-600" />;
    }
  };

  const getBadgeVariant = (type: ActivityLogItem['type']) => {
    switch (type) {
      case 'INFO':
        return 'default' as const;
      case 'WARNING':
        return 'warning' as const;
      case 'ERROR':
        return 'error' as const;
    }
  };

  if (logs.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Actividad de la Estrategia</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <p>No hay actividad registrada aún.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="flex-shrink-0">
        <CardTitle className="text-lg font-semibold">Actividad de la Estrategia</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 min-h-0">
        <ScrollArea className="h-full">
          <div className="space-y-3">
            {logs.map((log) => (
              <div key={log.id} className="flex items-start gap-3 p-3 border rounded-lg">
                <div className="flex-shrink-0 mt-0.5">
                  {getIcon(log.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant={getBadgeVariant(log.type)} className="text-xs">
                      {log.type}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {log.timestamp}
                    </span>
                  </div>
                  <div className="text-sm text-foreground">
                    {log.message}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

