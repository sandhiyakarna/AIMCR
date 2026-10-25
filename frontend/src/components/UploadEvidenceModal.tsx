import React, { useState, useRef } from 'react';
import { Modal } from './Modal';
import axios from 'axios';
import { useToast } from '../context/ToastContext';
import { Upload, FileText, Check, AlertCircle, Loader2, X } from 'lucide-react';

interface UploadEvidenceModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  onEvidenceUploaded: () => void;
}

export function UploadEvidenceModal({ isOpen, onClose, caseId, onEvidenceUploaded }: UploadEvidenceModalProps) {
  const [artifactType, setArtifactType] = useState('SMS');
  const [files, setFiles] = useState<File[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadResults, setUploadResults] = useState<{ success?: number; uploaded?: number; failed: number; errors: string[] } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { showToast } = useToast();

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const newFiles = Array.from(e.dataTransfer.files);
      setFiles(prev => [...prev, ...newFiles]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files);
      setFiles(prev => [...prev, ...newFiles]);
    }
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const clearFiles = () => {
    setFiles([]);
    setUploadResults(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (files.length === 0 || !caseId) return;

    setUploading(true);
    setUploadProgress(0);
    setUploadResults(null);

    if (files.length === 1) {
      // Single file upload via existing endpoint
      const formData = new FormData();
      formData.append('case_id', caseId);
      formData.append('artifact_type', artifactType);
      formData.append('file', files[0]);

      try {
        await axios.post('/api/evidence/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (progressEvent) => {
            if (progressEvent.total) {
              setUploadProgress(Math.round((progressEvent.loaded * 100) / progressEvent.total));
            }
          },
        });
        showToast('Forensic file uploaded and integrity validated (SHA-256)', 'success');
        uploadResults?.success ? uploadResults.success++ : 0;
        setUploadResults({ success: 1, failed: 0, errors: [] });
        onEvidenceUploaded();
        clearFiles();
        onClose();
      } catch (err: any) {
        const errMsg = err.response?.data?.detail || 'Failed to upload evidence';
        showToast(errMsg, 'error');
        setUploadResults({ success: 0, failed: 1, errors: [errMsg] });
      } finally {
        setUploading(false);
      }
    } else {
      // Bulk upload via new endpoint
      const formData = new FormData();
      formData.append('case_id', caseId);
      formData.append('artifact_type', artifactType);
      files.forEach(file => formData.append('files', file));

      try {
        const res = await axios.post('/api/evidence/upload-bulk', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (progressEvent) => {
            if (progressEvent.total) {
              setUploadProgress(Math.round((progressEvent.loaded * 100) / progressEvent.total));
            }
          },
        });
        const result = res.data;
        setUploadResults(result);
        showToast(`Bulk upload complete: ${result.uploaded} uploaded, ${result.failed} failed`, 'success');
        onEvidenceUploaded();
        clearFiles();
        onClose();
      } catch (err: any) {
        const errMsg = err.response?.data?.detail || 'Failed to upload evidence';
        showToast(errMsg, 'error');
        setUploadResults({ success: 0, failed: files.length, errors: [errMsg] });
      } finally {
        setUploading(false);
      }
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Upload Forensic Evidence">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1">
            Forensic Artifact Category
          </label>
          <select
            className="w-full glass-input text-xs font-semibold text-text-primary"
            value={artifactType}
            onChange={(e) => setArtifactType(e.target.value)}
          >
            <option value="SMS">SMS Backup Logs</option>
            <option value="Call">Call Log History</option>
            <option value="GPS">GPS Geolocation Coords</option>
            <option value="BrowserHistory">Browser History DB</option>
            <option value="Application">Application Usage Logs</option>
            <option value="File">Modified System Files</option>
            <option value="Contact">Device Contact Book</option>
            <option value="Notification">Notification Logs</option>
            <option value="WiFi">WiFi Network Logs</option>
            <option value="Bluetooth">Bluetooth Device Logs</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1">
            Evidence File(s)
          </label>
          
          <div
            onDragEnter={handleDrag}
            onDragOver={handleDrag}
            onDragLeave={handleDrag}
            onDrop={handleDrop}
            onClick={() => !uploading && fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors duration-200 ${
              dragActive
                ? 'border-brand-primary bg-brand-primary/10'
                : 'border-border-color hover:border-brand-primary/50'
            } ${uploading ? 'pointer-events-none opacity-60' : ''}`}
          >
            <input
              type="file"
              ref={fileInputRef}
              className="hidden"
              multiple
              onChange={handleFileChange}
              accept=".json,.txt,.csv,.db,.xml,.log,.zip,.tar,.gz"
            />
            
            {files.length > 0 ? (
              <div className="flex flex-col items-center space-y-2">
                <Check className="w-8 h-8 text-brand-success" />
                <p className="text-xs font-bold text-text-primary">
                  {files.length} file(s) selected
                </p>
              </div>
            ) : (
              <div className="flex flex-col items-center space-y-2">
                <Upload className="w-8 h-8 text-text-muted" />
                <p className="text-xs font-semibold text-text-secondary">
                  Drag & Drop forensic files here or <span className="text-brand-primary hover:underline">browse</span>
                </p>
                <p className="text-[9px] text-text-muted uppercase font-bold">
                  Supports multiple files, archives, and common forensic formats
                </p>
              </div>
            )}
          </div>

          {/* File list */}
          {files.length > 0 && (
            <div className="mt-3 space-y-1 max-h-32 overflow-y-auto">
              {files.map((file, idx) => (
                <div key={idx} className="flex items-center justify-between p-2 bg-bg-secondary rounded-lg border border-border-color">
                  <div className="flex items-center space-x-2 min-w-0">
                    <FileText className="w-3.5 h-3.5 text-text-muted shrink-0" />
                    <span className="text-[10px] font-semibold text-text-primary truncate">{file.name}</span>
                    <span className="text-[9px] text-text-muted">({(file.size / 1024).toFixed(1)} KB)</span>
                  </div>
                  {!uploading && (
                    <button type="button" onClick={() => removeFile(idx)} className="p-0.5 hover:bg-bg-card rounded">
                      <X className="w-3 h-3 text-text-muted" />
                    </button>
                  )}
                </div>
              ))}
              {files.length > 1 && !uploading && (
                <button type="button" onClick={clearFiles} className="text-[10px] text-brand-danger font-bold hover:underline">
                  Clear all files
                </button>
              )}
            </div>
          )}

          {/* Progress Bar */}
          {uploading && (
            <div className="mt-3">
              <div className="flex justify-between text-[10px] text-text-muted mb-1">
                <span>Uploading...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full h-2 bg-bg-secondary rounded-full overflow-hidden border border-border-color">
                <div
                  className="h-full bg-brand-primary rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* Upload Results */}
          {uploadResults && (
            <div className="mt-3 p-3 bg-bg-secondary rounded-xl border border-border-color space-y-1">
              <div className="flex items-center space-x-2">
                <Check className="w-4 h-4 text-brand-success" />
                <span className="text-xs font-bold text-brand-success">{uploadResults.success || uploadResults.uploaded} uploaded successfully</span>
              </div>
              {(uploadResults.failed > 0 || (uploadResults.errors && uploadResults.errors.length > 0)) && (
                <div className="flex items-start space-x-2">
                  <AlertCircle className="w-4 h-4 text-brand-danger shrink-0 mt-0.5" />
                  <span className="text-[10px] text-brand-danger">{uploadResults.failed} failed</span>
                </div>
              )}
              {uploadResults.errors && uploadResults.errors.slice(0, 3).map((err, i) => (
                <p key={i} className="text-[9px] text-text-muted pl-6">{err}</p>
              ))}
            </div>
          )}
        </div>

        <div className="p-3 bg-brand-warning/10 border border-brand-warning/30 rounded-xl flex gap-2.5">
          <AlertCircle className="w-4 h-4 text-brand-warning shrink-0 mt-0.5" />
          <p className="text-[10px] text-brand-warning leading-relaxed font-semibold">
            Uploading registers file metadata in SQLite case logs, routes files through parsers (including Notification/WiFi/Bluetooth parsers), and verifies evidence integrity using SHA-256 hashing.
          </p>
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
            disabled={uploading || files.length === 0}
            className="flex items-center space-x-2 px-4 py-2 text-xs font-bold text-white bg-brand-primary hover:bg-brand-primary-hover rounded-lg shadow-[0_12px_24px_rgba(37,99,235,0.24)] disabled:opacity-50 transition-all duration-150"
          >
            {uploading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Uploading {files.length} file(s)...</span>
              </>
            ) : (
              <span>Upload {files.length > 1 ? `${files.length} Files` : 'Evidence'}</span>
            )}
          </button>
        </div>
      </form>
    </Modal>
  );
}
