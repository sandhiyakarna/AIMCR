import React, { useState } from 'react';
import { Modal } from './Modal';
import axios from 'axios';
import { useToast } from '../context/ToastContext';

interface CreateCaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCaseCreated: (newCase: any) => void;
}

export function CreateCaseModal({ isOpen, onClose, onCaseCreated }: CreateCaseModalProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState('Medium');
  const [submitting, setSubmitting] = useState(false);
  const { showToast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    setSubmitting(true);
    try {
      const res = await axios.post('/api/cases', {
        title,
        description: description || undefined,
        priority,
      });
      showToast('Case created successfully', 'success');
      onCaseCreated(res.data);
      setTitle('');
      setDescription('');
      setPriority('Medium');
      onClose();
    } catch (err: any) {
      const errMsg = err.response?.data?.detail || 'Failed to create case';
      showToast(errMsg, 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const priorityColors: Record<string, string> = {
    Low: 'border-brand-success/30 bg-brand-success/10 text-brand-success',
    Medium: 'border-brand-warning/30 bg-brand-warning/10 text-brand-warning',
    High: 'border-brand-danger/30 bg-brand-danger/10 text-brand-danger',
    Critical: 'border-red-600/30 bg-red-600/10 text-red-600',
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create New Case File">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1">
            Case Title *
          </label>
          <input
            type="text"
            required
            className="w-full glass-input placeholder-text-muted text-text-primary text-xs"
            placeholder="e.g. Operation PhishTrap GPS jump anomaly"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1">
            Description
          </label>
          <textarea
            className="w-full glass-input placeholder-text-muted text-text-primary text-xs h-24 resize-none"
            placeholder="Provide case overview details, suspect names, device identifiers, and investigator scopes..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1">
            Priority
          </label>
          <div className="flex gap-2">
            {['Low', 'Medium', 'High', 'Critical'].map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setPriority(p)}
                className={`flex-1 py-1.5 text-[10px] font-bold rounded-lg border transition-all ${
                  priority === p
                    ? priorityColors[p] + ' ring-1 ring-offset-1'
                    : 'border-border-color text-text-muted hover:text-text-secondary bg-transparent'
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-2 border-t border-border-color">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-bold text-text-secondary hover:text-text-primary"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting || !title.trim()}
            className="px-4 py-2 text-xs font-bold text-white bg-brand-primary hover:bg-brand-primary-hover rounded-lg shadow-[0_12px_24px_rgba(37,99,235,0.24)] disabled:opacity-50 transition-all duration-150"
          >
            {submitting ? 'Creating...' : 'Create Case File'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
