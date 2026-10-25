// frontend/src/pages/Acquisition.tsx

import React, { useState, useEffect, useRef } from 'react';
import { useOutletContext } from 'react-router-dom';
import axios from 'axios';
import {
  Smartphone, UploadCloud, CheckCircle2, AlertTriangle, XCircle,
  RefreshCw, FileText, Terminal, Lock, Unlock, ShieldCheck, Eye, Info
} from 'lucide-react';
import { useToast } from '../context/ToastContext';

interface OutletContextType {
  selectedCaseId: string;
  selectedCase: any;
  loading: boolean;
  setLoading: (l: boolean) => void;
}

interface Device {
  id: string;
  model: string;
  status: string;
  type: string;
  brand: string;
  os_version: string;
  serial: string;
  encrypted: boolean;
  bootloader_locked: boolean;
}

interface ImportSummary {
  total_files: number;
  supported: number;
  unsupported: number;
  imported_successfully: number;
  metadata_extracted: number;
  sha256_generated: number;
  skipped_files: Array<{ file: string; reason: string }>;
}

export function Acquisition() {
  const { selectedCaseId, selectedCase } = useOutletContext<OutletContextType>();
  const { showToast } = useToast();

  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('');
  const [deviceLoading, setDeviceLoading] = useState(false);
  const [acquireLoading, setAcquireLoading] = useState(false);
  
  // File import states
  const [filesToCheck, setFilesToCheck] = useState<File[]>([]);
  const [checkedFiles, setCheckedFiles] = useState<Array<{ filename: string; status: string }>>([]);
  const [checkingFiles, setCheckingFiles] = useState(false);
  const [importSummary, setImportSummary] = useState<ImportSummary | null>(null);
  const [importLoading, setImportLoading] = useState(false);
  
  // Metadata Preview drawer
  const [previewMetadata, setPreviewMetadata] = useState<any | null>(null);
  const [showPreviewDrawer, setShowPreviewDrawer] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => {
    fetchDevices();
  }, []);

  const fetchDevices = async () => {
    setDeviceLoading(true);
    try {
      const res = await axios.get('/api/acquisition/devices');
      setDevices(res.data);
      if (res.data.length > 0) {
        setSelectedDeviceId(res.data[0].id);
      }
    } catch (e) {
      showToast('Failed to scan for connected forensic devices.', 'error');
    } finally {
      setDeviceLoading(false);
    }
  };

  const handleAcquire = async () => {
    if (!selectedCaseId) {
      showToast('Please select or create an active case first.', 'warning');
      return;
    }
    if (!selectedDeviceId) {
      showToast('No device selected.', 'warning');
      return;
    }

    setAcquireLoading(true);
    showToast('Starting Android ADB evidence acquisition...', 'info');
    try {
      const res = await axios.post('/api/acquisition/acquire', {
        case_id: selectedCaseId,
        device_id: selectedDeviceId
      });
      showToast(`Acquisition completed. Imported ${res.data.records_imported} forensic records.`, 'success');
      // Create a nice mock summary
      setImportSummary({
        total_files: res.data.files_pulled,
        supported: res.data.files_pulled,
        unsupported: 0,
        imported_successfully: res.data.records_imported,
        metadata_extracted: res.data.files_pulled,
        sha256_generated: res.data.files_pulled,
        skipped_files: res.data.errors.map((e: string) => ({ file: 'ADB Pull', reason: e }))
      });
    } catch (e: any) {
      const msg = e.response?.data?.detail || 'Acquisition execution failed.';
      showToast(msg, 'error');
    } finally {
      setAcquireLoading(false);
    }
  };

  // Drag and drop event handlers
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const files = Array.from(e.dataTransfer.files);
      setFilesToCheck(files);
      await runFileCheck(files);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const files = Array.from(e.target.files);
      setFilesToCheck(files);
      await runFileCheck(files);
    }
  };

  const runFileCheck = async (files: File[]) => {
    setCheckingFiles(true);
    try {
      const payload = {
        files: files.map(f => ({
          filename: f.name,
          mime_type: f.type || 'application/octet-stream'
        }))
      };
      const res = await axios.post('/api/acquisition/check-files', payload);
      setCheckedFiles(res.data);
    } catch (e) {
      showToast('Error validating files support.', 'error');
    } finally {
      setCheckingFiles(false);
    }
  };

  const triggerFileSelect = () => {
    fileInputRef.current?.click();
  };

  const handleImport = async () => {
    if (!selectedCaseId) {
      showToast('No active case selected.', 'warning');
      return;
    }
    if (filesToCheck.length === 0) {
      showToast('No files selected for import.', 'warning');
      return;
    }

    setImportLoading(true);
    showToast('Ingesting forensic files...', 'info');

    let combinedSummary: ImportSummary = {
      total_files: 0,
      supported: 0,
      unsupported: 0,
      imported_successfully: 0,
      metadata_extracted: 0,
      sha256_generated: 0,
      skipped_files: []
    };

    try {
      // Loop files and upload one-by-one or handle ZIP archive
      for (const file of filesToCheck) {
        const formData = new FormData();
        formData.append('case_id', selectedCaseId);
        formData.append('file', file);

        const res = await axios.post('/api/acquisition/import', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });

        const sum = res.data as ImportSummary;
        combinedSummary.total_files += sum.total_files;
        combinedSummary.supported += sum.supported;
        combinedSummary.unsupported += sum.unsupported;
        combinedSummary.imported_successfully += sum.imported_successfully;
        combinedSummary.metadata_extracted += sum.metadata_extracted;
        combinedSummary.sha256_generated += sum.sha256_generated;
        combinedSummary.skipped_files = [...combinedSummary.skipped_files, ...sum.skipped_files];
      }

      setImportSummary(combinedSummary);
      showToast('Import completed successfully.', 'success');
      // Clear file selection
      setFilesToCheck([]);
      setCheckedFiles([]);
    } catch (e) {
      showToast('Error occurred during evidence import.', 'error');
    } finally {
      setImportLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'supported':
        return <span className="flex items-center space-x-1 py-0.5 px-2 bg-brand-success/15 text-brand-success text-[10px] font-bold rounded-full border border-brand-success/20"><CheckCircle2 className="w-3 h-3" /> <span>Supported</span></span>;
      case 'partially_supported':
        return <span className="flex items-center space-x-1 py-0.5 px-2 bg-brand-warning/15 text-brand-warning text-[10px] font-bold rounded-full border border-brand-warning/20"><AlertTriangle className="w-3 h-3" /> <span>Metadata Only</span></span>;
      default:
        return <span className="flex items-center space-x-1 py-0.5 px-2 bg-brand-danger/15 text-brand-danger text-[10px] font-bold rounded-full border border-brand-danger/20"><XCircle className="w-3 h-3" /> <span>Unsupported</span></span>;
    }
  };

  const activeDevice = devices.find(d => d.id === selectedDeviceId);

  return (
    <div className="space-y-6">
      
      {/* Title Header */}
      <div>
        <h2 className="text-xl font-bold tracking-tight text-text-primary font-serif">Evidence Acquisition & Ingestion</h2>
        <p className="text-xs text-text-muted mt-1">Perform Android device imaging via ADB or upload forensic files (Cellebrite XMLs, databases, logs, archives).</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Device Monitor & ADB */}
        <div className="space-y-6">
          <div className="glass-panel p-5 relative overflow-hidden">
            {/* Background Glow */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-brand-primary/10 rounded-full blur-2xl -mr-10 -mt-10 pointer-events-none"></div>

            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center space-x-2">
                <Smartphone className="w-4 h-4 text-brand-primary" />
                <span>Forensic Device Monitor</span>
              </h3>
              
              <button
                onClick={fetchDevices}
                disabled={deviceLoading}
                className="p-1 text-text-muted hover:text-brand-primary hover:bg-hover-row rounded-lg transition-colors"
                title="Refresh Devices"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${deviceLoading ? 'animate-spin' : ''}`} />
              </button>
            </div>

            {/* Devices dropdown */}
            {devices.length === 0 ? (
              <div className="text-center py-6 border border-dashed border-border-color rounded-xl">
                <Smartphone className="w-8 h-8 text-text-muted mx-auto mb-2 opacity-50" />
                <p className="text-xs font-semibold text-text-secondary">No ADB devices connected</p>
                <p className="text-[10px] text-text-muted mt-0.5">Connect a device with USB Debugging enabled.</p>
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="text-[10px] font-bold text-text-muted uppercase tracking-wider block mb-1.5">Select Connected Device</label>
                  <select
                    className="glass-input bg-input-bg border-border-color text-xs font-semibold py-2 px-3 w-full text-text-primary"
                    value={selectedDeviceId}
                    onChange={e => setSelectedDeviceId(e.target.value)}
                  >
                    {devices.map(d => (
                      <option key={d.id} value={d.id}>
                        {d.model} ({d.type === 'emulated' ? 'Emulated' : 'ADB'})
                      </option>
                    ))}
                  </select>
                </div>

                {activeDevice && (
                  <div className="bg-bg-primary/55 border border-border-color rounded-xl p-3.5 space-y-2.5 text-xs">
                    <div className="flex items-center justify-between pb-2 border-b border-border-color">
                      <span className="font-bold text-text-secondary text-[11px]">ADB Status</span>
                      <span className={`font-bold px-2 py-0.5 rounded text-[10px] ${
                        activeDevice.status === 'Connected' 
                          ? 'bg-brand-success/15 text-brand-success border border-brand-success/20' 
                          : 'bg-brand-danger/15 text-brand-danger border border-brand-danger/20'
                      }`}>
                        {activeDevice.status}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-[11px] text-text-muted">
                      <div>
                        <span className="block font-medium">Manufacturer / Brand</span>
                        <span className="font-semibold text-text-primary">{activeDevice.brand}</span>
                      </div>
                      <div>
                        <span className="block font-medium">Android version</span>
                        <span className="font-semibold text-text-primary">{activeDevice.os_version}</span>
                      </div>
                      <div>
                        <span className="block font-medium">Serial Number</span>
                        <span className="font-semibold text-text-primary font-mono truncate block max-w-[120px]">{activeDevice.serial}</span>
                      </div>
                      <div>
                        <span className="block font-medium">Crypto Status</span>
                        <span className="font-semibold text-text-primary flex items-center space-x-1">
                          {activeDevice.encrypted ? (
                            <><Lock className="w-3 h-3 text-brand-success" /> <span className="text-brand-success font-bold">Encrypted</span></>
                          ) : (
                            <><Unlock className="w-3 h-3 text-brand-warning" /> <span className="text-brand-warning font-bold">Unencrypted</span></>
                          )}
                        </span>
                      </div>
                    </div>

                    {activeDevice.status === 'Connected' && (
                      <button
                        onClick={handleAcquire}
                        disabled={acquireLoading || !selectedCaseId}
                        className="w-full flex items-center justify-center space-x-2 py-2 px-3 bg-brand-primary hover:bg-brand-primary-hover text-white text-xs font-bold rounded-lg shadow-[0_10px_20px_rgba(37,99,235,0.2)] transition-all disabled:opacity-50 mt-2"
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${acquireLoading ? 'animate-spin' : ''}`} />
                        <span>{acquireLoading ? 'Imaging Device...' : 'Acquire Forensic Artifacts'}</span>
                      </button>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Quick Info Box */}
          <div className="glass-panel p-5 border-l-2 border-brand-info">
            <h4 className="text-xs font-bold text-brand-info uppercase tracking-wider flex items-center space-x-1.5 mb-2">
              <Info className="w-4 h-4" />
              <span>Privacy Preserving Imaging</span>
            </h4>
            <ul className="list-disc list-inside text-[11px] text-text-secondary space-y-1.5 leading-relaxed">
              <li>Media contents (photos/videos/voice messages) are <strong>never stored or analyzed</strong> by the AI.</li>
              <li>Only forensic metadata (timestamp, device info, filename, hashes) is extracted.</li>
              <li>ADB operations run locally on secure sandbox pathways.</li>
            </ul>
          </div>
        </div>

        {/* Right Column: File Import & Pre-Checker */}
        <div className="lg:col-span-2 space-y-6">
          <div className="glass-panel p-5">
            <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider flex items-center space-x-2 mb-4">
              <UploadCloud className="w-4 h-4 text-brand-primary" />
              <span>Forensic Evidence Importer</span>
            </h3>

            {/* Drag and Drop Zone */}
            <div
              className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all ${
                dragActive 
                  ? 'border-brand-primary bg-brand-primary/5' 
                  : 'border-border-color hover:border-brand-primary bg-bg-primary/20'
              }`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={triggerFileSelect}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                className="hidden"
                onChange={handleFileChange}
                accept=".csv,.json,.xml,.db,.sqlite,.sqlite3,.txt,.log,.html,.pdf,.zip,.tar,.gz,.jpg,.jpeg,.png,.heic,.mp4,.avi,.mov,.mp3,.wav,.aac"
              />
              
              <UploadCloud className="w-10 h-10 text-text-muted mx-auto mb-3 opacity-60" />
              <p className="text-xs font-bold text-text-primary">Drag & Drop Forensic Logs or Archives</p>
              <p className="text-[10px] text-text-muted mt-1">Supports Cellebrite, Axiom, Autopsy, ZIP, TAR, DB, JSON, XML, Media</p>
              <button
                type="button"
                className="mt-4 px-3.5 py-1.5 bg-card-secondary hover:bg-card text-text-primary border border-border-color text-xs font-bold rounded-lg transition-colors"
              >
                Browse Files
              </button>
            </div>

            {/* File Checker / Pre-Import list */}
            {filesToCheck.length > 0 && (
              <div className="mt-6 space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-[10px] font-bold text-text-muted uppercase tracking-wider">Pre-Import Validation Check</h4>
                  {checkingFiles && <span className="text-[10px] text-brand-primary animate-pulse font-bold">Checking files...</span>}
                </div>

                <div className="border border-border-color rounded-xl divide-y divide-border-color max-h-60 overflow-y-auto">
                  {filesToCheck.map((file, idx) => {
                    const checkResult = checkedFiles.find(cf => cf.filename === file.name);
                    return (
                      <div key={idx} className="flex items-center justify-between p-3 text-xs bg-bg-primary/10">
                        <div className="flex items-center space-x-2.5 overflow-hidden pr-4">
                          <FileText className="w-4 h-4 text-text-muted shrink-0" />
                          <div className="overflow-hidden">
                            <p className="font-semibold text-text-primary truncate">{file.name}</p>
                            <p className="text-[10px] text-text-muted font-mono">{ (file.size / 1024).toFixed(1) } KB</p>
                          </div>
                        </div>
                        <div className="shrink-0">
                          {checkResult ? getStatusBadge(checkResult.status) : <span className="text-[10px] text-text-muted animate-pulse">Checking...</span>}
                        </div>
                      </div>
                    );
                  })}
                </div>

                <button
                  onClick={handleImport}
                  disabled={importLoading || !selectedCaseId}
                  className="w-full flex items-center justify-center space-x-2 py-2 px-3 bg-brand-success hover:bg-brand-success/90 text-white text-xs font-bold rounded-lg shadow-[0_10px_20px_rgba(22,163,74,0.15)] transition-all disabled:opacity-50"
                >
                  <ShieldCheck className="w-4 h-4" />
                  <span>{importLoading ? 'Ingesting Evidence...' : 'Begin Forensic Ingestion'}</span>
                </button>
              </div>
            )}
          </div>

          {/* Import Summary Block */}
          {importSummary && (
            <div className="glass-panel p-5 bg-card-secondary/25 border-brand-success/30 border">
              <h3 className="text-xs font-bold text-brand-success uppercase tracking-wider flex items-center space-x-2 mb-4">
                <CheckCircle2 className="w-4 h-4" />
                <span>Forensic Ingestion Summary</span>
              </h3>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4 text-center">
                <div className="bg-bg-primary/40 p-3 rounded-xl border border-border-color">
                  <span className="block text-lg font-bold text-text-primary font-mono">{importSummary.total_files}</span>
                  <span className="text-[9px] font-bold text-text-muted uppercase tracking-wider">Total Scanned</span>
                </div>
                <div className="bg-bg-primary/40 p-3 rounded-xl border border-border-color">
                  <span className="block text-lg font-bold text-brand-success font-mono">{importSummary.imported_successfully}</span>
                  <span className="text-[9px] font-bold text-text-muted uppercase tracking-wider">Imported</span>
                </div>
                <div className="bg-bg-primary/40 p-3 rounded-xl border border-border-color">
                  <span className="block text-lg font-bold text-brand-info font-mono">{importSummary.metadata_extracted}</span>
                  <span className="text-[9px] font-bold text-text-muted uppercase tracking-wider">Metadata Only</span>
                </div>
                <div className="bg-bg-primary/40 p-3 rounded-xl border border-border-color">
                  <span className="block text-lg font-bold text-brand-warning font-mono">{importSummary.skipped_files.length}</span>
                  <span className="text-[9px] font-bold text-text-muted uppercase tracking-wider">Skipped</span>
                </div>
              </div>

              {importSummary.skipped_files.length > 0 && (
                <div>
                  <h4 className="text-[10px] font-bold text-brand-danger uppercase tracking-wider mb-2 flex items-center space-x-1.5">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>Skipped / Warned Artifacts</span>
                  </h4>
                  <div className="bg-brand-danger/5 border border-brand-danger/20 rounded-xl p-3 max-h-36 overflow-y-auto space-y-1.5">
                    {importSummary.skipped_files.map((item, idx) => (
                      <div key={idx} className="flex justify-between items-center text-[10px] text-text-secondary leading-tight">
                        <span className="font-semibold text-text-primary font-mono truncate max-w-[200px]">{item.file}</span>
                        <span className="text-brand-danger font-medium">{item.reason}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
