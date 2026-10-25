import React from 'react';

export function SkeletonLoader({ type = 'card', count = 1 }: { type?: 'card' | 'list' | 'chart' | 'table'; count?: number }) {
  const renderSkeleton = () => {
    switch (type) {
      case 'list':
        return (
          <div className="space-y-3">
            {Array.from({ length: count }).map((_, i) => (
              <div key={i} className="flex items-center space-x-3 p-3 border border-border-color rounded-xl bg-bg-secondary animate-pulse">
                <div className="w-8 h-8 rounded-lg bg-bg-secondary" />
                <div className="flex-1 space-y-2">
                  <div className="h-2.5 bg-bg-secondary rounded w-1/4" />
                  <div className="h-2 bg-bg-secondary rounded w-3/4" />
                </div>
                <div className="w-16 h-3 bg-bg-secondary rounded" />
              </div>
            ))}
          </div>
        );
      case 'table':
        return (
          <div className="space-y-2.5 animate-pulse">
            <div className="h-6 bg-bg-secondary rounded-lg w-full mb-4" />
            {Array.from({ length: count }).map((_, i) => (
              <div key={i} className="flex gap-4 h-8 items-center border-b border-border-color/70">
                <div className="h-3 bg-bg-secondary rounded w-16" />
                <div className="h-3 bg-bg-secondary rounded w-32" />
                <div className="h-3 bg-bg-secondary rounded w-12" />
                <div className="h-3 bg-bg-secondary rounded flex-1" />
              </div>
            ))}
          </div>
        );
      case 'chart':
        return (
          <div className="p-4 border border-border-color rounded-xl bg-bg-secondary h-56 flex items-end justify-between gap-1 animate-pulse">
            {Array.from({ length: 12 }).map((_, i) => (
              <div
                key={i}
                style={{ height: `${Math.floor(Math.random() * 80) + 15}%` }}
                className="w-full bg-bg-secondary rounded-t-sm"
              />
            ))}
          </div>
        );
      case 'card':
      default:
        return (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {Array.from({ length: count }).map((_, i) => (
              <div key={i} className="glass-panel p-5 animate-pulse flex flex-col justify-between h-28">
                <div className="flex justify-between items-center">
                  <div className="h-3 bg-bg-secondary rounded w-20" />
                  <div className="w-6 h-6 rounded bg-bg-secondary" />
                </div>
                <div className="h-6 bg-bg-secondary rounded w-10 mt-4" />
                <div className="h-2 bg-bg-secondary rounded w-24 mt-2" />
              </div>
            ))}
          </div>
        );
    }
  };

  return <>{renderSkeleton()}</>;
}
