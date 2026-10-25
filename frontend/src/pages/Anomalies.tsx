import React, { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import axios from 'axios';
import { ShieldAlert, Compass, MessageSquare, Phone, MapPin, Cpu, FileText, Folder } from 'lucide-react';
import { SkeletonLoader } from '../components/SkeletonLoader';

interface OutletContextType {
  selectedCaseId: string;
  loading: boolean;
  analyzing: boolean;
}

export function Anomalies() {
  const { selectedCaseId, loading: layoutLoading, analyzing } = useOutletContext<OutletContextType>();
  const [evidenceList, setEvidenceList] = useState<any[]>([]);
  const [anomalies, setAnomalies] = useState<any[]>([]);
  const [antiForensicsAlerts, setAntiForensicsAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (selectedCaseId) {
      fetchAnomalyData(selectedCaseId);
    }
  }, [selectedCaseId, layoutLoading, analyzing]);

  const fetchAnomalyData = async (caseId: string) => {
    setLoading(true);
    try {
      const [evRes, anomalyRes, summaryRes] = await Promise.all([
        axios.get(`/api/evidence/case/${caseId}`),
        axios.get(`/api/analyze/anomalies/${caseId}`),
        axios.get(`/api/analyze/summary/${caseId}`).catch(() => null)
      ]);
      setEvidenceList(evRes.data);
      setAnomalies(anomalyRes.data);
      if (summaryRes && summaryRes.data.anti_forensics) {
        setAntiForensicsAlerts(summaryRes.data.anti_forensics);
      } else {
        setAntiForensicsAlerts([]);
      }
    } catch (e) {
      console.error('Failed to fetch anomalies', e);
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (score: number) => {
    if (score > 0.8) return 'bg-red-500 text-white dark:bg-red-600';
    if (score > 0.5) return 'bg-amber-500 text-white dark:bg-amber-600';
    return 'bg-blue-500 text-white dark:bg-blue-600';
  };

  const getArtifactIcon = (type: string) => {
    switch (type) {
      case 'SMS': return <MessageSquare className="w-4 h-4 text-emerald-500 shrink-0" />;
      case 'Call': return <Phone className="w-4 h-4 text-blue-500 shrink-0" />;
      case 'GPS': return <MapPin className="w-4 h-4 text-rose-500 shrink-0" />;
      case 'BrowserHistory': return <Compass className="w-4 h-4 text-indigo-500 shrink-0" />;
      case 'Application': return <Cpu className="w-4 h-4 text-amber-500 shrink-0" />;
      case 'File': return <FileText className="w-4 h-4 text-purple-500 shrink-0" />;
      default: return <Folder className="w-4 h-4 text-slate-500 shrink-0" />;
    }
  };

  if (!selectedCaseId) {
    return (
      <div className="flex flex-col items-center justify-center h-80 text-center rounded-2xl border border-border-color bg-bg-card shadow-[0_4px_10px_rgba(15,23,42,0.06)]">
        <Folder className="w-12 h-12 text-text-muted mb-3" />
        <h3 className="text-sm font-bold text-text-primary uppercase tracking-wider">No Active Case File</h3>
        <p className="text-xs text-text-secondary max-w-xs mt-1">Select a case to compute and view behavioral anomalies.</p>
      </div>
    );
  }

  if (loading || layoutLoading) {
    return (
      <div className="space-y-6">
        <SkeletonLoader type="chart" />
        <SkeletonLoader type="table" count={5} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      
      {/* Analytics Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Hourly Chart Log */}
        <div className="glass-panel p-5 md:col-span-2 space-y-4">
          <h2 className="text-sm font-bold text-slate-800 dark:text-slate-100 uppercase tracking-wider border-b border-slate-100 dark:border-slate-800 pb-2">
            Device Activity Profiler
          </h2>
          
          <div className="space-y-2">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">
              Hourly Event Density (24h baseline)
            </span>
            <div className="flex items-end justify-between h-40 pt-4 px-2 border-b border-l border-slate-200 dark:border-slate-800/80">
              {Array.from({ length: 24 }).map((_, h) => {
                const count = evidenceList.filter(ev => new Date(ev.timestamp).getHours() === h).length;
                const maxCount = Math.max(...Array.from({ length: 24 }).map((_, hr) => evidenceList.filter(ev => new Date(ev.timestamp).getHours() === hr).length), 1);
                const pct = (count / maxCount) * 100;
                
                const isSleep = h < 6 || h >= 23;
                const colorClass = isSleep
                  ? 'bg-indigo-500/80 hover:bg-indigo-500 dark:bg-indigo-600/70 dark:hover:bg-indigo-600'
                  : 'bg-brand-500/80 hover:bg-brand-500 dark:bg-brand-600/70 dark:hover:bg-brand-600';
                
                return (
                  <div key={h} className="group relative flex-1 flex flex-col items-center mx-[1px] h-full justify-end">
                    <div className="absolute -top-8 bg-bg-card text-text-primary text-[9px] font-bold py-1 px-1.5 rounded opacity-0 group-hover:opacity-100 transition-opacity duration-150 pointer-events-none whitespace-nowrap z-30 shadow-[0_10px_30px_rgba(15,23,42,0.08)]">
                      Hour {h}:00 ({count} events)
                    </div>
                    <div
                      style={{ height: `${pct}%` }}
                      className={`w-full rounded-t-sm transition-all duration-300 ${colorClass}`}
                    />
                    <span className="text-[8px] text-text-muted mt-1 scale-90">{h}</span>
                  </div>
                );
              })}
            </div>
            <div className="flex items-center justify-center space-x-6 text-[10px] mt-2">
              <div className="flex items-center space-x-1.5">
                <div className="w-2.5 h-2.5 bg-brand-primary rounded-sm" />
                <span className="text-text-secondary font-semibold">Regular Active Hours (6 AM - 11 PM)</span>
              </div>
              <div className="flex items-center space-x-1.5">
                <div className="w-2.5 h-2.5 bg-indigo-500 rounded-sm" />
                <span className="text-text-secondary font-semibold">Typical Sleep Hours (11 PM - 6 AM)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Model parameters Card */}
        <div className="glass-panel p-5 flex flex-col justify-between">
          <div>
            <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider border-b border-border-color pb-2 mb-3">
              Model Parameters
            </h2>
            <div className="space-y-3 text-xs">
              <div>
                <span className="text-text-secondary font-bold block">Algorithm Baseline:</span>
                <span className="font-bold text-text-primary">Scikit-learn Isolation Forest</span>
              </div>
              <div>
                <span className="text-text-secondary font-bold block">Estimators Count:</span>
                <span className="font-bold text-text-primary">100 Trees</span>
              </div>
              <div>
                <span className="text-text-secondary font-bold block">Contamination Ratio:</span>
                <span className="font-bold text-text-primary">15.0% Outliers</span>
              </div>
              <div>
                <span className="text-text-secondary font-bold block">Feature Dimensions:</span>
                <span className="font-bold text-text-primary">Temporal (hour, weekend) + Spatial (GPS jumps) + Category Density</span>
              </div>
            </div>
          </div>
          <div className="p-3 bg-brand-primary/10 border border-brand-primary/30 rounded-lg text-xs text-brand-primary mt-4 leading-relaxed font-semibold">
            Isolation Forest flags multidimensional anomalies. Items exceeding 65% anomaly score represent significant behavioral anomalies.
          </div>
        </div>
      </div>

      {/* Outlier log table */}
      <div className="glass-panel p-5">
        <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider mb-4 border-b border-border-color pb-2">
          Isolation Forest Outlier Log
        </h2>
        
        {anomalies.length === 0 ? (
          <div className="text-center py-10 text-xs text-text-muted font-semibold">
            No anomalies detected. Click 'Re-Run Intelligence Engine' to compute.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="border-b border-border-color text-[10px] font-bold text-text-muted uppercase tracking-wider">
                  <th className="py-2.5">Severity</th>
                  <th className="py-2.5">Timestamp</th>
                  <th className="py-2.5">Artifact Type</th>
                  <th className="py-2.5">Anomaly Score</th>
                  <th className="py-2.5">AI Explanation / Contributing Factors</th>
                  <th className="py-2.5">Evidence Ref</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-color font-medium">
                {anomalies.map((a, idx) => (
                  <tr key={idx} className="hover:bg-hover-row transition-colors">
                    <td className="py-3">
                      <span className={`text-[9px] font-extrabold px-2 py-0.5 rounded-full uppercase tracking-wider ${getSeverityColor(a.score)}`}>
                        {a.score > 0.85 ? 'Critical' : 'Moderate'}
                      </span>
                    </td>
                    <td className="py-3 font-semibold text-text-primary">
                      {new Date(a.timestamp).toLocaleString()}
                    </td>
                    <td className="py-3">
                      <div className="flex items-center space-x-1.5">
                        {getArtifactIcon(a.artifact_type)}
                        <span className="font-semibold text-text-secondary">{a.artifact_type}</span>
                      </div>
                    </td>
                    <td className="py-3 font-mono font-bold text-text-secondary">
                      {Math.round(a.score * 100)}%
                    </td>
                    <td className="py-3 text-text-secondary pr-4 leading-relaxed font-semibold">
                      {a.explanation}
                    </td>
                    <td className="py-3 font-mono text-brand-primary font-bold select-all">
                      {a.evidence_id?.slice(0, 8)}...
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Anti-Forensics Alerts Dashboard Section */}
      <div className="glass-panel p-5">
        <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider mb-4 border-b border-border-color pb-2 flex items-center justify-between">
          <span>Anti-Forensics & Tampering Identification Log</span>
          <span className="text-[10px] font-bold px-2 py-0.5 bg-brand-danger/10 text-brand-danger border border-brand-danger/20 rounded-full">
            {antiForensicsAlerts.length} Flag(s) Detected
          </span>
        </h2>
        
        {antiForensicsAlerts.length === 0 ? (
          <div className="text-center py-10 text-xs text-text-muted font-semibold">
            No active attempts to alter, hide, or erase evidence were flagged.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="border-b border-border-color text-[10px] font-bold text-text-muted uppercase tracking-wider">
                  <th className="py-2.5">Tampering Category</th>
                  <th className="py-2.5">Severity</th>
                  <th className="py-2.5">Timestamp</th>
                  <th className="py-2.5">Forensic Findings / Description</th>
                  <th className="py-2.5">Evidence Reference</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-color font-medium">
                {antiForensicsAlerts.map((af, idx) => (
                  <tr key={idx} className="hover:bg-hover-row transition-colors">
                    <td className="py-3 font-semibold text-text-primary">
                      <span className="px-2 py-1 bg-red-50 dark:bg-red-950/20 text-red-600 dark:text-red-400 border border-red-100 dark:border-red-900/30 rounded-md">
                        {af.type}
                      </span>
                    </td>
                    <td className="py-3">
                      <span className={`text-[9px] font-extrabold px-2 py-0.5 rounded-full uppercase tracking-wider ${af.severity === 'High' ? 'bg-red-500 text-white' : 'bg-amber-500 text-white'}`}>
                        {af.severity}
                      </span>
                    </td>
                    <td className="py-3 text-text-secondary font-semibold">
                      {new Date(af.timestamp).toLocaleString()}
                    </td>
                    <td className="py-3 text-text-secondary leading-relaxed font-semibold pr-4">
                      {af.description}
                    </td>
                    <td className="py-3 font-mono text-brand-primary font-bold">
                      {af.evidence_id?.slice(0, 8)}...
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
}
