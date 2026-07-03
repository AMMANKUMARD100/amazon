import React, { useState, useEffect, useRef } from 'react';
import { Menu, Bell, Sun, Moon, User, CheckCircle2, AlertTriangle, Info } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import api from '../services/api';

const Navbar = ({ toggleSidebar }) => {
  const { user, logout } = useAuth();
  const { isDarkMode, toggleTheme } = useTheme();
  const [notifications, setNotifications] = useState([]);
  const [showNotifDropdown, setShowNotifDropdown] = useState(false);
  const [showProfileDropdown, setShowProfileDropdown] = useState(false);
  
  const notifRef = useRef(null);
  const profileRef = useRef(null);

  // Fetch notifications on load and every 30 seconds
  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, []);

  // Close dropdowns on outside click
  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (notifRef.current && !notifRef.current.contains(e.target)) {
        setShowNotifDropdown(false);
      }
      if (profileRef.current && !profileRef.current.contains(e.target)) {
        setShowProfileDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  const fetchNotifications = async () => {
    try {
      const res = await api.get('/agents/notifications');
      setNotifications(res.data);
    } catch (err) {
      console.error('Failed to load notifications:', err);
    }
  };

  const markAllAsRead = async () => {
    try {
      await api.post('/agents/notifications');
      // Set all local notifications to read
      setNotifications(prev => prev.map(n => ({ ...n, is_read: 1 })));
    } catch (err) {
      console.error('Failed to mark notifications read:', err);
    }
  };

  const unreadCount = notifications.filter(n => n.is_read === 0).length;

  const getNotifIcon = (type) => {
    switch (type) {
      case 'Alert':
        return <AlertTriangle className="text-red-500 shrink-0" size={16} />;
      case 'Reminder':
        return <CheckCircle2 className="text-amber-500 shrink-0" size={16} />;
      default:
        return <Info className="text-blue-500 shrink-0" size={16} />;
    }
  };

  return (
    <header className="flex items-center justify-between px-6 h-16 bg-white dark:bg-slate-900 border-b border-slate-200/60 dark:border-slate-800/60 sticky top-0 z-10">
      
      {/* Mobile Sidebar toggler and Title */}
      <div className="flex items-center gap-3">
        <button
          onClick={toggleSidebar}
          className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 lg:hidden"
        >
          <Menu size={22} />
        </button>
        <span className="font-semibold text-slate-800 dark:text-white hidden sm:inline">
          Concierge Console
        </span>
      </div>

      {/* Action buttons controls */}
      <div className="flex items-center gap-4">
        
        {/* Theme Toggler */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-xl text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          title="Toggle Dark Mode"
        >
          {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
        </button>

        {/* Live Notifications bell dropdown */}
        <div className="relative" ref={notifRef}>
          <button
            onClick={() => setShowNotifDropdown(!showNotifDropdown)}
            className="p-2 rounded-xl text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors relative"
          >
            <Bell size={20} />
            {unreadCount > 0 && (
              <span className="absolute top-1.5 right-1.5 w-4 h-4 bg-red-500 rounded-full text-[9px] font-bold text-white flex items-center justify-center animate-pulse">
                {unreadCount}
              </span>
            )}
          </button>

          {showNotifDropdown && (
            <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-slate-900 border border-slate-200/60 dark:border-slate-800/60 rounded-2xl shadow-xl z-30 py-2 animate-slide-up">
              <div className="flex items-center justify-between px-4 pb-2 border-b border-slate-100 dark:border-slate-800">
                <span className="font-semibold text-sm text-slate-800 dark:text-white">Notifications</span>
                {unreadCount > 0 && (
                  <button 
                    onClick={markAllAsRead}
                    className="text-xs text-brand-500 hover:underline font-medium"
                  >
                    Mark all read
                  </button>
                )}
              </div>

              <div className="max-h-64 overflow-y-auto py-1">
                {notifications.length === 0 ? (
                  <div className="px-4 py-6 text-center text-xs text-slate-400">
                    No active alerts. Everything looks clear!
                  </div>
                ) : (
                  notifications.map((n) => (
                    <div 
                      key={n.id} 
                      className={`px-4 py-2.5 flex gap-3 text-xs transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/40
                        ${n.is_read === 0 ? 'bg-brand-50/40 dark:bg-brand-950/10' : ''}`}
                    >
                      {getNotifIcon(n.type)}
                      <div>
                        <h4 className="font-semibold text-slate-800 dark:text-slate-200">{n.title}</h4>
                        <p className="text-slate-500 dark:text-slate-400 mt-0.5">{n.message}</p>
                        <span className="text-[10px] text-slate-400 block mt-1">
                          {new Date(n.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* User profile details dropdown */}
        <div className="relative" ref={profileRef}>
          <button
            onClick={() => setShowProfileDropdown(!showProfileDropdown)}
            className="flex items-center gap-2.5 pl-2 pr-3 py-1.5 rounded-xl border border-slate-200/60 dark:border-slate-800/60 hover:bg-slate-100/40 dark:hover:bg-slate-800/40 transition-colors"
          >
            <div className="w-8 h-8 rounded-lg bg-brand-500 text-white flex items-center justify-center font-bold text-sm">
              {user?.full_name ? user.full_name.charAt(0).toUpperCase() : <User size={18} />}
            </div>
            <div className="text-left hidden md:block">
              <p className="text-xs font-semibold leading-none text-slate-800 dark:text-slate-200">
                {user?.full_name || 'Alex Mercer'}
              </p>
              <p className="text-[10px] text-slate-400 leading-none mt-0.5">
                {user?.role || 'Student'}
              </p>
            </div>
          </button>

          {showProfileDropdown && (
            <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-slate-900 border border-slate-200/60 dark:border-slate-800/60 rounded-2xl shadow-xl z-30 py-1.5 animate-slide-up">
              <div className="px-4 py-2 border-b border-slate-100 dark:border-slate-800">
                <p className="text-xs text-slate-400">Signed in as</p>
                <p className="text-sm font-semibold text-slate-800 dark:text-white truncate">{user?.email}</p>
                <p className="text-[10px] text-slate-400 truncate mt-0.5">{user?.matric_number}</p>
              </div>
              <button
                onClick={logout}
                className="w-full text-left px-4 py-2.5 text-xs text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/20 font-medium transition-colors"
              >
                Sign Out
              </button>
            </div>
          )}
        </div>

      </div>
    </header>
  );
};

export default Navbar;
