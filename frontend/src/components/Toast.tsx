import React from 'react';
import { useToast } from '../context/ToastContext';
import { CheckCircle, XCircle, Info, AlertTriangle, X } from 'lucide-react';

export function ToastContainer() {
  const { toasts, removeToast } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-5 right-5 z-[9999] flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      {toasts.map((toast) => {
        let icon = <Info className="w-5 h-5 text-brand-primary" />;
        let borderColor = 'border-brand-primary/20';
        let bgColor = 'bg-brand-primary/10';
        let textColor = 'text-text-primary';

        if (toast.type === 'success') {
          icon = <CheckCircle className="w-5 h-5 text-brand-success" />;
          borderColor = 'border-brand-success/20';
          bgColor = 'bg-brand-success/10';
          textColor = 'text-text-primary';
        } else if (toast.type === 'error') {
          icon = <XCircle className="w-5 h-5 text-brand-danger" />;
          borderColor = 'border-brand-danger/20';
          bgColor = 'bg-brand-danger/10';
          textColor = 'text-text-primary';
        } else if (toast.type === 'warning') {
          icon = <AlertTriangle className="w-5 h-5 text-brand-warning" />;
          borderColor = 'border-brand-warning/20';
          bgColor = 'bg-brand-warning/10';
          textColor = 'text-text-primary';
        }

        return (
          <div
            key={toast.id}
            className={`flex items-start gap-3 p-4 rounded-xl border ${borderColor} ${bgColor} ${textColor} shadow-[0_10px_30px_rgba(15,23,42,0.08)] backdrop-blur-md transition-all duration-300 transform translate-y-0 pointer-events-auto`}
            role="alert"
          >
            <div className="shrink-0">{icon}</div>
            <div className="flex-1 text-xs font-semibold leading-relaxed">{toast.message}</div>
            <button
              onClick={() => removeToast(toast.id)}
              className="shrink-0 p-0.5 hover:bg-slate-200/50 dark:hover:bg-slate-800/50 rounded-lg transition-colors"
            >
              <X className="w-3.5 h-3.5 opacity-60 hover:opacity-100" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
