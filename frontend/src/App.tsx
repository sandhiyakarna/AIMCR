import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import axios from 'axios';
import { ToastProvider } from './context/ToastContext';
import { Layout } from './components/Layout';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Timeline } from './pages/Timeline';
import { Reconstruction } from './pages/Reconstruction';
import { Anomalies } from './pages/Anomalies';
import { Graph } from './pages/Graph';
import { Copilot } from './pages/Copilot';
import { AuditTrail } from './pages/AuditTrail';
import { Admin } from './pages/Admin';
import { Settings } from './pages/Settings';
import { Acquisition } from './pages/Acquisition';
import { ReportGeneration } from './pages/ReportGeneration';
import { NotFound } from './pages/NotFound';

import { API_BASE_URL } from './config';

axios.defaults.baseURL = API_BASE_URL;

// Configure global Axios request interceptor to attach JWT token
axios.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('aimcr_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Global response interceptor for automatic 401 authentication expiration handling
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('aimcr_token');
      localStorage.removeItem('aimcr_role');
      localStorage.removeItem('aimcr_name');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Login Route */}
          <Route path="/login" element={<Login />} />
          
          {/* Private Shell Layout routes */}
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="timeline" element={<Timeline />} />
            <Route path="reconstruction" element={<Reconstruction />} />
            <Route path="anomalies" element={<Anomalies />} />
            <Route path="graph" element={<Graph />} />
            <Route path="copilot" element={<Copilot />} />
            <Route path="acquisition" element={<Acquisition />} />
            <Route path="reports" element={<ReportGeneration />} />
            <Route path="audit" element={<AuditTrail />} />
            <Route path="admin" element={<Admin />} />
            <Route path="settings" element={<Settings />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  );
}
