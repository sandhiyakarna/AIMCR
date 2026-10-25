import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { RefreshCw, Key, ArrowLeft, ArrowRight } from 'lucide-react';
import { SkeletonLoader } from '../components/SkeletonLoader';

export function AuditTrail() {
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  
  // Pagination
  const [page, setPage] = useState(0);
  const [pageSize] = useState(15);
  const [totalCount, setTotalCount] = useState(0);

  useEffect(() => {
    fetchAuditTrail();
  }, [page]);

  const fetchAuditTrail = async () => {
    setLoading(true);
    try {
      const skip = page * pageSize;
      const res = await axios.get(`/api/audit?skip=${skip}&limit=${pageSize}`);
      // API now returns { items: [...], total_count: N }
      setAuditLogs(res.data.items || res.data);
      setTotalCount(res.data.total_count || 0);
    } catch (e) {
      console.error('Failed to load audit logs', e);
    } finally {
      setLoading(false);
    }
  };

  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className="glass-panel p-5 rounded-2xl space-y-4">
      <div className="flex justify-between items-center border-b border-border-color pb-3">
        <div className="flex items-center space-x-2.5">
          <Key className="w-5 h-5 text-brand-500" />
          <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider">
            Immutable Chain of Custody Audit Log
          </h2>
        </div>
        <div className="flex items-center space-x-3">
          <span className="text-[10px] font-bold text-text-muted">
            {totalCount > 0 ? `${totalCount} total entries` : ''}
          </span>
          <button
            onClick={fetchAuditTrail}
            disabled={loading}
            className="p-1 hover:bg-bg-secondary rounded"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-text-muted ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {loading ? (
        <SkeletonLoader type="table" count={5} />
      ) : auditLogs.length === 0 ? (
        <div className="text-center py-10 text-xs text-text-secondary font-semibold">
          No audit log entries recorded.
        </div>
      ) : (
        <div className="space-y-4">
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="border-b border-border-color text-[10px] font-bold text-text-muted uppercase tracking-wider">
                  <th className="py-2.5">Log Timestamp</th>
                  <th className="py-2.5">User</th>
                  <th className="py-2.5">Action Executed</th>
                  <th className="py-2.5">Activity Context Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-color font-medium">
                {auditLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-hover-row transition-colors">
                    <td className="py-3 font-semibold text-text-primary">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="py-3">
                      <span className="text-[9px] font-bold px-2 py-0.5 bg-bg-secondary text-text-secondary rounded-full border border-border-color">
                        {log.user_name}
                      </span>
                    </td>
                    <td className="py-3">
                      <span className="font-bold text-text-primary">{log.action}</span>
                    </td>
                    <td className="py-3 text-text-secondary leading-relaxed font-sans pr-4">
                      {log.details}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls with real count */}
          <div className="flex justify-between items-center pt-3 border-t border-border-color text-xs">
            <button
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0 || loading}
              className="flex items-center space-x-1 px-3 py-1.5 border border-slate-200 dark:border-slate-800 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-900 disabled:opacity-50 text-[10px] font-bold uppercase tracking-wider transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Previous</span>
            </button>
            <span className="text-text-muted font-bold uppercase tracking-widest text-[9px]">
              Page {page + 1} of {Math.max(totalPages, 1)}
            </span>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={page + 1 >= totalPages || loading}
              className="flex items-center space-x-1 px-3 py-1.5 border border-slate-200 dark:border-slate-800 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-900 disabled:opacity-50 text-[10px] font-bold uppercase tracking-wider transition-colors"
            >
              <span>Next</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
