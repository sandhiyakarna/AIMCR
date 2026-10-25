import React, { useState, useEffect, useRef } from 'react';
import { useOutletContext, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Send, RefreshCw, Cpu, MessageSquare, Phone, MapPin, Compass, FileText, Folder, Download } from 'lucide-react';

interface OutletContextType {
  selectedCaseId: string;
  loading: boolean;
}

export function Copilot() {
  const { selectedCaseId, loading: layoutLoading } = useOutletContext<OutletContextType>();
  const navigate = useNavigate();

  const [messages, setMessages] = useState<any[]>([
    {
      sender: 'ai',
      text: 'Hello Investigator. I am the AIMCR Copilot. Ask me any question about the case, and I will search the FAISS vector index to provide grounded analysis citing the exact Evidence IDs.',
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeSidebarTab, setActiveSidebarTab] = useState<'queries' | 'recs'>('queries');
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [recSummary, setRecSummary] = useState('');
  const [fetchingRecs, setFetchingRecs] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  useEffect(() => {
    if (selectedCaseId) {
      fetchRecommendations(selectedCaseId);
    }
  }, [selectedCaseId]);

  const fetchRecommendations = async (caseId: string) => {
    setFetchingRecs(true);
    try {
      const res = await axios.get(`/api/copilot/recommendations/${caseId}`);
      setRecommendations(res.data.recommendations || []);
      setRecSummary(res.data.summary || '');
    } catch (e) {
      console.error('Failed to fetch recommendations', e);
    } finally {
      setFetchingRecs(false);
    }
  };

  const handleAskCopilot = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !selectedCaseId) return;

    const userQuestion = input;
    setMessages((prev) => [...prev, { sender: 'user', text: userQuestion, timestamp: new Date() }]);
    setInput('');
    setLoading(true);

    try {
      const res = await axios.post(`/api/copilot/investigations/${selectedCaseId}/ai/query`, {
        question: userQuestion
      });

      setMessages((prev) => [
        ...prev,
        {
          sender: 'ai',
          text: res.data.answer,
          evidence: res.data.retrieved_evidence,
          confidence: res.data.confidence,
          limitations: res.data.limitations,
          timestamp: new Date()
        }
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          sender: 'ai',
          text: 'Error communicating with AI Copilot service. Check connection or verify Ollama service status.',
          timestamp: new Date()
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickQuery = (query: string) => {
    setInput(query);
  };

  const getArtifactIcon = (type: string) => {
    switch (type) {
      case 'SMS': return <MessageSquare className="w-3.5 h-3.5 text-emerald-500" />;
      case 'Call': return <Phone className="w-3.5 h-3.5 text-blue-500" />;
      case 'GPS': return <MapPin className="w-3.5 h-3.5 text-rose-500" />;
      case 'BrowserHistory': return <Compass className="w-3.5 h-3.5 text-indigo-500" />;
      case 'Application': return <Cpu className="w-3.5 h-3.5 text-amber-500" />;
      case 'File': return <FileText className="w-3.5 h-3.5 text-purple-500" />;
      default: return <Folder className="w-3.5 h-3.5 text-slate-500" />;
    }
  };

  if (!selectedCaseId) {
    return (
      <div className="flex flex-col items-center justify-center h-80 text-center rounded-2xl border border-border-color bg-bg-card shadow-[0_4px_10px_rgba(15,23,42,0.06)]">
        <Folder className="w-12 h-12 text-text-muted mb-3" />
        <h3 className="text-sm font-bold text-text-primary uppercase tracking-wider">No Active Case File</h3>
        <p className="text-xs text-text-secondary max-w-xs mt-1">Select a case to query the AI Investigation Copilot.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-stretch h-[calc(100vh-140px)]">
      
      {/* Tabbed Sidebar */}
      <div className="glass-panel p-4 flex flex-col justify-between h-full overflow-y-auto">
        <div className="space-y-4">
          <div className="flex border-b border-border-color pb-1">
            <button
              onClick={() => setActiveSidebarTab('queries')}
              className={`flex-1 text-center pb-2 text-[10px] font-bold uppercase tracking-wider ${activeSidebarTab === 'queries' ? 'text-brand-primary border-b-2 border-brand-primary' : 'text-text-muted hover:text-text-secondary'}`}
            >
              Quick Queries
            </button>
            <button
              onClick={() => setActiveSidebarTab('recs')}
              className={`flex-1 text-center pb-2 text-[10px] font-bold uppercase tracking-wider ${activeSidebarTab === 'recs' ? 'text-brand-primary border-b-2 border-brand-primary' : 'text-text-muted hover:text-text-secondary'}`}
            >
              Forensic Tips
            </button>
          </div>

          {activeSidebarTab === 'queries' ? (
            <div className="space-y-2">
              <button
                onClick={() => handleQuickQuery("Summarize this investigation case.")}
                className="w-full p-2.5 bg-slate-50 dark:bg-slate-900 hover:bg-brand-50 hover:text-brand-600 dark:hover:bg-brand-950/20 text-left rounded-lg border border-slate-100 dark:border-slate-800 text-[10px] font-semibold text-slate-700 dark:text-slate-300 transition-colors"
              >
                "Summarize this case"
              </button>
              <button
                onClick={() => handleQuickQuery("What happened after the phishing SMS was received?")}
                className="w-full p-2.5 bg-slate-50 dark:bg-slate-900 hover:bg-brand-50 hover:text-brand-600 dark:hover:bg-brand-950/20 text-left rounded-lg border border-slate-100 dark:border-slate-800 text-[10px] font-semibold text-slate-700 dark:text-slate-300 transition-colors"
              >
                "Analyze phishing sequence"
              </button>
              <button
                onClick={() => handleQuickQuery("List all geographic location anomalies in the evidence.")}
                className="w-full p-2.5 bg-slate-50 dark:bg-slate-900 hover:bg-brand-50 hover:text-brand-600 dark:hover:bg-brand-950/20 text-left rounded-lg border border-slate-100 dark:border-slate-800 text-[10px] font-semibold text-slate-700 dark:text-slate-300 transition-colors"
              >
                "Show GPS location anomalies"
              </button>
              <button
                onClick={() => handleQuickQuery("What apps were opened during atypical active hours?")}
                className="w-full p-2.5 bg-slate-50 dark:bg-slate-900 hover:bg-brand-50 hover:text-brand-600 dark:hover:bg-brand-950/20 text-left rounded-lg border border-slate-100 dark:border-slate-800 text-[10px] font-semibold text-slate-700 dark:text-slate-300 transition-colors"
              >
                "Show sensitive app launches"
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {recSummary && (
                <p className="text-[10px] text-text-secondary leading-relaxed border-b border-border-color pb-2 mb-2 font-semibold">
                  {recSummary}
                </p>
              )}
              {recommendations.length === 0 ? (
                <p className="text-[10px] text-text-muted py-2 font-semibold">No forensic tips calculated yet. Run analysis to compute recommendations.</p>
              ) : (
                <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                  {recommendations.map((r, idx) => (
                    <div key={idx} className="p-2.5 bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-lg space-y-1">
                      <div className="flex justify-between items-center">
                        <span className={`text-[8px] font-extrabold px-1.5 py-0.5 rounded uppercase tracking-wider ${r.priority === 'Critical' ? 'bg-red-500 text-white' : r.priority === 'High' ? 'bg-orange-500 text-white' : 'bg-blue-500 text-white'}`}>
                          {r.priority} Priority
                        </span>
                      </div>
                      <p className="text-[10px] font-bold text-text-primary leading-snug">{r.action}</p>
                      <p className="text-[9px] text-text-muted leading-relaxed font-semibold">{r.rationale}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="p-3 bg-brand-primary/10 border border-brand-primary/20 rounded-lg text-[10px] text-brand-primary leading-relaxed mt-4 font-semibold">
          <b>Privacy Note:</b> Embedding search operates locally via FAISS. Prompt answers are processed entirely on-premise to preserve chain of custody.
        </div>
      </div>

      {/* Chat Interface Container */}
      <div className="lg:col-span-3 glass-panel p-5 flex flex-col justify-between h-full">
        {/* Chat Header */}
        <div className="flex justify-between items-center border-b border-slate-100 dark:border-slate-800 pb-2.5 mb-3.5 shrink-0">
          <div className="flex items-center space-x-2">
            <Cpu className="w-4 h-4 text-brand-primary" />
            <h2 className="text-xs font-bold text-text-primary uppercase tracking-wider">AI Forensic Assistant</h2>
          </div>
          <button
            type="button"
            onClick={() => {
              setMessages([
                {
                  sender: 'ai',
                  text: 'Hello Investigator. I am the AIMCR Copilot. Ask me any question about the case, and I will search the FAISS vector index to provide grounded analysis citing the exact Evidence IDs.',
                  timestamp: new Date()
                }
              ]);
            }}
            className="text-[10px] font-bold text-text-muted hover:text-brand-danger flex items-center space-x-1 px-2.5 py-1 bg-slate-50 hover:bg-red-500/10 dark:bg-slate-900 border border-border-color rounded-md transition-colors"
            title="Reset conversation state"
          >
            <span>Clear Conversation</span>
          </button>
        </div>

        {/* Messages list */}
        <div className="flex-1 overflow-y-auto space-y-4 pr-2 mb-4">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] rounded-xl p-3.5 text-xs shadow-sm leading-relaxed ${msg.sender === 'user' ? 'bg-brand-500 text-white rounded-br-none' : 'bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-800 text-slate-700 dark:text-slate-300 rounded-bl-none'}`}>
                <div className="whitespace-pre-line font-semibold">{msg.text}</div>
                
                {msg.confidence && (
                  <div className="mt-2.5 text-[9px] font-bold flex items-center space-x-1">
                    <span className="text-slate-400 dark:text-slate-500 uppercase tracking-wider">AI Confidence:</span>
                    <span className={`px-1.5 py-0.5 rounded text-[8px] uppercase ${
                      msg.confidence === 'High' ? 'bg-brand-success/10 text-brand-success border border-brand-success/20' :
                      msg.confidence === 'Medium' ? 'bg-brand-warning/10 text-brand-warning border border-brand-warning/20' :
                      'bg-brand-danger/10 text-brand-danger border border-brand-danger/20'
                    }`}>
                      {msg.confidence}
                    </span>
                  </div>
                )}
                
                {msg.limitations && msg.limitations.length > 0 && (
                  <div className="mt-2.5 text-[9px]">
                    <span className="text-slate-400 dark:text-slate-500 uppercase tracking-wider block font-bold mb-1">Evidence Gaps / Limitations</span>
                    <ul className="list-disc pl-3 text-[9px] text-text-secondary leading-snug space-y-0.5 font-medium">
                      {msg.limitations.map((lim: string, lIdx: number) => (
                        <li key={lIdx}>{lim}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Evidence citations */}
                {msg.evidence && msg.evidence.length > 0 && (
                  <div className="mt-3 pt-2 border-t border-slate-200/50 dark:border-slate-800/50">
                    <span className="text-[9px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block mb-1.5">Grounded Evidence Sources</span>
                    <div className="flex flex-wrap gap-1.5">
                      {msg.evidence.map((ev: any) => (
                        <button
                          key={ev.id}
                          onClick={() => {
                            // Redirect to timeline with selected evidence via URL parameter (survives refresh)
                            navigate(`/timeline?evidenceId=${ev.id}`);
                          }}
                          className="flex items-center space-x-1 px-2 py-0.5 bg-card-secondary hover:bg-card border border-border-color rounded hover:border-brand-primary/40 transition-colors text-[9px] font-mono text-brand-primary font-bold"
                          title="Click to view in timeline inspector"
                        >
                          {getArtifactIcon(ev.artifact_type)}
                          <span>{ev.id.slice(0, 8)}...</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-xl rounded-bl-none p-3.5 text-xs flex items-center space-x-2">
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-brand-500" />
                <span className="text-slate-400 font-semibold">Generating grounded explanation...</span>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Input Bar Form */}
        <form onSubmit={handleAskCopilot} className="flex items-center space-x-2 border-t border-slate-100 dark:border-slate-800 pt-3 shrink-0">
          <input
            type="text"
            disabled={loading}
            placeholder="Ask AI Copilot about the case..."
            className="glass-input flex-1 text-xs py-2 text-text-primary bg-input-bg border-border-color"
            value={input}
            onChange={e => setInput(e.target.value)}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="p-2 bg-brand-500 hover:bg-brand-600 disabled:opacity-50 text-white rounded-lg transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>

    </div>
  );
}
