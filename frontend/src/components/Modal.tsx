import React, { useEffect } from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

export function Modal({ isOpen, onClose, title, children }: ModalProps) {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleEscape);
    }

    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-slate-950/40 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Modal Content */}
      <div className="relative w-full max-w-lg transform overflow-hidden rounded-2xl bg-modal-bg border border-border-color p-6 text-left shadow-[0_10px_30px_rgba(15,23,42,0.08)] transition-all z-10 font-sans">
        <div className="flex items-center justify-between border-b border-border-color pb-3 mb-4">
          <h3 className="text-sm font-bold text-text-primary uppercase tracking-wider">
            {title}
          </h3>
          <button
            onClick={onClose}
            className="p-1 hover:bg-hover-row text-text-muted hover:text-text-secondary rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        
        <div className="text-xs text-text-secondary">
          {children}
        </div>
      </div>
    </div>
  );
}
