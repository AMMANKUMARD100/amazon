import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { GraduationCap, Lock, User, AlertCircle, Loader2 } from 'lucide-react';

const Login = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const sessionExpired = searchParams.get('expired') === 'true';

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setErrorMsg('Please enter both username and password.');
      return;
    }

    try {
      setErrorMsg('');
      setSubmitting(true);
      await login(username, password);
      navigate('/');
    } catch (err) {
      setErrorMsg(err.message || 'Invalid username or password.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-tr from-brand-900 via-slate-900 to-slate-900 p-4 select-none">
      
      {/* Background radial soft light */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_var(--tw-gradient-stops))] from-brand-500/10 via-transparent to-transparent pointer-events-none" />

      <div className="w-full max-w-md glass-panel bg-white/10 border-white/5 shadow-2xl p-8 text-white relative z-10 animate-fade-in">
        
        {/* Header Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="p-3 bg-brand-500 rounded-2xl text-white shadow-lg shadow-brand-500/30 mb-3">
            <GraduationCap size={32} />
          </div>
          <h2 className="text-2xl font-bold tracking-tight">CampusMate AI</h2>
          <p className="text-xs text-slate-400 mt-1">Intelligent Student Concierge Agent</p>
        </div>

        {sessionExpired && (
          <div className="mb-5 p-3 rounded-xl bg-amber-500/15 border border-amber-500/30 text-xs text-amber-300 flex items-center gap-2">
            <AlertCircle size={16} />
            Your session has expired. Please log in again.
          </div>
        )}

        {errorMsg && (
          <div className="mb-5 p-3 rounded-xl bg-red-500/15 border border-red-500/30 text-xs text-red-300 flex items-center gap-2">
            <AlertCircle size={16} />
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Username Input */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">
              Username
            </label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-slate-500">
                <User size={18} />
              </span>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username (student/admin)"
                className="w-full pl-10 pr-4 py-3 bg-slate-800/40 border border-slate-700/50 rounded-xl text-sm placeholder-slate-500 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 text-white transition-all"
                required
                disabled={submitting}
              />
            </div>
          </div>

          {/* Password Input */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">
              Password
            </label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-slate-500">
                <Lock size={18} />
              </span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                className="w-full pl-10 pr-4 py-3 bg-slate-800/40 border border-slate-700/50 rounded-xl text-sm placeholder-slate-500 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 text-white transition-all"
                required
                disabled={submitting}
              />
            </div>
          </div>

          {/* Login Button */}
          <button
            type="submit"
            disabled={submitting}
            className="w-full py-3 bg-brand-500 hover:bg-brand-600 active:bg-brand-700 disabled:bg-brand-500/50 rounded-xl text-sm font-semibold tracking-wide shadow-lg shadow-brand-500/25 flex items-center justify-center gap-2 transition-all"
          >
            {submitting ? (
              <>
                <Loader2 className="animate-spin" size={18} />
                Logging in...
              </>
            ) : (
              'Sign In'
            )}
          </button>
        </form>

        {/* Mock accounts credentials details helper */}
        <div className="mt-8 pt-6 border-t border-slate-800/60 text-center">
          <span className="text-[10px] uppercase font-bold text-slate-500 tracking-widest block mb-2">
            Local Offline Credentials
          </span>
          <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-400">
            <div className="bg-slate-800/20 p-2 rounded-lg border border-slate-800/40">
              <p className="font-bold text-slate-300">Student</p>
              <p className="mt-0.5">student / password123</p>
            </div>
            <div className="bg-slate-800/20 p-2 rounded-lg border border-slate-800/40">
              <p className="font-bold text-slate-300">Admin</p>
              <p className="mt-0.5">admin / adminpassword123</p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};

export default Login;
