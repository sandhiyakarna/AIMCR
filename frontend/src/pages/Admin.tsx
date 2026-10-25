import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useToast } from '../context/ToastContext';
import { SkeletonLoader } from '../components/SkeletonLoader';
import { Users, Plus, Edit2, Trash2, Key, Check, Folder, Shield } from 'lucide-react';

export function Admin() {
  const [users, setUsers] = useState<any[]>([]);
  const [stats, setStats] = useState<any>({ total_users: 0, total_cases: 0, total_audit_logs: 0 });
  const [loading, setLoading] = useState(false);
  const { showToast } = useToast();

  // Create user form state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [role, setRole] = useState('Investigator');
  const [creating, setCreating] = useState(false);

  // Edit user state
  const [editingUserId, setEditingUserId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');
  const [editingRole, setEditingRole] = useState('');
  const [editingPassword, setEditingPassword] = useState('');
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    fetchUsers();
    fetchStats();
  }, []);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await axios.get('/api/users');
      setUsers(res.data);
    } catch (e) {
      console.error(e);
      showToast('Failed to load user list. Admin access required.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await axios.get('/api/users/stats');
      setStats(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password || !name) return;

    setCreating(true);
    try {
      const res = await axios.post('/api/users', {
        email,
        password,
        name,
        role
      });
      showToast(`User ${name} created successfully!`, 'success');
      setUsers((prev) => [...prev, res.data]);
      setEmail('');
      setPassword('');
      setName('');
      setRole('Investigator');
      fetchStats();
    } catch (err: any) {
      const errMsg = err.response?.data?.detail || 'Failed to create user';
      showToast(errMsg, 'error');
    } finally {
      setCreating(false);
    }
  };

  const handleStartEdit = (user: any) => {
    setEditingUserId(user.id);
    setEditingName(user.name);
    setEditingRole(user.role);
    setEditingPassword('');
  };

  const handleUpdateUser = async (user_id: string) => {
    setUpdating(true);
    try {
      const res = await axios.put(`/api/users/${user_id}`, {
        name: editingName,
        role: editingRole,
        password: editingPassword || undefined
      });
      showToast('User updated successfully', 'success');
      setUsers((prev) => prev.map(u => u.id === user_id ? res.data : u));
      setEditingUserId(null);
    } catch (err: any) {
      const errMsg = err.response?.data?.detail || 'Failed to update user';
      showToast(errMsg, 'error');
    } finally {
      setUpdating(false);
    }
  };

  const handleDeleteUser = async (user_id: string, user_name: string) => {
    if (!window.confirm(`Are you sure you want to delete user ${user_name}?`)) return;

    try {
      await axios.delete(`/api/users/${user_id}`);
      showToast('User deleted successfully', 'success');
      setUsers((prev) => prev.filter(u => u.id !== user_id));
      fetchStats();
    } catch (err: any) {
      const errMsg = err.response?.data?.detail || 'Failed to delete user';
      showToast(errMsg, 'error');
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Platform Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="glass-panel p-5 flex items-center justify-between">
          <div>
            <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">
              Total Personnel Users
            </span>
            <h3 className="text-2xl font-bold dark:text-white font-serif mt-1">{stats.total_users}</h3>
          </div>
          <Users className="w-8 h-8 text-brand-500 opacity-60" />
        </div>

        <div className="glass-panel p-5 flex items-center justify-between">
          <div>
            <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">
              Active Investigation Cases
            </span>
            <h3 className="text-2xl font-bold dark:text-white font-serif mt-1">{stats.total_cases}</h3>
          </div>
          <Folder className="w-8 h-8 text-indigo-500 opacity-60" />
        </div>

        <div className="glass-panel p-5 flex items-center justify-between">
          <div>
            <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">
              System Audit Operations
            </span>
            <h3 className="text-2xl font-bold dark:text-white font-serif mt-1">{stats.total_audit_logs}</h3>
          </div>
          <Key className="w-8 h-8 text-emerald-500 opacity-60" />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        
        {/* Create User Form */}
        <div className="glass-panel p-5 rounded-2xl space-y-4">
          <h2 className="text-sm font-bold text-slate-800 dark:text-slate-100 uppercase tracking-wider border-b border-slate-100 dark:border-slate-800 pb-2 flex items-center gap-1.5">
            <Plus className="w-4 h-4 text-brand-500" />
            <span>Add Investigator User</span>
          </h2>
          <form onSubmit={handleCreateUser} className="space-y-3">
            <div>
              <label className="block text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
                Full Name
              </label>
              <input
                type="text"
                required
                className="w-full glass-input bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-slate-100 placeholder-slate-400 text-xs"
                placeholder="e.g. Inspector Lestrade"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            
            <div>
              <label className="block text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
                Email Address
              </label>
              <input
                type="email"
                required
                className="w-full glass-input bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-slate-100 placeholder-slate-400 text-xs"
                placeholder="lestrade@aimcr.gov"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
                Initial Password
              </label>
              <input
                type="password"
                required
                className="w-full glass-input bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-slate-100 placeholder-slate-400 text-xs"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
                Access Authorization Role
              </label>
              <select
                className="w-full glass-input bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-slate-100 text-xs font-semibold"
                value={role}
                onChange={(e) => setRole(e.target.value)}
              >
                <option value="Investigator">Investigator</option>
                <option value="Admin">Administrator</option>
                <option value="Auditor">Compliance Auditor</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={creating || !email || !password || !name}
              className="w-full py-2 bg-brand-primary hover:bg-brand-primary-hover text-white text-xs font-bold rounded-lg shadow-[0_12px_24px_rgba(37,99,235,0.24)] transition-colors disabled:opacity-50 mt-2"
            >
              {creating ? 'Creating user account...' : 'Create Access Account'}
            </button>
          </form>
        </div>

        {/* User Account Registry list */}
        <div className="lg:col-span-2 glass-panel p-5 rounded-2xl space-y-4">
          <h2 className="text-sm font-bold text-slate-800 dark:text-slate-100 uppercase tracking-wider border-b border-slate-100 dark:border-slate-800 pb-2 flex items-center gap-1.5">
            <Shield className="w-4 h-4 text-brand-500" />
            <span>Personnel Access Accounts</span>
          </h2>

          {loading ? (
            <SkeletonLoader type="list" count={3} />
          ) : users.length === 0 ? (
            <div className="text-center py-6 text-xs text-slate-400 font-semibold">
              No investigator users registered.
            </div>
          ) : (
            <div className="space-y-3 max-h-[460px] overflow-y-auto pr-1">
              {users.map((user) => {
                const isEditing = editingUserId === user.id;

                return (
                  <div
                    key={user.id}
                    className="p-3.5 border border-border-color rounded-xl bg-card-secondary/60 flex items-center justify-between"
                  >
                    {isEditing ? (
                      <div className="flex-1 grid grid-cols-1 md:grid-cols-4 gap-2 mr-4">
                        <input
                          type="text"
                          className="glass-input py-1 px-2 text-xs bg-input-bg text-text-primary"
                          value={editingName}
                          onChange={(e) => setEditingName(e.target.value)}
                          placeholder="Name"
                        />
                        <select
                          className="glass-input py-1 px-2 text-xs bg-input-bg text-text-primary font-semibold"
                          value={editingRole}
                          onChange={(e) => setEditingRole(e.target.value)}
                        >
                          <option value="Investigator">Investigator</option>
                          <option value="Admin">Admin</option>
                          <option value="Auditor">Auditor</option>
                        </select>
                        <input
                          type="password"
                          className="glass-input py-1 px-2 text-xs bg-input-bg text-text-primary"
                          value={editingPassword}
                          onChange={(e) => setEditingPassword(e.target.value)}
                          placeholder="Reset Password (optional)"
                        />
                        <div className="flex gap-1 items-center">
                          <button
                            onClick={() => handleUpdateUser(user.id)}
                            disabled={updating || !editingName}
                            className="p-1.5 bg-emerald-500 hover:bg-emerald-600 text-white rounded transition-colors"
                          >
                            <Check className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => setEditingUserId(null)}
                            className="text-xs px-2 py-1 text-slate-400 hover:text-slate-600"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="flex items-center space-x-3">
                          <div className="w-8 h-8 rounded-full bg-brand-100 dark:bg-brand-900/50 flex items-center justify-center font-bold text-brand-600 text-xs shrink-0">
                            {user.name[0].toUpperCase()}
                          </div>
                          <div>
                            <div className="flex items-center space-x-2">
                              <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200">{user.name}</h4>
                              <span className="text-[9px] font-bold px-2 py-0.5 bg-slate-100 dark:bg-slate-900 text-slate-500 rounded-full border border-slate-200/50 dark:border-slate-800/50">
                                {user.role}
                              </span>
                            </div>
                            <p className="text-[10px] text-slate-400 font-semibold mt-0.5">{user.email}</p>
                          </div>
                        </div>

                        <div className="flex items-center space-x-1 shrink-0">
                          <button
                            onClick={() => handleStartEdit(user)}
                            className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded transition-colors"
                            title="Edit User Details"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDeleteUser(user.id, user.name)}
                            className="p-1.5 hover:bg-red-50 dark:hover:bg-red-950/20 text-slate-400 hover:text-red-500 rounded transition-colors"
                            title="Delete Account"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
