import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link, Outlet } from 'react-router-dom';
import axios from 'axios';
import { useTheme } from '../context/ThemeContext';
import { useToast } from '../context/ToastContext';
import { ToastContainer } from './Toast';
import { CreateCaseModal } from './CreateCaseModal';
import { UploadEvidenceModal } from './UploadEvidenceModal';
import {
  LayoutDashboard, Calendar, GitFork, Cpu, ShieldAlert, Folder, Download, FilePenLine,
  LogOut, Sun, Moon, Plus, RefreshCw, Users, Key, Shield, Settings
} from 'lucide-react';

export function Layout() {
  const token = localStorage.getItem('aimcr_token');
  const userRole = localStorage.getItem('aimcr_role') || '';
  const userName = localStorage.getItem('aimcr_name') || '';
  const navigate = useNavigate();
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();
  const { showToast } = useToast();

  const [cases, setCases] = useState<any[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>('');
  const [selectedCase, setSelectedCase] = useState<any>(null);
  
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  
  // Modals state
  const [isCaseModalOpen, setIsCaseModalOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  // Redirect to login if no token
  useEffect(() => {
    if (!token) {
      navigate('/login');
    } else {
      fetchCases();
    }
  }, [token]);

  useEffect(() => {
    if (selectedCaseId) {
      const c = cases.find(item => item.id === selectedCaseId);
      setSelectedCase(c);
    }
  }, [selectedCaseId, cases]);

  const fetchCases = async (selectNewId?: string) => {
    try {
      const res = await axios.get('/api/cases');
      setCases(res.data);
      if (res.data.length > 0) {
        if (selectNewId) {
          setSelectedCaseId(selectNewId);
        } else if (!selectedCaseId) {
          setSelectedCaseId(res.data[0].id);
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleRunAnalysis = async () => {
    if (!selectedCaseId) return;
    setAnalyzing(true);
    try {
      await axios.post(`/api/analyze/run/${selectedCaseId}`);
      showToast('Intelligence engine executed. Computed anomalies, graph structures, and timelines.', 'success');
      // Trigger a state reload
      const tempId = selectedCaseId;
      setSelectedCaseId('');
      setTimeout(() => setSelectedCaseId(tempId), 50);
    } catch (e) {
      showToast('Failed to execute analysis engine.', 'error');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('aimcr_token');
    localStorage.removeItem('aimcr_role');
    localStorage.removeItem('aimcr_name');
    showToast('Signed out successfully.', 'info');
    navigate('/login');
  };

  const navItems = [
    { path: '/', label: 'Dashboard Overview', icon: <LayoutDashboard className="w-4 h-4" /> },
    { path: '/acquisition', label: 'Evidence Acquisition', icon: <Download className="w-4 h-4" /> },
    { path: '/timeline', label: 'Evidence Timeline', icon: <Calendar className="w-4 h-4" /> },
    { path: '/reconstruction', label: 'Crime Reconstruction', icon: <GitFork className="w-4 h-4" /> },
    { path: '/anomalies', label: 'Behavior & Anomalies', icon: <ShieldAlert className="w-4 h-4" /> },
    { path: '/graph', label: 'Relationship Graph', icon: <Users className="w-4 h-4" /> },
    { path: '/copilot', label: 'AI Investigation Copilot', icon: <Cpu className="w-4 h-4" /> },
    { path: '/reports', label: 'Report Generation', icon: <FilePenLine className="w-4 h-4" /> },
  ];

  const adminAuditorNavItems = [
    { path: '/audit', label: 'Case Audit Trail', icon: <Key className="w-4 h-4" />, roles: ['Admin', 'Auditor'] },
    { path: '/admin', label: 'User Management', icon: <Shield className="w-4 h-4" />, roles: ['Admin'] },
  ];

  return (
    <div className="min-h-screen flex bg-bg-base text-text-primary font-sans transition-colors duration-200">
      
      {/* Sidebar */}
      <aside className="w-64 border-r border-border-color bg-sidebar-bg flex flex-col justify-between shrink-0 z-30 shadow-[0_10px_30px_rgba(15,23,42,0.08)]">
        <div className="p-5 flex flex-col h-full overflow-y-auto">
          {/* Logo */}
          <div className="flex items-center space-x-3 mb-8 shrink-0">
            <div className="p-2 bg-brand-primary rounded-lg shadow-[0_0_0_1px_rgba(255,255,255,0.06),0_10px_20px_rgba(37,99,235,0.25)]">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-bold tracking-tight text-text-primary font-serif">AIMCR</span>
              <p className="text-[9px] text-text-muted uppercase tracking-wider font-bold">Forensic Intel</p>
            </div>
          </div>

          {/* Navigation links */}
          <nav className="space-y-1 flex-1">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`w-full flex items-center space-x-3 px-4 py-2.5 rounded-lg text-xs font-semibold tracking-wide transition-all duration-150 ${
                    isActive
                      ? 'bg-brand-primary text-white shadow-[0_10px_20px_rgba(37,99,235,0.18)]'
                      : 'text-text-secondary hover:bg-hover-row hover:text-text-primary'
                  }`}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </Link>
              );
            })}

            {/* Admin and Auditor items */}
            {adminAuditorNavItems.map((item) => {
              if (!item.roles.includes(userRole)) return null;
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`w-full flex items-center space-x-3 px-4 py-2.5 rounded-lg text-xs font-semibold tracking-wide transition-all duration-150 ${
                    isActive
                      ? 'bg-brand-primary text-white shadow-[0_10px_20px_rgba(37,99,235,0.18)]'
                      : 'text-text-secondary hover:bg-hover-row hover:text-text-primary'
                  }`}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Create case buttons inside sidebar */}
          <div className="pt-4 border-t border-border-color space-y-2 shrink-0">
            <button
              onClick={() => setIsCaseModalOpen(true)}
              className="w-full flex items-center justify-center space-x-2 py-2 px-3 bg-card-secondary hover:bg-card text-text-primary text-xs font-bold rounded-lg border border-border-color transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Create Case File</span>
            </button>
            
            <button
              onClick={() => setIsUploadModalOpen(true)}
              disabled={!selectedCaseId}
              className="w-full flex items-center justify-center space-x-2 py-2 px-3 bg-brand-primary/10 hover:bg-brand-primary/20 text-brand-primary text-xs font-bold rounded-lg border border-brand-primary/30 transition-colors disabled:opacity-50"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Upload Evidence</span>
            </button>
          </div>
        </div>

        {/* User Footer Profile */}
        <div className="p-4 border-t border-border-color flex items-center justify-between shrink-0">
          <Link to="/settings" className="flex items-center space-x-2.5 overflow-hidden hover:opacity-80 transition-opacity">
            <div className="w-8 h-8 rounded-full bg-brand-primary/10 flex items-center justify-center shrink-0">
              <span className="font-bold text-xs text-brand-primary">{userName ? userName[0].toUpperCase() : 'U'}</span>
            </div>
            <div className="overflow-hidden">
              <p className="text-xs font-semibold text-text-primary truncate">{userName}</p>
              <p className="text-[10px] text-text-muted uppercase tracking-wider font-bold truncate">{userRole}</p>
            </div>
          </Link>
          
          <div className="flex items-center space-x-1">
            <Link to="/settings" className="p-1 text-text-muted hover:text-text-secondary rounded-lg">
              <Settings className="w-4 h-4" />
            </Link>
            <button
              onClick={handleLogout}
              className="p-1 hover:bg-brand-danger/10 text-text-muted hover:text-brand-danger rounded-lg transition-colors duration-150"
              title="Log Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-16 border-b border-border-color bg-navbar-bg/95 flex items-center justify-between px-6 shrink-0 z-20 backdrop-blur">
          <div className="flex items-center space-x-3">
            <span className="text-xs font-bold text-text-muted uppercase tracking-wider">Active Case File:</span>
            <select
              className="glass-input bg-input-bg border-border-color text-xs font-semibold py-1 px-3 pr-8 focus:ring-1 text-text-primary"
              value={selectedCaseId}
              onChange={e => setSelectedCaseId(e.target.value)}
            >
              {cases.length === 0 ? (
                <option value="">No Active Cases</option>
              ) : (
                cases.map(c => (
                  <option key={c.id} value={c.id}>{c.title} ({c.priority || 'Medium'})</option>
                ))
              )}
            </select>
            {selectedCase && (
              <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                selectedCase.priority === 'Critical' ? 'bg-red-500/15 text-red-500 border border-red-500/30' :
                selectedCase.priority === 'High' ? 'bg-orange-500/15 text-orange-500 border border-orange-500/30' :
                selectedCase.priority === 'Low' ? 'bg-green-500/15 text-green-500 border border-green-500/30' :
                'bg-yellow-500/15 text-yellow-500 border border-yellow-500/30'
              }`}>
                {selectedCase.priority || 'Medium'}
              </span>
            )}
            
            <button
              onClick={handleRunAnalysis}
              disabled={analyzing || loading || !selectedCaseId}
              className="flex items-center space-x-2 px-3 py-1 bg-brand-primary/10 hover:bg-brand-primary/20 text-brand-primary text-xs font-semibold rounded-lg border border-brand-primary/30 transition-colors duration-150 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${analyzing ? 'animate-spin' : ''}`} />
              <span>{analyzing ? 'Analyzing Device Logs...' : 'Re-Run Intelligence Engine'}</span>
            </button>
          </div>

          <div className="flex items-center space-x-4">
            {/* Dark Mode Toggler */}
            <button
              onClick={toggleTheme}
              className="p-2 bg-card-secondary hover:bg-card border border-border-color text-text-secondary rounded-lg transition-colors duration-150"
              aria-label="Toggle theme"
            >
              {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>

          </div>
        </header>

        {/* Child Router Outlets */}
        <main className="flex-1 overflow-y-auto p-6 relative app-shell-main">
          <Outlet context={{ selectedCaseId, selectedCase, cases, fetchCases, loading, setLoading, analyzing }} />
        </main>
      </div>

      {/* Global Toast notifications */}
      <ToastContainer />

      {/* Reusable creation Modals */}
      <CreateCaseModal
        isOpen={isCaseModalOpen}
        onClose={() => setIsCaseModalOpen(false)}
        onCaseCreated={(newCase) => {
          fetchCases(newCase.id);
        }}
      />

      <UploadEvidenceModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        caseId={selectedCaseId}
        onEvidenceUploaded={() => {
          // Re-trigger loading case details by selecting it again
          const temp = selectedCaseId;
          setSelectedCaseId('');
          setTimeout(() => setSelectedCaseId(temp), 50);
        }}
      />
    </div>
  );
}
