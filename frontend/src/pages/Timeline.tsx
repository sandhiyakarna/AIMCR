import React, { useState, useEffect } from 'react';
import { useOutletContext, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Search, Compass, MessageSquare, Phone, MapPin, Cpu, FileText, Folder, Download, ExternalLink, History } from 'lucide-react';
import { SkeletonLoader } from '../components/SkeletonLoader';
import { useToast } from '../context/ToastContext';
import { API_BASE_URL } from '../config';

interface OutletContextType {
  selectedCaseId: string;
  loading: boolean;
  analyzing: boolean;
}

export function Timeline() {
  const { selectedCaseId, loading: layoutLoading, analyzing } = useOutletContext<OutletContextType>();
  const [searchParams, setSearchParams] = useSearchParams();
  const { showToast } = useToast();
  const [evidenceList, setEvidenceList] = useState<any[]>([]);
  const [anomalies, setAnomalies] = useState<any[]>([]);
  const [accessLogs, setAccessLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('ALL');
  const [selectedEvidence, setSelectedEvidence] = useState<any>(null);
  const [showAccessLogs, setShowAccessLogs] = useState(false);

  useEffect(() => {
    if (selectedCaseId) {
      fetchTimelineData(selectedCaseId);
    }
  }, [selectedCaseId, layoutLoading, analyzing]);

  useEffect(() => {
    if (evidenceList.length > 0) {
      // Read from URL params instead of React Router state
      const evidenceIdFromUrl = searchParams.get('evidenceId');
      if (evidenceIdFromUrl) {
        const found = evidenceList.find((ev) => ev.id === evidenceIdFromUrl);
        if (found) {
          setSelectedEvidence(found);
          return;
        }
      }
      // Auto select first item
      if (!selectedEvidence) {
        setSelectedEvidence(evidenceList[0]);
      }
    }
  }, [searchParams, evidenceList]);

  useEffect(() => {
    if (selectedEvidence) {
      fetchAccessLogs(selectedEvidence.id);
    }
  }, [selectedEvidence]);

  const fetchTimelineData = async (caseId: string) => {
    setLoading(true);
    try {
      const [evRes, anomalyRes] = await Promise.all([
        axios.get(`/api/timeline/${caseId}`),
        axios.get(`/api/analyze/anomalies/${caseId}`)
      ]);
      setEvidenceList(evRes.data);
      setAnomalies(anomalyRes.data);
      
      if (evRes.data.length > 0 && !selectedEvidence) {
        setSelectedEvidence(evRes.data[0]);
      }
    } catch (e) {
      console.error('Failed to load timeline data', e);
    } finally {
      setLoading(false);
    }
  };

  const fetchAccessLogs = async (evidenceId: string) => {
    try {
      const res = await axios.get(`/api/evidence/${evidenceId}/access-logs`);
      setAccessLogs(res.data);
    } catch (e) {
      console.error('Failed to load access logs', e);
      setAccessLogs([]);
    }
  };

  const handleEvidenceSelect = (ev: any) => {
    setSelectedEvidence(ev);
    // Update URL params for shareable link
    setSearchParams({ evidenceId: ev.id });
  };

  const handleDownload = async (evidenceId: string) => {
    try {
      const token = localStorage.getItem('aimcr_token');
      window.open(`${API_BASE_URL}/api/evidence/${evidenceId}/download?token=${token}`, '_blank');
      showToast('Evidence download started', 'success');
    } catch (e) {
      showToast('Failed to download evidence', 'error');
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
      case 'Notification': return <MessageSquare className="w-4 h-4 text-pink-500 shrink-0" />;
      case 'WiFi': return <Compass className="w-4 h-4 text-cyan-500 shrink-0" />;
      case 'Bluetooth': return <Cpu className="w-4 h-4 text-sky-500 shrink-0" />;
      default: return <Folder className="w-4 h-4 text-slate-500 shrink-0" />;
    }
  };

  const getDisplayTitle = (ev: any) => {
    const meta = ev.metadata || {};
    switch (ev.artifact_type) {
      case 'SMS': return meta.message || 'SMS Message';
      case 'BrowserHistory': return meta.url || 'Web Visit';
      case 'Call': return `Call with: ${meta.contact_name || meta.phone_number || 'Unknown'}`;
      case 'GPS': return `Coordinates: ${meta.latitude}, ${meta.longitude}`;
      case 'File': return meta.filename || 'File Modified';
      case 'Application': return `App Launched: ${meta.app_name || 'App'}`;
      case 'Notification': return meta.title || 'Notification';
      case 'WiFi': return `SSID: ${meta.ssid || 'Unknown'}`;
      case 'Bluetooth': return `Device: ${meta.name || 'Unknown'}`;
      default: return 'Forensic Entry';
    }
  };

  const filteredEvidence = evidenceList.filter((ev) => {
    if (filterType !== 'ALL' && ev.artifact_type !== filterType) return false;
    if (searchQuery.trim() !== '') {
      const q = searchQuery.toLowerCase();
      const titleMatch = getDisplayTitle(ev).toLowerCase().includes(q);
      const sourceMatch = ev.source.toLowerCase().includes(q);
      const hashMatch = ev.hash.toLowerCase().includes(q);
      const typeMatch = ev.artifact_type.toLowerCase().includes(q);
      return titleMatch || sourceMatch || hashMatch || typeMatch;
    }
    return true;
  });

  if (!selectedCaseId) {
    return (
      <div className="flex flex-col items-center justify-center h-80 text-center">
        <Folder className="w-12 h-12 text-slate-300 dark:text-slate-700 mb-3" />
        <h3 className="text-sm font-bold text-slate-600 dark:text-slate-400 uppercase tracking-wider">No Active Case File</h3>
        <p className="text-xs text-slate-400 max-w-xs mt-1">Select a case or create one to view the chronological timeline logs.</p>
      </div>
    );
  }

  if (loading || layoutLoading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <SkeletonLoader type="list" count={4} />
        </div>
        <div>
          <SkeletonLoader type="list" count={3} />
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
      
      {/* Timeline List Card */}
      <div className="lg:col-span-2 glass-panel p-5 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-border-color pb-4">
          <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider">Chronological Evidence Trace</h2>
          
          <div className="flex items-center space-x-2 shrink-0">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-text-muted absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search timeline..."
                className="glass-input pl-8 py-1 text-xs w-44 text-text-primary bg-input-bg border-border-color"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
              />
            </div>
            <select
              className="glass-input py-1 px-2 pr-8 text-xs bg-input-bg border-border-color text-text-primary font-semibold"
              value={filterType}
              onChange={e => setFilterType(e.target.value)}
            >
              <option value="ALL">All Types</option>
              <option value="SMS">SMS Logs</option>
              <option value="Call">Calls</option>
              <option value="GPS">Locations</option>
              <option value="BrowserHistory">Web History</option>
              <option value="Application">Apps</option>
              <option value="File">Files</option>
              <option value="Notification">Notifications</option>
              <option value="WiFi">WiFi Networks</option>
              <option value="Bluetooth">Bluetooth Devices</option>
            </select>
          </div>
        </div>

        {filteredEvidence.length === 0 ? (
          <div className="text-center py-10 text-xs text-text-muted font-semibold">
            No forensic artifacts match your search query or filters.
          </div>
        ) : (
          <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
            {filteredEvidence.map((ev) => {
              const isSelected = selectedEvidence?.id === ev.id;
              const hasThreatIntel = ev.metadata && ev.metadata.threat_intel_match;
              const isAnomaly = anomalies.some(a => a.evidence_id === ev.id);
              
              return (
                <div
                  key={ev.id}
                  onClick={() => handleEvidenceSelect(ev)}
                  className={`p-3 border rounded-xl cursor-pointer transition-all duration-150 ${
                    isSelected
                      ? 'border-brand-primary bg-brand-primary/10'
                      : hasThreatIntel
                      ? 'border-red-500/40 bg-red-500/10 dark:bg-red-950/20 hover:border-red-500/60'
                      : isAnomaly
                      ? 'border-brand-danger/30 bg-brand-danger/10 hover:border-brand-danger/50'
                      : 'border-border-color bg-card-secondary hover:border-brand-primary/20'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div className="flex items-center space-x-2.5 min-w-0">
                      <div className="p-1.5 bg-card rounded border border-border-color shrink-0">
                        {getArtifactIcon(ev.artifact_type)}
                      </div>
                      <div className="min-w-0">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-text-muted">
                          {ev.artifact_type}
                        </span>
                        <h4 className="text-xs font-semibold text-text-primary truncate mt-0.5 max-w-xs md:max-w-md">
                          {getDisplayTitle(ev)}
                        </h4>
                      </div>
                    </div>
                    <div className="flex flex-col items-end shrink-0 text-right space-y-1">
                      <span className="text-[9px] font-bold text-text-muted">
                        {new Date(ev.timestamp).toLocaleString()}
                      </span>
                      {hasThreatIntel && (
                        <span className="text-[9px] font-extrabold text-red-500 uppercase tracking-wider bg-red-500/15 dark:bg-red-500/20 px-1.5 py-0.5 rounded border border-red-500/30">
                          Threat Match
                        </span>
                      )}
                      {isAnomaly && !hasThreatIntel && (
                        <span className="text-[9px] font-extrabold text-brand-danger uppercase tracking-widest">
                          Anomaly
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Forensic Inspector Card with Download */}
      <div className="glass-panel p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-border-color pb-2">
          <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider">
            Forensic Inspector
          </h2>
        </div>
        
        {!selectedEvidence ? (
          <p className="text-xs text-text-muted py-6 text-center">
            Select an artifact in the timeline to inspect its metadata and integrity hashes.
          </p>
        ) : (
          <div className="space-y-4 text-xs">
            <div>
              <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider block">
                Artifact ID
              </span>
              <p className="font-mono text-text-secondary mt-1 select-all break-all bg-card p-2 rounded border border-border-color">
                {selectedEvidence.id}
              </p>
            </div>

            <div>
              <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider block">
                Acquisition Source
              </span>
              <p className="font-semibold text-text-primary mt-1">
                {selectedEvidence.source}
              </p>
            </div>

            <div>
              <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider block">
                Verification Integrity (SHA-256)
              </span>
              <p className="font-mono text-text-secondary mt-1 bg-card p-2 rounded border border-border-color select-all break-all">
                {selectedEvidence.hash}
              </p>
            </div>

            <div>
              <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider block">
                Acquisition Timestamp
              </span>
              <p className="font-semibold text-text-primary mt-1">
                {new Date(selectedEvidence.timestamp).toLocaleString()}
              </p>
            </div>

            {/* Download Evidence Button */}
            <button
              onClick={() => handleDownload(selectedEvidence.id)}
              className="w-full flex items-center justify-center space-x-2 py-2 px-3 bg-brand-primary hover:bg-brand-primary-hover text-white text-xs font-bold rounded-lg shadow-[0_10px_20px_rgba(37,99,235,0.2)] transition-all duration-150"
            >
              <Download className="w-4 h-4" />
              <span>Download Evidence</span>
            </button>

            {/* Access Logs Toggle */}
            <div>
              <button
                onClick={() => setShowAccessLogs(!showAccessLogs)}
                className="w-full flex items-center justify-between py-2 px-3 bg-card-secondary border border-border-color rounded-lg text-xs font-semibold text-text-primary hover:bg-card transition-colors"
              >
                <div className="flex items-center space-x-2">
                  <History className="w-4 h-4 text-text-muted" />
                  <span>Chain of Custody Log</span>
                </div>
                <span className="text-text-muted">{accessLogs.length} entries</span>
              </button>
              
              {showAccessLogs && (
                <div className="mt-2 max-h-40 overflow-y-auto space-y-1.5">
                  {accessLogs.length === 0 ? (
                    <p className="text-[10px] text-text-muted py-2 text-center">No access logs recorded.</p>
                  ) : (
                    accessLogs.map((log: any) => (
                      <div key={log.id} className="p-2 bg-bg-secondary rounded-lg border border-border-color">
                        <div className="flex justify-between items-center">
                          <span className="text-[9px] font-bold uppercase tracking-wider text-brand-primary">{log.action}</span>
                          <span className="text-[9px] text-text-muted">{new Date(log.timestamp).toLocaleString()}</span>
                        </div>
                        {log.remarks && (
                          <p className="text-[9px] text-text-secondary mt-0.5">{log.remarks}</p>
                        )}
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            <div>
              <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider block mb-1">
                Parsed Metadata Attributes
              </span>
              <pre className="font-mono text-[10px] text-text-secondary bg-card p-3 rounded-lg border border-border-color overflow-x-auto max-h-60">
                {JSON.stringify(selectedEvidence.metadata, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>

    </div>
  );
}
