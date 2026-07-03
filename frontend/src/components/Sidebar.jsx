import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  CalendarCheck, 
  BookOpen, 
  CalendarDays, 
  HelpCircle, 
  UserCircle,
  GraduationCap,
  LogOut
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const Sidebar = ({ isOpen, toggleSidebar }) => {
  const { logout } = useAuth();
  
  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Attendance', path: '/attendance', icon: CalendarCheck },
    { name: 'Assignments', path: '/assignments', icon: BookOpen },
    { name: 'Study Planner', path: '/study-planner', icon: CalendarDays },
    { name: 'Campus FAQ', path: '/faq', icon: HelpCircle },
    { name: 'Profile', path: '/profile', icon: UserCircle },
  ];

  return (
    <aside className={`
      fixed inset-y-0 left-0 z-20 flex flex-col w-64 border-r border-slate-200/60 dark:border-slate-800/60
      bg-white dark:bg-slate-900 transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:h-screen
      ${isOpen ? 'translate-x-0' : '-translate-x-full'}
    `}>
      {/* Brand logo header */}
      <div className="flex items-center gap-3 px-6 h-16 border-b border-slate-200/60 dark:border-slate-800/60">
        <div className="p-1.5 bg-brand-500 rounded-xl text-white">
          <GraduationCap size={24} />
        </div>
        <div>
          <h1 className="font-bold text-lg leading-tight tracking-tight text-slate-800 dark:text-white">
            CampusMate AI
          </h1>
          <span className="text-[10px] font-medium text-slate-400 uppercase tracking-widest">
            Concierge Portal
          </span>
        </div>
      </div>

      {/* Nav List links */}
      <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            onClick={() => {
              if (window.innerWidth < 1024) toggleSidebar(); // Close sidebar on mobile select
            }}
            className={({ isActive }) => `
              flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200
              ${isActive 
                ? 'bg-brand-500 text-white shadow-md shadow-brand-500/20' 
                : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800/60'}
            `}
          >
            <item.icon size={20} />
            {item.name}
          </NavLink>
        ))}
      </nav>

      {/* Logout Footer option */}
      <div className="p-4 border-t border-slate-200/60 dark:border-slate-800/60">
        <button
          onClick={logout}
          className="flex items-center gap-3.5 w-full px-4 py-3 rounded-xl text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/20 transition-all duration-200"
        >
          <LogOut size={20} />
          Sign Out
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
