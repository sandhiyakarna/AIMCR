import React, { useEffect, useRef, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import axios from 'axios';
import { AlertTriangle, CheckCircle2, Download, FilePenLine, Fingerprint, KeyRound, Lock, Plus, RefreshCw, Save, Search, ShieldCheck, Trash2, UploadCloud, FileText } from 'lucide-react';
import { useToast } from '../context/ToastContext';
import { buildReportPages, downloadEditableWordDocument } from '../services/reportDocument';
import { API_BASE_URL } from '../config';

interface OutletContextType {
  selectedCaseId: string;
  selectedCase: any;
}

export function ReportGeneration() {
  const { selectedCaseId, selectedCase } = useOutletContext<OutletContextType>();
  const { showToast } = useToast();
  const editorRefs = useRef<Array<HTMLDivElement | null>>([]);
  const [reportData, setReportData] = useState<any>({ evidence: [], anomalies: [], reconstructions: [], graphData: {}, summaryData: null });
  const [loading, setLoading] = useState(false);
  const [generatingPdf, setGeneratingPdf] = useState(false);
  const [lastSaved, setLastSaved] = useState('Not saved yet');
  const [pages, setPages] = useState<string[]>([]);
  const [masterCaseId, setMasterCaseId] = useState('');
  const [mfaVerified, setMfaVerified] = useState(false);
  const [fidoVerified, setFidoVerified] = useState(false);
  const [dscVerified, setDscVerified] = useState(false);
  const [secureAccessGranted, setSecureAccessGranted] = useState(false);
  const [locked, setLocked] = useState(false);
  const [indicators, setIndicators] = useState<Array<{ type: string; value: string }>>([{ type: 'IP address', value: '' }]);
  const [legalAct, setLegalAct] = useState('Information Technology Act, 2000');
  const [legalSection, setLegalSection] = useState('Section 66C - Identity theft');
  const [checklist, setChecklist] = useState({ fir: false, chain: false, section65B: false, seizure: false });
  const [attachments, setAttachments] = useState<Array<{ name: string; hash: string; verified: boolean }>>([]);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [auditEventCount, setAuditEventCount] = useState(0);

  const writeAuditEvent = async (action: string, details: string) => {
    if (!selectedCaseId) return;
    const key = `aimcr-secure-audit-${selectedCaseId}`;
    const events = JSON.parse(localStorage.getItem(key) || '[]') as Array<{ action: string; details: string; timestamp: string; previousHash: string; hash: string }>;
    const previousHash = events.at(-1)?.hash || 'GENESIS';
    const timestamp = new Date().toISOString();
    const payload = `${previousHash}|${timestamp}|${action}|${details}`;
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(payload));
    const hash = Array.from(new Uint8Array(digest)).map(byte => byte.toString(16).padStart(2, '0')).join('');
    events.push({ action, details, timestamp, previousHash, hash });
    localStorage.setItem(key, JSON.stringify(events));
    setAuditEventCount(events.length);
  };

  const loadReportData = async () => {
    if (!selectedCaseId) return;
    setLoading(true);
    try {
      const [evidence, anomalies, reconstructions, graphData, summaryData] = await Promise.all([
        axios.get(`/api/evidence/case/${selectedCaseId}`),
        axios.get(`/api/analyze/anomalies/${selectedCaseId}`),
        axios.get(`/api/timeline/reconstruct/${selectedCaseId}`),
        axios.get(`/api/analyze/graph/${selectedCaseId}`),
        axios.get(`/api/analyze/summary/${selectedCaseId}`).catch(() => ({ data: null }))
      ]);
      setReportData({ evidence: evidence.data, anomalies: anomalies.data, reconstructions: reconstructions.data, graphData: graphData.data, summaryData: summaryData.data });
    } catch {
      showToast('Unable to load case data for report generation.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (secureAccessGranted) {
      loadReportData();
    }
  }, [selectedCaseId, secureAccessGranted]);

  useEffect(() => {
    if (secureAccessGranted && selectedCaseId && !loading) {
      const savedDraft = localStorage.getItem(`aimcr-report-${selectedCaseId}`);
      try {
        setPages(savedDraft ? JSON.parse(savedDraft) : buildReportPages({ caseFile: selectedCase, ...reportData }));
      } catch {
        setPages(buildReportPages({ caseFile: selectedCase, ...reportData }));
      }
      setMasterCaseId(selectedCase?.master_case_id || selectedCaseId);
      setLocked(Boolean(localStorage.getItem(`aimcr-report-locked-${selectedCaseId}`)));
      const auditEvents = JSON.parse(localStorage.getItem(`aimcr-secure-audit-${selectedCaseId}`) || '[]');
      setAuditEventCount(auditEvents.length);
      void writeAuditEvent('VIEW_REPORT', 'Report workspace opened after secure access verification');
      setLastSaved('Auto-generated from current case data');
    }
  }, [selectedCaseId, selectedCase, reportData, loading]);

  const saveDraft = () => {
    if (!selectedCaseId || locked) return;
    const currentPages = editorRefs.current.map((editor, index) => editor?.innerHTML || pages[index] || '');
    setPages(currentPages);
    localStorage.setItem(`aimcr-report-${selectedCaseId}`, JSON.stringify(currentPages));
    void writeAuditEvent('EDIT_REPORT', 'Editable report draft saved');
    setLastSaved(`Draft saved ${new Date().toLocaleTimeString()}`);
    showToast('Editable report draft saved locally.', 'success');
  };

  const exportReport = () => {
    if (!selectedCaseId) return;
    const currentPages = editorRefs.current.map((editor, index) => editor?.innerHTML || pages[index] || '');
    downloadEditableWordDocument(selectedCase?.title || 'investigation', currentPages.join('<div style="page-break-after:always"></div>'));
    showToast('Editable Word report exported.', 'success');
  };

  const downloadPdfReport = async () => {
    if (!selectedCaseId) return;
    setGeneratingPdf(true);
    try {
      const res = await axios.post(`/api/report/generate/${selectedCaseId}`);
      const reportId = res.data.report_id;
      if (reportId) {
        const token = localStorage.getItem('aimcr_token');
        window.open(`${API_BASE_URL}/api/report/download/${reportId}?token=${token}`, '_blank');
        showToast('PDF Investigation Report generated and download started.', 'success');
      } else {
        showToast('Report generated successfully.', 'success');
      }
    } catch (e: any) {
      showToast(e.response?.data?.detail || 'Failed to generate PDF report.', 'error');
    } finally {
      setGeneratingPdf(false);
    }
  };

  const updatePage = (index: number, html: string) => {
    if (locked) return;
    setPages(current => current.map((page, pageIndex) => pageIndex === index ? html : page));
  };

  const addPage = () => {
    if (locked) return;
    setPages(current => [...current, '<p class="report-kicker">ADDITIONAL REPORT PAGE</p><h2>New Section</h2><p>Click here to add case-specific content.</p>']);
    void writeAuditEvent('EDIT_REPORT', 'Additional report page created');
  };

  const removePage = (index: number) => {
    if (pages.length === 1 || locked) return;
    setPages(current => current.filter((_, pageIndex) => pageIndex !== index));
  };

  const addIndicator = () => !locked && setIndicators(current => [...current, { type: 'IP address', value: '' }]);
  const updateIndicator = (index: number, field: 'type' | 'value', value: string) => setIndicators(current => current.map((row, rowIndex) => rowIndex === index ? { ...row, [field]: value } : row));
  const indicatorMatches = indicators.filter(row => row.value.trim().length > 0 && (row.value.includes('185.') || indicators.filter(item => item.value === row.value).length > 1));

  const hashAttachment = async (file: File) => {
    const buffer = await file.arrayBuffer();
    const digest = await crypto.subtle.digest('SHA-256', buffer);
    const hash = Array.from(new Uint8Array(digest)).map(byte => byte.toString(16).padStart(2, '0')).join('');
    setAttachments(current => [...current, { name: file.name, hash, verified: false }]);
  };

  const validateReport = () => {
    const errors: string[] = [];
    if (!masterCaseId.trim()) errors.push('Master Case ID is required.');
    if (!mfaVerified || !fidoVerified || !dscVerified) errors.push('MFA, FIDO2 handshake, and DSC simulation must all be verified.');
    if (!checklist.fir || !checklist.chain || !checklist.section65B || !checklist.seizure) errors.push('Complete the FIR, seizure, chain-of-custody, and Section 65B checklist.');
    if (!attachments.length || attachments.some(file => !file.verified)) errors.push('Attach evidence and verify each Section 65B record.');
    if (!indicators.some(row => row.value.trim())) errors.push('Add at least one technical indicator.');
    setValidationErrors(errors);
    return errors;
  };

  const approveAndLock = () => {
    const errors = validateReport();
    if (errors.length) {
      showToast('Final approval blocked: complete the validation checklist.', 'warning');
      return;
    }
    setLocked(true);
    localStorage.setItem(`aimcr-report-locked-${selectedCaseId}`, new Date().toISOString());
    void writeAuditEvent('FINAL_APPROVAL', 'DSC-approved report write-lock activated');
    showToast('DSC-approved final report locked for write protection.', 'success');
  };

  const openSecureReport = () => {
    if (!mfaVerified || !fidoVerified || !dscVerified) {
      showToast('Complete MFA, FIDO2, and DSC verification before opening the report workspace.', 'warning');
      return;
    }
    setSecureAccessGranted(true);
    void writeAuditEvent('SECURE_ACCESS_GRANTED', 'MFA, FIDO2, and DSC verification completed');
  };

  if (!selectedCaseId) {
    return <div className="glass-panel p-10 text-center text-sm text-text-secondary">Select or create a case file to generate its report.</div>;
  }

  const factorItems: Array<{ label: string; verified: boolean; setter: React.Dispatch<React.SetStateAction<boolean>>; icon: React.ReactNode }> = [
    { label: 'MFA verification', verified: mfaVerified, setter: setMfaVerified, icon: <KeyRound className="w-5 h-5" /> },
    { label: 'FIDO2 handshake', verified: fidoVerified, setter: setFidoVerified, icon: <Fingerprint className="w-5 h-5" /> },
    { label: 'DSC token verification', verified: dscVerified, setter: setDscVerified, icon: <Lock className="w-5 h-5" /> }
  ];

  if (!secureAccessGranted) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <section className="glass-panel w-full max-w-2xl p-6 md:p-10 space-y-7">
          <div className="text-center space-y-3">
            <div className="mx-auto w-14 h-14 rounded-full bg-brand-primary/10 text-brand-primary flex items-center justify-center"><ShieldCheck className="w-7 h-7" /></div>
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-brand-primary">Restricted report workspace</p>
            <h1 className="text-2xl font-bold text-text-primary font-serif">Secure report access</h1>
            <p className="text-xs text-text-secondary max-w-md mx-auto">Verify all required security factors before the case report workspace is opened.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {factorItems.map(({ label, verified, setter, icon }) => (
              <button key={label} onClick={() => setter(true)} className={`flex flex-col items-center gap-3 p-4 text-center rounded-lg border transition-colors ${verified ? 'border-brand-success/40 bg-brand-success/5 text-brand-success' : 'border-border-color bg-bg-secondary text-text-secondary hover:border-brand-primary'}`}>
                {icon}
                <span className="text-xs font-semibold">{label}</span>
                <span className="text-[10px]">{verified ? 'Verified' : 'Verify factor'}</span>
                {verified && <CheckCircle2 className="w-4 h-4" />}
              </button>
            ))}
          </div>
          <div className="flex flex-col items-center gap-3">
            <button onClick={openSecureReport} className="flex items-center gap-2 px-5 py-2.5 bg-brand-primary hover:bg-brand-primary-hover text-white text-xs font-semibold rounded-lg disabled:opacity-50" disabled={!mfaVerified || !fidoVerified || !dscVerified}><ShieldCheck className="w-4 h-4" /> Open secure report workspace</button>
            <p className="text-[10px] text-text-muted">Access event is recorded in the report audit chain.</p>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="flex items-center gap-2 text-brand-primary text-[10px] font-bold uppercase tracking-[0.18em]"><FilePenLine className="w-4 h-4" /> Report generation portal</div>
          <h1 className="mt-2 text-2xl font-bold text-text-primary font-serif">Editable case report</h1>
          <p className="mt-1 text-xs text-text-secondary">IIF-5 final-report workspace with Unicode and bilingual-ready content.</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={loadReportData} disabled={loading} className="flex items-center gap-2 px-3 py-2 text-xs font-semibold text-text-secondary border border-border-color rounded-lg hover:bg-hover-row disabled:opacity-50"><RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Regenerate</button>
          <button onClick={saveDraft} disabled={locked} className="flex items-center gap-2 px-3 py-2 text-xs font-semibold text-text-secondary border border-border-color rounded-lg hover:bg-hover-row disabled:opacity-40"><Save className="w-4 h-4" /> Save draft</button>
          <button onClick={downloadPdfReport} disabled={generatingPdf} className="flex items-center gap-2 px-3 py-2 bg-card-secondary hover:bg-card border border-border-color text-text-primary text-xs font-semibold rounded-lg disabled:opacity-50"><FileText className={`w-4 h-4 ${generatingPdf ? 'animate-spin' : 'text-brand-primary'}`} /> {generatingPdf ? 'Generating PDF...' : 'Download Official PDF'}</button>
          <button onClick={exportReport} className="flex items-center gap-2 px-3 py-2 bg-brand-primary hover:bg-brand-primary-hover text-white text-xs font-semibold rounded-lg shadow-[0_10px_20px_rgba(37,99,235,0.2)]"><Download className="w-4 h-4" /> Export court-ready Word</button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 text-[10px] text-text-muted"><ShieldCheck className="w-4 h-4 text-brand-success" /> {locked ? 'FINAL REPORT LOCKED' : lastSaved} <span className="ml-auto">{locked ? 'Read-only court-ready preview' : 'Complete security validation before sign-off'}</span></div>

      <section className="glass-panel p-5 space-y-4">
        <div className="flex items-center justify-between"><div><h2 className="text-sm font-bold text-text-primary uppercase tracking-wider">Case intake & control</h2><p className="text-xs text-text-secondary mt-1">Workspace access verified. Continue preparing the controlled report.</p></div><span className={`text-[10px] font-bold px-2 py-1 rounded-full ${locked ? 'bg-brand-success/10 text-brand-success' : 'bg-brand-warning/10 text-brand-warning'}`}>{locked ? 'WRITE-LOCK ACTIVE' : 'DRAFT / CONTROLLED'}</span></div>
        <div className="flex flex-col md:flex-row gap-3"><label className="text-xs font-semibold text-text-secondary flex-1">Master Case ID<input value={masterCaseId} disabled={locked} onChange={event => setMasterCaseId(event.target.value)} className="glass-input mt-1 w-full text-xs" placeholder="Enter FIR / master case reference" /></label><div className="flex items-end"><button onClick={() => showToast(`Prior records linked for ${masterCaseId || 'the case'}.`, 'info')} disabled={locked || !masterCaseId} className="flex items-center gap-2 px-3 py-2 text-xs font-semibold border border-border-color rounded-lg hover:bg-hover-row disabled:opacity-40"><Search className="w-4 h-4" /> Fetch prior FIR, arrest & seizure records</button></div></div>
      </section>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <section className="glass-panel p-5 space-y-4"><div className="flex justify-between items-center"><div><h2 className="text-sm font-bold text-text-primary uppercase tracking-wider">Technical indicators</h2><p className="text-xs text-text-secondary mt-1">NCRP / Cri-MAC cross-match simulation</p></div><button onClick={addIndicator} disabled={locked} className="flex items-center gap-1 text-xs font-semibold text-brand-primary disabled:opacity-40"><Plus className="w-4 h-4" /> Add row</button></div>{indicators.map((row, index) => <div key={index} className="flex gap-2"><select value={row.type} disabled={locked} onChange={event => updateIndicator(index, 'type', event.target.value)} className="glass-input text-xs w-36"><option>IP address</option><option>MAC address</option><option>IMEI</option><option>Crypto wallet hash</option><option>Bank account</option></select><input value={row.value} disabled={locked} onChange={event => updateIndicator(index, 'value', event.target.value)} className="glass-input text-xs flex-1" placeholder="Indicator value" /></div>)}{indicatorMatches.length > 0 && <div className="flex items-start gap-2 p-3 rounded-lg bg-brand-warning/10 border border-brand-warning/20 text-brand-warning text-xs"><AlertTriangle className="w-4 h-4 shrink-0" /><span><strong>Cross-case link flagged.</strong> {indicatorMatches.length} indicator(s) match simulated multi-case or cross-jurisdiction records.</span></div>}</section>
        <section className="glass-panel p-5 space-y-4"><div><h2 className="text-sm font-bold text-text-primary uppercase tracking-wider">Legal mapping & compliance</h2><p className="text-xs text-text-secondary mt-1">Statutory mapping drives the procedural checklist.</p></div><div className="grid grid-cols-1 sm:grid-cols-2 gap-2"><select value={legalAct} disabled={locked} onChange={event => setLegalAct(event.target.value)} className="glass-input text-xs"><option>Information Technology Act, 2000</option><option>Bharatiya Nyaya Sanhita, 2023</option><option>Indian Penal Code, 1860</option></select><select value={legalSection} disabled={locked} onChange={event => setLegalSection(event.target.value)} className="glass-input text-xs"><option>Section 66C - Identity theft</option><option>Section 66D - Cheating by personation</option><option>Section 43 - Unauthorized access</option></select></div><div className="p-3 rounded-lg bg-bg-secondary border border-border-color text-xs text-text-secondary"><strong className="text-text-primary">{legalSection}</strong><p className="mt-1">Dishonestly or fraudulently making use of the electronic signature, password or any other unique identification feature of another person.</p></div><div className="grid grid-cols-1 sm:grid-cols-2 gap-2">{[['fir', 'FIR / master case linked'], ['arrest', 'Arrest memo linked'], ['seizure', 'Seizure log linked'], ['chain', 'Chain of custody verified'], ['section65B', 'Section 65B certificate verified']].map(([key, label]) => <label key={key} className="flex items-center gap-2 text-xs text-text-secondary"><input type="checkbox" disabled={locked} checked={checklist[key as keyof typeof checklist]} onChange={event => setChecklist(current => ({ ...current, [key]: event.target.checked }))} /> {label}</label>)}</div></section>
      </div>

      <section className="glass-panel p-5 space-y-4"><div className="flex justify-between items-center"><div><h2 className="text-sm font-bold text-text-primary uppercase tracking-wider">Evidence attachments & Section 65B</h2><p className="text-xs text-text-secondary mt-1">SHA-256 is computed at upload and cannot be edited.</p></div><label className="flex items-center gap-2 px-3 py-2 text-xs font-semibold border border-border-color rounded-lg cursor-pointer hover:bg-hover-row"><UploadCloud className="w-4 h-4" /> Attach evidence<input type="file" className="hidden" disabled={locked} onChange={event => event.target.files?.[0] && hashAttachment(event.target.files[0])} /></label></div>{attachments.length === 0 ? <p className="text-xs text-text-muted">No new attachments. Existing case evidence is loaded into the report.</p> : attachments.map((file, index) => <div key={file.hash} className="flex flex-wrap items-center gap-3 p-3 bg-bg-secondary rounded-lg border border-border-color"><span className="text-xs font-semibold text-text-primary flex-1">{file.name}<small className="block text-[10px] text-text-muted font-mono mt-1">SHA-256: {file.hash}</small></span><label className="text-xs text-text-secondary"><input type="checkbox" disabled={locked} checked={file.verified} onChange={event => setAttachments(current => current.map((item, itemIndex) => itemIndex === index ? { ...item, verified: event.target.checked } : item))} /> 65B verified</label></div>)}</section>

      <section className="glass-panel p-5 space-y-3"><div className="flex items-center justify-between"><div><h2 className="text-sm font-bold text-text-primary uppercase tracking-wider">Pre-submission validation</h2><p className="text-xs text-text-secondary mt-1">All controls must pass before cryptographic approval.</p></div><button onClick={approveAndLock} disabled={locked} className="flex items-center gap-2 px-3 py-2 bg-brand-success hover:opacity-90 text-white text-xs font-semibold rounded-lg disabled:opacity-40"><Lock className="w-4 h-4" /> Validate & DSC approve</button></div>{validationErrors.length > 0 && <ul className="space-y-1 text-xs text-brand-danger">{validationErrors.map(error => <li key={error} className="flex items-center gap-2"><AlertTriangle className="w-3.5 h-3.5" /> {error}</li>)}</ul>}{validationErrors.length === 0 && <p className="text-xs text-text-muted">Validator ready. Run approval to check mandatory parameters.</p>}</section>

      <div className="report-editor-shell rounded-xl border border-border-color bg-slate-200/70 dark:bg-slate-950/40 p-4 md:p-8 overflow-auto">
        <div className="mx-auto max-w-4xl space-y-6">
          {pages.map((page, index) => (
            <section key={`${selectedCaseId}-${index}`} className="report-page relative">
              <div className="report-page-toolbar"><span>Page {index + 1} of {pages.length}</span><button onClick={() => removePage(index)} disabled={pages.length === 1} title="Remove page" className="text-text-muted hover:text-brand-danger disabled:opacity-30"><Trash2 className="w-3.5 h-3.5" /></button></div>
              <div ref={element => { editorRefs.current[index] = element; }} contentEditable={!locked} suppressContentEditableWarning onInput={event => updatePage(index, event.currentTarget.innerHTML)} dangerouslySetInnerHTML={{ __html: page }} className="report-editor min-h-[900px] bg-white text-slate-800 shadow-[0_12px_35px_rgba(15,23,42,0.16)] px-8 py-10 md:px-16 md:py-14 outline-none" />
            </section>
          ))}
          <button onClick={addPage} className="mx-auto flex items-center gap-2 px-4 py-2 text-xs font-semibold text-text-secondary border border-dashed border-border-strong rounded-lg hover:border-brand-primary hover:text-brand-primary"><Plus className="w-4 h-4" /> Add report page</button>
        </div>
      </div>
      <p className="text-[10px] text-text-muted text-right">Tamper-evident local audit chain: {auditEventCount} event(s) recorded for this report.</p>
    </div>
  );
}
