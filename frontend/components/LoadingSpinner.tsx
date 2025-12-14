'use client';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
  fullScreen?: boolean;
}

export function LoadingSpinner({ size = 'md', text, fullScreen = false }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12'
  };

  const containerClasses = fullScreen
    ? 'min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-white to-slate-50'
    : 'flex items-center justify-center min-h-[400px] w-full';

  return (
    <div className={containerClasses}>
      <div className="text-center">
        {/* Premium Spinner */}
        <div className="relative inline-flex items-center justify-center mb-4">
          {/* Outer ring - subtle rotation */}
          <div className={`${sizeClasses[size]} border-4 border-slate-200 rounded-full`}></div>
          
          {/* Animated ring - smooth rotation */}
          <div className={`${sizeClasses[size]} border-4 border-slate-900 border-t-transparent rounded-full absolute animate-spin`} style={{ animationDuration: '0.8s' }}></div>
          
          {/* Inner dot - pulse effect */}
          <div className={`absolute ${size === 'sm' ? 'w-1 h-1' : size === 'md' ? 'w-2 h-2' : 'w-3 h-3'} bg-slate-900 rounded-full animate-pulse`} style={{ animationDuration: '1.2s' }}></div>
        </div>
        
        {/* Optional text */}
        {text && (
          <p className="text-sm font-medium text-slate-600 animate-pulse" style={{ animationDuration: '1.5s' }}>
            {text}
          </p>
        )}
      </div>
    </div>
  );
}

