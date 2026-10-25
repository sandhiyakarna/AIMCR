import React, { useState, useEffect } from 'react';
import { useTheme } from '../context/ThemeContext';
import { Settings as SettingsIcon, Sun, Moon, Shield, Info, Monitor, Bell, FileText, Cpu, BookOpen, CheckCircle2 } from 'lucide-react';
import { useToast } from '../context/ToastContext';

const SETTINGS_KEY = 'aimcr_preferences';

interface UserPreferences {
  notifications: {
    emailAlerts: boolean;
    anomalyDetection: boolean;
    reportReady: boolean;
    systemUpdates: boolean;
  };
  defaultArtifacts: {
    sms: boolean;
    calls: boolean;
    gps: boolean;
    browserHistory: boolean;
    contacts: boolean;
    applications: boolean;
    files: boolean;
    notifications: boolean;
    wifi: boolean;
    bluetooth: boolean;
  };
  parserPreferences: {
    autoParse: boolean;
    extractMetadata: boolean;
    runThreatIntel: boolean;
    generateHashes: boolean;
  };
  reportPreferences: {
    includeAnomalies: boolean;
    includeGraph: boolean;
    includeReconstruction: boolean;
    includeAuditLog: boolean;
    includeRecommendations: boolean;
    pageSize: string;
  };
}

const DEFAULT_PREFERENCES: UserPreferences = {
  notifications: {
    emailAlerts: true,
    anomalyDetection: true,
    reportReady: true,
    systemUpdates: false,
  },
  defaultArtifacts: {
    sms: true,
    calls: true,
    gps: true,
    browserHistory: true,
    contacts: true,
    applications: true,
    files: true,
    notifications: true,
    wifi: false,
    bluetooth: false,
  },
  parserPreferences: {
    autoParse: true,
    extractMetadata: true,
    runThreatIntel: true,
    generateHashes: true,
  },
  reportPreferences: {
    includeAnomalies: true,
    includeGraph: true,
    includeReconstruction: true,
    includeAuditLog: true,
    includeRecommendations: true,
    pageSize: 'A4',
  },
};

export function Settings() {
  const { theme, toggleTheme } = useTheme();
  const { showToast } = useToast();
  const userName = localStorage.getItem('aimcr_name') || 'Investigator';
  const userRole = localStorage.getItem('aimcr_role') || 'Investigator';
  const [prefs, setPrefs] = useState<UserPreferences>(() => {
    try {
      const saved = localStorage.getItem(SETTINGS_KEY);
      return saved ? { ...DEFAULT_PREFERENCES, ...JSON.parse(saved) } : DEFAULT_PREFERENCES;
    } catch {
      return DEFAULT_PREFERENCES;
    }
  });

  const savePreferences = (updated: UserPreferences) => {
    setPrefs(updated);
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(updated));
    showToast('Preferences saved successfully', 'success');
  };

  const updateNotification = (key: keyof UserPreferences['notifications']) => {
    const updated = {
      ...prefs,
      notifications: { ...prefs.notifications, [key]: !prefs.notifications[key] },
    };
    savePreferences(updated);
  };

  const updateArtifact = (key: keyof UserPreferences['defaultArtifacts']) => {
    const updated = {
      ...prefs,
      defaultArtifacts: { ...prefs.defaultArtifacts, [key]: !prefs.defaultArtifacts[key] },
    };
    savePreferences(updated);
  };

  const updateParser = (key: keyof UserPreferences['parserPreferences']) => {
    const updated = {
      ...prefs,
      parserPreferences: { ...prefs.parserPreferences, [key]: !prefs.parserPreferences[key] },
    };
    savePreferences(updated);
  };

  const updateReport = (key: keyof UserPreferences['reportPreferences']) => {
    const updated = {
      ...prefs,
      reportPreferences: { ...prefs.reportPreferences, [key]: !prefs.reportPreferences[key] },
    };
    savePreferences(updated);
  };

  const updateReportPageSize = (pageSize: string) => {
    const updated = {
      ...prefs,
      reportPreferences: { ...prefs.reportPreferences, pageSize },
    };
    savePreferences(updated);
  };

  const ToggleSwitch = ({ checked, onChange, label }: { checked: boolean; onChange: () => void; label?: string }) => (
    <div className="flex items-center justify-between py-2">
      {label && <span className="text-xs font-semibold text-text-primary">{label}</span>}
      <button
        onClick={onChange}
        className={`relative w-10 h-5 rounded-full transition-colors ${
          checked ? 'bg-brand-primary' : 'bg-slate-300 dark:bg-slate-700'
        }`}
      >
        <span
          className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow-sm transition-transform ${
            checked ? 'translate-x-5' : 'translate-x-0'
          }`}
        />
      </button>
    </div>
  );

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      
      {/* Title */}
      <div className="flex items-center space-x-2.5 border-b border-border-color pb-3">
        <SettingsIcon className="w-5 h-5 text-brand-primary" />
        <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider">
          Platform Settings
        </h2>
      </div>

      {/* User Info */}
      <div className="glass-panel p-5 space-y-3">
        <h3 className="text-xs font-bold text-text-muted uppercase tracking-wider">
          Forensic Profile Info
        </h3>
        <div className="p-4 bg-bg-secondary border border-border-color rounded-xl space-y-3 font-semibold text-xs">
          <div className="flex justify-between items-center">
            <span className="text-text-muted">FullName:</span>
            <span className="text-text-primary">{userName}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-text-muted">System Role:</span>
            <span className="px-2.5 py-0.5 bg-brand-primary/10 text-brand-primary rounded-full border border-brand-primary/20 font-bold uppercase tracking-wider text-[9px]">
              {userRole}
            </span>
          </div>
        </div>
      </div>

      {/* Notification Settings */}
      <div className="glass-panel p-5 space-y-3">
        <h3 className="text-xs font-bold text-text-muted uppercase tracking-wider flex items-center space-x-2">
          <Bell className="w-4 h-4 text-brand-primary" />
          <span>Notification Settings</span>
        </h3>
        <div className="p-4 bg-bg-secondary border border-border-color rounded-xl space-y-1">
          <ToggleSwitch checked={prefs.notifications.emailAlerts} onChange={() => updateNotification('emailAlerts')} label="Email alerts for case updates" />
          <ToggleSwitch checked={prefs.notifications.anomalyDetection} onChange={() => updateNotification('anomalyDetection')} label="Notify on anomaly detection" />
          <ToggleSwitch checked={prefs.notifications.reportReady} onChange={() => updateNotification('reportReady')} label="Report generation complete" />
          <ToggleSwitch checked={prefs.notifications.systemUpdates} onChange={() => updateNotification('systemUpdates')} label="System update notifications" />
        </div>
      </div>

      {/* Default Artifact Preferences */}
      <div className="glass-panel p-5 space-y-3">
        <h3 className="text-xs font-bold text-text-muted uppercase tracking-wider flex items-center space-x-2">
          <FileText className="w-4 h-4 text-brand-primary" />
          <span>Default Artifact Preferences</span>
        </h3>
        <div className="p-4 bg-bg-secondary border border-border-color rounded-xl space-y-1">
          <div className="grid grid-cols-2 gap-2">
            <ToggleSwitch checked={prefs.defaultArtifacts.sms} onChange={() => updateArtifact('sms')} label="SMS Logs" />
            <ToggleSwitch checked={prefs.defaultArtifacts.calls} onChange={() => updateArtifact('calls')} label="Call Logs" />
            <ToggleSwitch checked={prefs.defaultArtifacts.gps} onChange={() => updateArtifact('gps')} label="GPS Locations" />
            <ToggleSwitch checked={prefs.defaultArtifacts.browserHistory} onChange={() => updateArtifact('browserHistory')} label="Browser History" />
            <ToggleSwitch checked={prefs.defaultArtifacts.contacts} onChange={() => updateArtifact('contacts')} label="Contacts" />
            <ToggleSwitch checked={prefs.defaultArtifacts.applications} onChange={() => updateArtifact('applications')} label="Applications" />
            <ToggleSwitch checked={prefs.defaultArtifacts.files} onChange={() => updateArtifact('files')} label="Files" />
            <ToggleSwitch checked={prefs.defaultArtifacts.notifications} onChange={() => updateArtifact('notifications')} label="Notifications" />
            <ToggleSwitch checked={prefs.defaultArtifacts.wifi} onChange={() => updateArtifact('wifi')} label="WiFi Networks" />
            <ToggleSwitch checked={prefs.defaultArtifacts.bluetooth} onChange={() => updateArtifact('bluetooth')} label="Bluetooth Devices" />
          </div>
        </div>
      </div>

      {/* Parser Preferences */}
      <div className="glass-panel p-5 space-y-3">
        <h3 className="text-xs font-bold text-text-muted uppercase tracking-wider flex items-center space-x-2">
          <Cpu className="w-4 h-4 text-brand-primary" />
          <span>Parser Preferences</span>
        </h3>
        <div className="p-4 bg-bg-secondary border border-border-color rounded-xl space-y-1">
          <ToggleSwitch checked={prefs.parserPreferences.autoParse} onChange={() => updateParser('autoParse')} label="Auto-parse uploaded files" />
          <ToggleSwitch checked={prefs.parserPreferences.extractMetadata} onChange={() => updateParser('extractMetadata')} label="Extract metadata from media" />
          <ToggleSwitch checked={prefs.parserPreferences.runThreatIntel} onChange={() => updateParser('runThreatIntel')} label="Run Threat Intelligence checks" />
          <ToggleSwitch checked={prefs.parserPreferences.generateHashes} onChange={() => updateParser('generateHashes')} label="Generate SHA-256 hashes" />
        </div>
      </div>

      {/* Report Preferences */}
      <div className="glass-panel p-5 space-y-3">
        <h3 className="text-xs font-bold text-text-muted uppercase tracking-wider flex items-center space-x-2">
          <BookOpen className="w-4 h-4 text-brand-primary" />
          <span>Report Preferences</span>
        </h3>
        <div className="p-4 bg-bg-secondary border border-border-color rounded-xl space-y-1">
          <ToggleSwitch checked={prefs.reportPreferences.includeAnomalies} onChange={() => updateReport('includeAnomalies')} label="Include anomaly log" />
          <ToggleSwitch checked={prefs.reportPreferences.includeGraph} onChange={() => updateReport('includeGraph')} label="Include relationship graph" />
          <ToggleSwitch checked={prefs.reportPreferences.includeReconstruction} onChange={() => updateReport('includeReconstruction')} label="Include crime reconstruction" />
          <ToggleSwitch checked={prefs.reportPreferences.includeAuditLog} onChange={() => updateReport('includeAuditLog')} label="Include audit trail" />
          <ToggleSwitch checked={prefs.reportPreferences.includeRecommendations} onChange={() => updateReport('includeRecommendations')} label="Include recommendations" />
          <div className="flex items-center justify-between py-2">
            <span className="text-xs font-semibold text-text-primary">Report page size</span>
            <select
              className="glass-input text-xs py-1 px-2 text-text-primary bg-input-bg border-border-color"
              value={prefs.reportPreferences.pageSize}
              onChange={(e) => updateReportPageSize(e.target.value)}
            >
              <option value="A4">A4</option>
              <option value="Letter">Letter</option>
              <option value="Legal">Legal</option>
            </select>
          </div>
        </div>
      </div>

      {/* Interface Preferences */}
      <div className="glass-panel p-5 space-y-3">
        <h3 className="text-xs font-bold text-text-muted uppercase tracking-wider flex items-center space-x-2">
          <Monitor className="w-4 h-4 text-brand-primary" />
          <span>Interface Preferences</span>
        </h3>
        <div className="p-4 bg-bg-secondary border border-border-color rounded-xl">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-xs font-bold text-text-primary">Theme mode</h4>
              <p className="text-[10px] text-text-secondary font-semibold mt-0.5">
                Toggle between Light Mode and Dark Mode layouts.
              </p>
            </div>
            
            <button
              onClick={toggleTheme}
              className="flex items-center space-x-2 px-3 py-1.5 bg-card-secondary border border-border-color rounded-lg text-xs font-bold shadow-sm transition-colors hover:bg-card"
            >
              {theme === 'dark' ? (
                <>
                  <Sun className="w-3.5 h-3.5 text-amber-500" />
                  <span>Switch to Light</span>
                </>
              ) : (
                <>
                  <Moon className="w-3.5 h-3.5 text-indigo-500" />
                  <span>Switch to Dark</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Platform Info */}
      <div className="glass-panel p-5 space-y-3">
        <h3 className="text-xs font-bold text-text-muted uppercase tracking-wider">
          Platform Info
        </h3>
        <div className="p-4 bg-bg-secondary border border-border-color rounded-xl space-y-3 text-[10px] text-text-secondary leading-relaxed font-semibold">
          <div className="flex items-start space-x-2">
            <Info className="w-4 h-4 text-brand-primary shrink-0 mt-0.5" />
            <p>
              AIMCR is a Research & Enterprise digital forensics utility. Under active compliance audit trails, all investigator queries, uploads, and report generations are traceably signed using cryptographically secure parameters.
            </p>
          </div>
          <div className="flex items-start space-x-2">
            <Monitor className="w-4 h-4 text-brand-primary shrink-0 mt-0.5" />
            <p>
              Vector Index: FAISS CPU flat index. Models: SentenceTransformers all-MiniLM-L6-v2. Anomaly: Scikit-Learn Isolation Forest.
            </p>
          </div>
        </div>
      </div>

    </div>
  );
}
