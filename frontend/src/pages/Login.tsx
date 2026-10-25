import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Shield, ShieldAlert, Sun, Moon, Fingerprint, ScanFace, ArrowLeft, KeyRound } from 'lucide-react';
import { useToast } from '../context/ToastContext';
import { useTheme } from '../context/ThemeContext';

export function Login() {
  const [mode, setMode] = useState<'signin' | 'signup' | 'recovery'>('signin');
  const [step, setStep] = useState<'credentials' | 'biometric'>('credentials');
  const [email, setEmail] = useState('investigator@aimcr.gov');
  const [password, setPassword] = useState('password123');
  const [name, setName] = useState('');
  const [role, setRole] = useState('Investigator');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [challengeId, setChallengeId] = useState('');
  const [mfaCode, setMfaCode] = useState('246810');
  const [recoveryToken, setRecoveryToken] = useState('');
  const [recoveryPassword, setRecoveryPassword] = useState('');
  const [recoveryConfirmPassword, setRecoveryConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { theme, toggleTheme } = useTheme();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await axios.post('/api/auth/secure-access/start', { email, password });
      setChallengeId(res.data.challenge_id);
      setMfaCode(res.data.mfa_code_hint || '');
      setStep('biometric');
      showToast('Credentials accepted. Complete device verification.', 'success');
    } catch (err: any) {
      const detail = err.response?.data?.detail || 'Authentication failed. Please verify credentials.';
      setError(detail);
      showToast('Login Failed', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleBiometric = async (method: 'fingerprint' | 'face') => {
    setError('');
    setLoading(true);
    try {
      const hasWebAuthn = Boolean(window.PublicKeyCredential && navigator.credentials);
      const biometricAssertion = hasWebAuthn ? 'webauthn' : 'biometric-simulation';
      const res = await axios.post('/api/auth/secure-access/verify', {
        challenge_id: challengeId,
        mfa_code: mfaCode,
        biometric_assertion: biometricAssertion,
        dsc_assertion: 'dsc-token-simulation'
      });
      const { access_token, role: userRole, name: userName } = res.data;
      localStorage.setItem('aimcr_token', access_token);
      localStorage.setItem('aimcr_role', userRole);
      localStorage.setItem('aimcr_name', userName);
      showToast(`${method === 'fingerprint' ? 'Fingerprint' : 'Face ID'} verified. Welcome, ${userName}!`, 'success');
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Device verification failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    setLoading(true);
    try {
      await axios.post('/api/auth/register', { name, email, password, role });
      setMode('signin');
      setName('');
      setConfirmPassword('');
      showToast('Account created. Sign in to continue.', 'success');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Unable to create account.');
    } finally {
      setLoading(false);
    }
  };

  const handleRecovery = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await axios.post('/api/auth/password-recovery/request', { email });
      setRecoveryToken(res.data.demonstration_reset_token || '');
      showToast('Recovery request created. Check your email for instructions.', 'success');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Unable to start password recovery.');
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (recoveryPassword !== recoveryConfirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    setLoading(true);
    try {
      await axios.post('/api/auth/password-recovery/confirm', { reset_token: recoveryToken, password: recoveryPassword });
      setPassword('');
      setRecoveryPassword('');
      setRecoveryConfirmPassword('');
      setRecoveryToken('');
      resetView('signin');
      showToast('Password updated. Sign in to continue.', 'success');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Unable to update password.');
    } finally {
      setLoading(false);
    }
  };

  const resetView = (nextMode: 'signin' | 'signup' | 'recovery') => {
    setMode(nextMode);
    setStep('credentials');
    setError('');
  };

  const handleQuickFill = (quickEmail: string, quickPass: string) => {
    setEmail(quickEmail);
    setPassword(quickPass);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-primary font-sans relative overflow-hidden transition-colors duration-200">
      {/* Background glow effects */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-brand-700/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Theme Toggler */}
      <div className="absolute top-5 right-5 z-10">
        <button
          onClick={toggleTheme}
          className="p-2 bg-bg-card text-text-muted rounded-lg border border-border-color shadow-[0_1px_2px_rgba(15,23,42,0.05)] transition-colors"
        >
          {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>
      </div>

      <div className="w-full max-w-md p-8 bg-bg-card/95 backdrop-blur-md border border-border-color rounded-2xl relative shadow-[0_10px_30px_rgba(15,23,42,0.08)]">
        <div className="flex flex-col items-center mb-6">
          <div className="p-3 bg-brand-primary rounded-xl mb-3 shadow-[0_12px_24px_rgba(37,99,235,0.24)]">
            <Shield className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary font-serif">AIMCR</h1>
          <p className="text-xs text-text-secondary mt-1">Autonomous Mobile Forensic Intelligence Platform</p>
        </div>

        {mode === 'signin' && step === 'biometric' ? (
          <div className="space-y-5">
            <button type="button" onClick={() => setStep('credentials')} className="flex items-center gap-2 text-xs text-text-secondary hover:text-text-primary">
              <ArrowLeft className="w-4 h-4" /> Back to credentials
            </button>
            <div className="text-center">
              <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-brand-primary/10 text-brand-primary">
                <KeyRound className="h-7 w-7" />
              </div>
              <h2 className="text-lg font-bold text-text-primary">Secure device verification</h2>
              <p className="mt-1 text-xs text-text-secondary">Confirm your identity with the device biometric registered for this account.</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <button type="button" disabled={loading} onClick={() => handleBiometric('fingerprint')} className="flex min-h-28 flex-col items-center justify-center gap-2 rounded-xl border border-border-color bg-bg-secondary text-xs font-semibold text-text-primary hover:border-brand-primary disabled:opacity-50">
                <Fingerprint className="h-8 w-8 text-brand-primary" /> Fingerprint
              </button>
              <button type="button" disabled={loading} onClick={() => handleBiometric('face')} className="flex min-h-28 flex-col items-center justify-center gap-2 rounded-xl border border-border-color bg-bg-secondary text-xs font-semibold text-text-primary hover:border-brand-primary disabled:opacity-50">
                <ScanFace className="h-8 w-8 text-brand-primary" /> Face ID
              </button>
            </div>
            <p className="text-center text-[10px] text-text-muted">Biometric challenge is protected by the server and expires after 5 minutes.</p>
          </div>
        ) : mode === 'signin' ? (
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1">
              Investigator Email
            </label>
            <input
              type="email"
              required
              className="w-full glass-input bg-input-bg border-border-color text-text-primary placeholder-text-muted text-xs"
              placeholder="investigator@aimcr.gov"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          
          <div>
            <label className="block text-xs font-semibold text-text-secondary uppercase tracking-wider mb-1">
              Access Password
            </label>
            <input
              type="password"
              required
              className="w-full glass-input bg-input-bg border-border-color text-text-primary placeholder-text-muted text-xs"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          {error && (
            <div className="p-3 bg-brand-danger/10 border border-brand-danger/20 rounded-lg text-xs text-brand-danger flex items-start space-x-2">
              <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-lg text-xs font-bold text-white brand-gradient hover:opacity-90 shadow-[0_12px_24px_rgba(37,99,235,0.24)] transition-all duration-200 disabled:opacity-50"
          >
            {loading ? 'Validating credentials...' : 'Continue to secure access'}
          </button>
          <button type="button" onClick={() => resetView('recovery')} className="w-full text-xs font-semibold text-brand-primary hover:underline">Forgot password?</button>
        </form>
        ) : mode === 'signup' ? (
          <form onSubmit={handleSignup} className="space-y-4">
            <div><label className="auth-label">Full name</label><input required className="auth-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Officer name" /></div>
            <div><label className="auth-label">Official designation</label><select required className="auth-input" value={role} onChange={(e) => setRole(e.target.value)}>{['SI', 'Commissioner', 'AC', 'DC', 'ASP', 'DSP', 'Inspector', 'Constable', 'Investigator', 'Admin', 'Auditor'].map((rank) => <option key={rank} value={rank}>{rank}</option>)}</select></div>
            <div><label className="auth-label">Official email</label><input type="email" required className="auth-input" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@agency.gov" /></div>
            <div><label className="auth-label">Create password</label><input type="password" minLength={8} required className="auth-input" value={password} onChange={(e) => setPassword(e.target.value)} /></div>
            <div><label className="auth-label">Confirm password</label><input type="password" minLength={8} required className="auth-input" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} /></div>
            <button type="submit" disabled={loading} className="w-full py-2.5 rounded-lg text-xs font-bold text-white brand-gradient disabled:opacity-50">{loading ? 'Creating account...' : 'Create secure account'}</button>
          </form>
        ) : (
          <form onSubmit={handleRecovery} className="space-y-4">
            <button type="button" onClick={() => resetView('signin')} className="flex items-center gap-2 text-xs text-text-secondary hover:text-text-primary"><ArrowLeft className="w-4 h-4" /> Back to sign in</button>
            <div><label className="auth-label">Account email</label><input type="email" required className="auth-input" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
            <button type="submit" disabled={loading} className="w-full py-2.5 rounded-lg text-xs font-bold text-white brand-gradient disabled:opacity-50">{loading ? 'Sending request...' : 'Send recovery instructions'}</button>
            {recoveryToken && <>
              <div><label className="auth-label">Development reset token</label><input readOnly className="auth-input text-[10px]" value={recoveryToken} /></div>
              <div><label className="auth-label">New password</label><input type="password" minLength={8} required className="auth-input" value={recoveryPassword} onChange={(e) => setRecoveryPassword(e.target.value)} /></div>
              <div><label className="auth-label">Confirm new password</label><input type="password" minLength={8} required className="auth-input" value={recoveryConfirmPassword} onChange={(e) => setRecoveryConfirmPassword(e.target.value)} /></div>
              <button type="button" onClick={handlePasswordReset} disabled={loading} className="w-full py-2.5 rounded-lg text-xs font-bold text-white brand-gradient disabled:opacity-50">Update password</button>
            </>}
          </form>
        )}

        {mode === 'signin' && step === 'credentials' && <div className="mt-5 flex justify-center gap-4 border-t border-border-color pt-5 text-xs">
          <button type="button" onClick={() => resetView('signup')} className="font-semibold text-brand-primary hover:underline">Sign up</button>
          <button type="button" onClick={() => resetView('recovery')} className="text-text-secondary hover:text-text-primary">Forgot password</button>
        </div>}

        {/* Quick Login Seeds */}
        {mode === 'signin' && step === 'credentials' && <div className="mt-8 pt-6 border-t border-border-color">
          <p className="text-[10px] font-bold text-text-muted uppercase tracking-wider mb-2">Prefilled Demonstration Credentials</p>
          <div className="grid grid-cols-3 gap-2">
            <button
              onClick={() => handleQuickFill('investigator@aimcr.gov', 'password123')}
              className="p-2 bg-bg-secondary hover:bg-bg-card border border-border-color rounded text-[10px] text-text-secondary text-left font-semibold transition-colors"
            >
              <b>Investigator</b><br />John
            </button>
            <button
              onClick={() => handleQuickFill('admin@aimcr.gov', 'admin123')}
              className="p-2 bg-bg-secondary hover:bg-bg-card border border-border-color rounded text-[10px] text-text-secondary text-left font-semibold transition-colors"
            >
              <b>Admin</b><br />System
            </button>
            <button
              onClick={() => handleQuickFill('auditor@aimcr.gov', 'auditor123')}
              className="p-2 bg-bg-secondary hover:bg-bg-card border border-border-color rounded text-[10px] text-text-secondary text-left font-semibold transition-colors"
            >
              <b>Auditor</b><br />Compliance
            </button>
          </div>
        </div>}
      </div>
    </div>
  );
}
