import React, { useState, useEffect } from 'react';
import { useOutletContext, Link } from 'react-router-dom';
import axios from 'axios';
import { Folder, ShieldAlert, GitFork, Users, Phone, MapPin, Cpu, ChevronRight } from 'lucide-react';
import { SkeletonLoader } from '../components/SkeletonLoader';

interface OutletContextType {
  selectedCaseId: string;
  selectedCase: any;
  loading: boolean;
  analyzing: boolean;
}

export function Dashboard() {
  const { selectedCaseId, selectedCase, loading: layoutLoading, analyzing } = useOutletContext<OutletContextType>();
  const [evidenceList, setEvidenceList] = useState<any[]>([]);
  const [anomalies, setAnomalies] = useState<any[]>([]);
  const [reconstructions, setReconstructions] = useState<any[]>([]);
  const [graphData, setGraphData] = useState<any>({ nodes: [], edges: [] });
  const [summaryData, setSummaryData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (selectedCaseId) {
      fetchCaseDetails(selectedCaseId);
    }
  }, [selectedCaseId, layoutLoading, analyzing]);

  const fetchCaseDetails = async (caseId: string) => {
    setLoading(true);
    try {
      const [evRes, anomalyRes, reconRes, graphRes, summaryRes] = await Promise.all([
        axios.get(`/api/evidence/case/${caseId}`),
        axios.get(`/api/analyze/anomalies/${caseId}`),
        axios.get(`/api/timeline/reconstruct/${caseId}`),
        axios.get(`/api/analyze/graph/${caseId}`),
        axios.get(`/api/analyze/summary/${caseId}`).catch(() => null)
      ]);
      
      setEvidenceList(evRes.data);
      setAnomalies(anomalyRes.data);
      setReconstructions(reconRes.data);
      setGraphData(graphRes.data);
      if (summaryRes) {
        setSummaryData(summaryRes.data);
      } else {
        setSummaryData(null);
      }
    } catch (e) {
      console.error('Failed to load dashboard data', e);
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (score: number) => {
    if (score > 80 || score > 0.8) return 'bg-brand-danger/10 text-brand-danger border border-brand-danger/20';
    if (score > 50 || score > 0.5) return 'bg-brand-warning/10 text-brand-warning border border-brand-warning/20';
    return 'bg-brand-primary/10 text-brand-primary border border-brand-primary/20';
  };

  const getArtifactIcon = (type: string) => {
    switch (type) {
      case 'SMS': return <Folder className="w-4 h-4 text-emerald-500 shrink-0" />;
      case 'Call': return <Phone className="w-4 h-4 text-blue-500 shrink-0" />;
      case 'GPS': return <MapPin className="w-4 h-4 text-rose-500 shrink-0" />;
      case 'BrowserHistory': return <Folder className="w-4 h-4 text-indigo-500 shrink-0" />;
      case 'Application': return <Cpu className="w-4 h-4 text-amber-500 shrink-0" />;
      case 'File': return <Folder className="w-4 h-4 text-purple-500 shrink-0" />;
      default: return <Folder className="w-4 h-4 text-slate-500 shrink-0" />;
    }
  };

  if (!selectedCaseId) {
    return (
      <div className="flex flex-col items-center justify-center h-80 text-center rounded-2xl border border-border-color bg-bg-card shadow-[0_4px_10px_rgba(15,23,42,0.06)]">
        <Folder className="w-12 h-12 text-text-muted mb-3" />
        <h3 className="text-sm font-bold text-text-primary uppercase tracking-wider">No Active Case File</h3>
        <p className="text-xs text-text-secondary max-w-xs mt-1">Create a case file using the sidebar button to begin mobile intelligence operations.</p>
      </div>
    );
  }

  if (loading || layoutLoading) {
    return (
      <div className="space-y-6">
        <SkeletonLoader type="card" count={4} />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <SkeletonLoader type="list" count={2} />
          </div>
          <div>
            <SkeletonLoader type="list" count={3} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      
      {/* Forensic Case Complexity Index (FCCI) Panel */}
      {summaryData && summaryData.complexity && (
        <div className="glass-panel p-6 border-l-4 border-l-brand-danger bg-gradient-to-r from-bg-card to-slate-900/10">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="space-y-2 flex-1">
              <div className="flex items-center space-x-2">
                <span className="text-[10px] font-bold px-2 py-0.5 bg-brand-danger/10 text-brand-danger border border-brand-danger/20 rounded-full uppercase tracking-wider">
                  Forensic Complexity Index
                </span>
                <span className="text-xs text-text-muted font-bold">•</span>
                <span className="text-xs font-semibold text-text-secondary">FCCI Assessment</span>
                {selectedCase && (
                  <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                    selectedCase.priority === 'Critical' ? 'bg-red-500/15 text-red-500 border border-red-500/30' :
                    selectedCase.priority === 'High' ? 'bg-orange-500/15 text-orange-500 border border-orange-500/30' :
                    selectedCase.priority === 'Low' ? 'bg-green-500/15 text-green-500 border border-green-500/30' :
                    'bg-yellow-500/15 text-yellow-500 border border-yellow-500/30'
                  }`}>
                    Priority: {selectedCase.priority}
                  </span>
                )}
              </div>
              <h2 className="text-xl font-bold text-text-primary">
                Case Complexity: <span className="text-brand-danger">{summaryData.complexity.rating}</span> ({summaryData.complexity.score}/100)
              </h2>
              <p className="text-xs text-text-secondary leading-relaxed font-semibold">
                {summaryData.complexity.explanation}
              </p>
              {summaryData.complexity.breakdown && (
                <div className="flex flex-wrap gap-2 pt-2">
                  {summaryData.complexity.breakdown.map((item: string, idx: number) => (
                    <span key={idx} className="text-[9px] font-bold px-2 py-1 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 rounded-md">
                      {item}
                    </span>
                  ))}
                </div>
              )}
            </div>
            
            {/* Visual Meter Dial */}
            <div className="flex flex-col items-center shrink-0">
              <div className="relative w-24 h-12 overflow-hidden flex items-end justify-center">
                {/* Semi-circle dial background */}
                <div className="absolute top-0 left-0 w-24 h-24 border-8 border-slate-200 dark:border-slate-800 rounded-full"></div>
                {/* Semi-circle dial progress filled (colored according to score) */}
                <div 
                  className={`absolute top-0 left-0 w-24 h-24 border-8 rounded-full transition-transform duration-1000 origin-center`}
                  style={{
                    transform: `rotate(${Math.min(summaryData.complexity.score * 1.8, 180) - 180}deg)`,
                    borderColor: summaryData.complexity.score > 75 ? '#ef4444' : summaryData.complexity.score > 50 ? '#f97316' : '#3b82f6',
                    clipPath: 'polygon(0% 0%, 100% 0%, 100% 50%, 0% 50%)'
                  }}
                ></div>
                {/* Center Score */}
                <span className="text-lg font-serif font-bold text-text-primary z-10">{summaryData.complexity.score}</span>
              </div>
              <span className="text-[9px] font-bold text-text-muted uppercase tracking-widest mt-1">FCCI SCORE</span>
            </div>
          </div>
        </div>
      )}

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="glass-panel p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-text-secondary uppercase tracking-wider">Forensic Artifacts</span>
            <Folder className="w-5 h-5 text-indigo-500" />
          </div>
          <h3 className="text-2xl font-bold text-text-primary font-serif">{evidenceList.length}</h3>
          <p className="text-[10px] text-text-muted mt-1">Normalized chronological entries</p>
        </div>
        
        <div className="glass-panel p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-text-secondary uppercase tracking-wider">Flagged Anomalies</span>
            <ShieldAlert className="w-5 h-5 text-brand-danger" />
          </div>
          <h3 className="text-2xl font-bold text-text-primary font-serif">{anomalies.length}</h3>
          <p className="text-[10px] text-brand-danger font-bold mt-1">Isolation Forest deviations</p>
        </div>

        <div className="glass-panel p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-text-secondary uppercase tracking-wider">Reconstructed Scenarios</span>
            <GitFork className="w-5 h-5 text-brand-warning" />
          </div>
          <h3 className="text-2xl font-bold text-text-primary font-serif">{reconstructions.length}</h3>
          <p className="text-[10px] text-text-muted mt-1">Attack sequences identified</p>
        </div>

        <div className="glass-panel p-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold text-text-secondary uppercase tracking-wider">Network Connections</span>
            <Users className="w-5 h-5 text-brand-success" />
          </div>
          <h3 className="text-2xl font-bold text-text-primary font-serif">{graphData.edges?.length || 0}</h3>
          <p className="text-[10px] text-text-muted mt-1">Graph nodes & edge links</p>
        </div>
      </div>

      {/* Main row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Reconstructions List */}
        <div className="lg:col-span-2 space-y-4">
          <div className="glass-panel p-5">
            <div className="flex justify-between items-center mb-4 border-b border-border-color pb-2">
              <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider">Reconstructed Cybercrime Sequences</h2>
              <Link to="/reconstruction" className="text-xs text-brand-primary font-bold hover:underline flex items-center">
                <span>View Details</span>
                <ChevronRight className="w-4 h-4 ml-0.5" />
              </Link>
            </div>
            
            {reconstructions.length === 0 ? (
              <p className="text-xs text-text-muted py-4">No sequences reconstructed. Click 'Re-Run Intelligence Engine' to compute.</p>
            ) : (
              <div className="space-y-4">
                {reconstructions.map((recon, idx) => (
                  <div key={idx} className="p-4 bg-bg-secondary border border-border-color rounded-xl space-y-3 shadow-[0_1px_2px_rgba(15,23,42,0.05)]">
                    <div className="flex justify-between items-center">
                      <span className="text-xs font-bold text-brand-primary">{recon.incident_type}</span>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${getSeverityColor(recon.confidence)}`}>
                        {Math.round(recon.confidence * 100)}% Confidence
                      </span>
                    </div>
                    <p className="text-xs text-text-secondary leading-relaxed font-semibold">
                      {recon.explanation}
                    </p>
                    
                    <div className="border-t border-border-color pt-2">
                      <p className="text-[9px] font-bold text-text-muted uppercase tracking-wider mb-2">Key Events Linkage</p>
                      <div className="flex flex-wrap gap-2">
                        {recon.steps.slice(0, 4).map((step: any) => (
                          <div key={step.step_number} className="flex items-center space-x-1 text-[10px] bg-bg-card border border-border-color px-2 py-1 rounded">
                            {getArtifactIcon(step.event_type)}
                            <span className="font-semibold text-text-secondary">{step.evidence_references[0]?.slice(0, 8)}...</span>
                          </div>
                        ))}
                        {recon.steps.length > 4 && (
                          <span className="text-[10px] text-text-muted self-center">+{recon.steps.length - 4} more</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Priority Targets Panel */}
        <div className="space-y-4">
          <div className="glass-panel p-5">
            <div className="flex justify-between items-center mb-4 border-b border-border-color pb-2">
              <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider">Investigative Priorities</h2>
              <Link to="/graph" className="text-xs text-brand-primary font-bold hover:underline flex items-center">
                <span>View Graph</span>
                <ChevronRight className="w-4 h-4 ml-0.5" />
              </Link>
            </div>
            
            {graphData.nodes?.length === 0 ? (
              <p className="text-xs text-text-muted py-4">No graph data. Click 'Re-Run Intelligence Engine' to compute.</p>
            ) : (
              <div className="space-y-3">
                {graphData.nodes
                  ?.sort((a: any, b: any) => b.priority_score - a.priority_score)
                  .slice(0, 5)
                  .map((node: any) => (
                    <div key={node.id} className="flex items-center justify-between p-2.5 bg-bg-secondary border border-border-color rounded-lg hover:border-brand-primary/20 transition-all duration-200">
                      <div className="flex items-center space-x-2.5 min-w-0">
                        <div className="p-1.5 bg-card rounded border border-border-color shrink-0">
                          {node.type === 'Contact' ? <Phone className="w-3.5 h-3.5 text-blue-500" /> : node.type === 'Location' ? <MapPin className="w-3.5 h-3.5 text-rose-500" /> : <Cpu className="w-3.5 h-3.5 text-indigo-500" />}
                        </div>
                        <div className="min-w-0">
                          <p className="text-xs font-semibold text-text-primary truncate">{node.label}</p>
                          <p className="text-[9px] font-bold text-text-muted uppercase tracking-wider">{node.type}</p>
                        </div>
                      </div>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${getSeverityColor(node.priority_score / 100)}`}>
                        {Math.round(node.priority_score)}/100 Priority
                      </span>
                    </div>
                  ))}
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
