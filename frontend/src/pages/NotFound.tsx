import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldAlert, Home } from 'lucide-react';

export function NotFound() {
  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center text-center font-sans">
      <div className="p-4 bg-brand-danger/10 border border-brand-danger/20 rounded-2xl mb-4">
        <ShieldAlert className="w-12 h-12 text-brand-danger animate-bounce" />
      </div>
      <h1 className="text-3xl font-extrabold text-text-primary font-serif">404</h1>
      <p className="text-sm font-bold text-text-secondary uppercase tracking-widest mt-1">Route Not Found</p>
      <p className="text-xs text-text-secondary max-w-sm mt-2 leading-relaxed">
        The forensic route directory you are trying to access does not exist or you lack authorization keys to view this sector.
      </p>
      <Link
        to="/"
        className="mt-6 flex items-center space-x-2 px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white text-xs font-bold rounded-lg shadow-[0_12px_24px_rgba(37,99,235,0.24)] transition-colors"
      >
        <Home className="w-4 h-4" />
        <span>Return to Dashboard</span>
      </Link>
    </div>
  );
}
