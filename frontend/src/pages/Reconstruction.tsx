import React, { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import axios from 'axios';
import { GitFork, MessageSquare, Phone, MapPin, Compass, Cpu, FileText, Folder } from 'lucide-react';
import { SkeletonLoader } from '../components/SkeletonLoader';

interface OutletContextType {
  selectedCaseId: string;
  loading: boolean;
  analyzing: boolean;
}

export function Reconstruction() {
  const { selectedCaseId, loading: layoutLoading, analyzing } = useOutletContext<OutletContextType>();
  const [reconstructions, setReconstructions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (selectedCaseId) {
      fetchReconstructionData(selectedCaseId);
    }
  }, [selectedCaseId, layoutLoading, analyzing]);

  const fetchReconstructionData = async (caseId: string) => {
    setLoading(true);
    try {
      const res = await axios.get(`/api/timeline/reconstruct/${caseId}`);
      setReconstructions(res.data);
    } catch (e) {
      console.error('Failed to fetch reconstructions', e);
    } finally {
      setLoading(false);
    }
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

  const getSeverityBgColor = (score: number) => {
    if (score > 0.8) return 'bg-red-500 text-white';
    if (score > 0.5) return 'bg-amber-500 text-white';
    return 'bg-blue-500 text-white';
  };

  if (!selectedCaseId) {
    return (
      <div className="flex flex-col items-center justify-center h-80 text-center">
        <Folder className="w-12 h-12 text-slate-300 dark:text-slate-700 mb-3" />
        <h3 className="text-sm font-bold text-slate-600 dark:text-slate-400 uppercase tracking-wider">No Active Case File</h3>
        <p className="text-xs text-slate-400 max-w-xs mt-1">Select a case or run the analysis engine to view attack reconstructions.</p>
      </div>
    );
  }

  if (loading || layoutLoading) {
    return (
      <div className="space-y-6">
        <SkeletonLoader type="list" count={3} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="glass-panel p-5">
        <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider mb-4 border-b border-border-color pb-2">
          Autonomous Crime Reconstruction Explanations
        </h2>
        
        {reconstructions.length === 0 ? (
          <div className="text-center py-10 text-xs text-text-muted font-semibold">
            No structured reconstructions available. Click 'Re-Run Intelligence Engine' to compute.
          </div>
        ) : (
          <div className="space-y-8">
            {reconstructions.map((recon, idx) => (
              <div key={idx} className="space-y-4 border border-border-color rounded-xl p-5 bg-card-secondary">
                <div className="flex justify-between items-center pb-2 border-b border-border-color">
                  <div className="flex items-center space-x-2">
                    <GitFork className="w-5 h-5 text-brand-primary animate-pulse" />
                    <h3 className="text-sm font-bold text-text-primary">{recon.incident_type}</h3>
                  </div>
                  <span className={`text-xs font-bold px-3 py-1 rounded-full ${getSeverityBgColor(recon.confidence)} shadow-sm`}>
                    {Math.round(recon.confidence * 100)}% Confidence Level
                  </span>
                </div>
                
                <div>
                  <h4 className="text-[10px] font-bold text-text-muted uppercase tracking-wider mb-1">
                    Incident Explanation
                  </h4>
                  <p className="text-xs text-text-secondary leading-relaxed font-semibold bg-card p-3 rounded-lg border border-border-color">
                    {recon.explanation}
                  </p>
                </div>

                {/* Interactive Steps Flow */}
                <div>
                  <h4 className="text-[10px] font-bold text-text-muted uppercase tracking-wider mb-3">
                    Incident sequence steps
                  </h4>
                  <div className="space-y-4 relative pl-4 before:absolute before:left-1.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-brand-primary/20">
                    {recon.steps.map((step: any, stepIdx: number) => (
                      <div key={stepIdx} className="relative space-y-1.5">
                        
                        {/* Bullet Circle */}
                        <div className="absolute -left-[20px] top-1 w-3.5 h-3.5 rounded-full bg-brand-primary border-2 border-card-secondary flex items-center justify-center">
                          <span className="text-[7px] text-white font-extrabold">{step.step_number}</span>
                        </div>

                        <div className="p-3 bg-card border border-border-color rounded-lg flex justify-between items-start shadow-sm hover:border-brand-primary/10 transition-colors">
                          <div className="space-y-1 min-w-0">
                            <div className="flex items-center space-x-2">
                              {getArtifactIcon(step.event_type)}
                              <span className="text-[9px] font-bold text-text-muted uppercase tracking-wider">{step.event_type}</span>
                            </div>
                            <p className="text-xs text-text-secondary font-semibold">{step.description}</p>
                          </div>
                          <div className="flex flex-col items-end shrink-0 text-right space-y-1">
                            <span className="text-[9px] font-bold text-text-muted">
                              {new Date(step.timestamp).toLocaleString()}
                            </span>
                            <div className="flex items-center space-x-1 bg-brand-primary/10 px-1.5 py-0.5 rounded text-[8px] font-mono text-brand-primary">
                              <span>Ref:</span>
                              <span className="font-bold select-all">{step.evidence_references[0]?.slice(0, 8)}...</span>
                            </div>
                          </div>
                        </div>

                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
