import { cn } from '@/lib/utils';

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular';
  width?: string | number;
  height?: string | number;
}

/**
 * Componente Skeleton para mostrar placeholders durante la carga inicial.
 * 
 * Usado en lugar de spinners para una mejor UX.
 */
export function Skeleton({
  className,
  variant = 'rectangular',
  width,
  height,
}: SkeletonProps) {
  const baseClasses = 'animate-pulse bg-muted rounded';
  
  const variantClasses = {
    text: 'h-4',
    circular: 'rounded-full',
    rectangular: 'rounded',
  };

  const style: React.CSSProperties = {};
  if (width) style.width = typeof width === 'number' ? `${width}px` : width;
  if (height) style.height = typeof height === 'number' ? `${height}px` : height;

  return (
    <div
      className={cn(baseClasses, variantClasses[variant], className)}
      style={style}
    />
  );
}

/**
 * Skeleton para una tarjeta completa
 */
export function CardSkeleton() {
  return (
    <div className="space-y-4 p-6 border rounded-lg">
      <Skeleton variant="text" width="60%" />
      <Skeleton variant="text" width="80%" />
      <Skeleton variant="text" width="40%" />
    </div>
  );
}

/**
 * Skeleton para una tabla con alturas fijas para prevenir layout shift.
 * 
 * Alturas fijas:
 * - Header: 40px (h-10)
 * - Rows: 48px (h-12)
 * 
 * Estas dimensiones coinciden con el renderizado típico de tablas.
 */
export function TableSkeleton({ rows = 5, columns = 3 }: { rows?: number; columns?: number }) {
  return (
    <div className="space-y-3">
      {/* Header - altura fija 40px */}
      <div className="flex gap-4 h-10">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={`header-${i}`} variant="text" width="100%" height={40} />
        ))}
      </div>
      {/* Rows - altura fija 48px por fila */}
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <div key={`row-${rowIdx}`} className="flex gap-4 h-12">
          {Array.from({ length: columns }).map((_, colIdx) => (
            <Skeleton key={`cell-${rowIdx}-${colIdx}`} variant="text" width="100%" height={48} />
          ))}
        </div>
      ))}
    </div>
  );
}

/**
 * Skeleton para una lista de items
 */
export function ListSkeleton({ items = 5 }: { items?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: items }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 p-4 border rounded-lg">
          <Skeleton variant="circular" width={40} height={40} />
          <div className="flex-1 space-y-2">
            <Skeleton variant="text" width="60%" />
            <Skeleton variant="text" width="40%" />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Skeleton para un grid de cards (útil para dashboards)
 */
export function CardsGridSkeleton({ count = 4, columns = 4 }: { count?: number; columns?: number }) {
  // Usar clases de Tailwind directamente en lugar de template strings dinámicos
  const gridColsClass = columns === 1 ? 'grid-cols-1' : 
                       columns === 2 ? 'grid-cols-1 md:grid-cols-2' :
                       columns === 3 ? 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3' :
                       'grid-cols-1 md:grid-cols-2 lg:grid-cols-4';
  
  return (
    <div className={`grid ${gridColsClass} gap-4`}>
      {Array.from({ length: count }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  );
}

/**
 * Skeleton específico para Equity Card
 */
export function EquityCardSkeleton() {
  return (
    <div className="space-y-4 p-6 border rounded-lg">
      <Skeleton variant="text" width="40%" height={16} />
      <Skeleton variant="text" width="60%" height={32} />
      <div className="space-y-2 pt-3">
        <Skeleton variant="text" width="100%" height={14} />
        <Skeleton variant="text" width="80%" height={14} />
        <Skeleton variant="text" width="90%" height={14} />
      </div>
    </div>
  );
}

/**
 * Skeleton específico para Strategy Table
 */
export function StrategyTableSkeleton({ rows = 5, columns = 4 }: { rows?: number; columns?: number }) {
  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex gap-4 h-10">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={`header-${i}`} variant="text" width="100%" height={40} />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <div key={`row-${rowIdx}`} className="flex gap-4 h-12">
          {Array.from({ length: columns }).map((_, colIdx) => (
            <Skeleton key={`cell-${rowIdx}-${colIdx}`} variant="text" width="100%" height={48} />
          ))}
        </div>
      ))}
    </div>
  );
}
