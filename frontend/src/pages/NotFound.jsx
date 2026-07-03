import React from 'react';
import { Link } from 'react-router-dom';
import { HelpCircle, ArrowLeft } from 'lucide-react';

const NotFound = () => {
  return (
    <div className="flex flex-col items-center justify-center min-h-[75vh] text-center p-6 select-none">
      <div className="p-4 bg-brand-500/10 text-brand-500 rounded-full mb-4">
        <HelpCircle size={48} />
      </div>
      <h1 className="text-3xl font-extrabold text-slate-800 dark:text-white">404 - Page Not Found</h1>
      <p className="text-slate-500 dark:text-slate-400 text-sm mt-2 max-w-sm">
        The concierge agent could not find the file or directory path you were looking for.
      </p>
      <Link 
        to="/" 
        className="mt-6 flex items-center gap-2 text-xs font-bold text-brand-500 hover:text-brand-600 dark:text-brand-400"
      >
        <ArrowLeft size={16} />
        Back to Dashboard
      </Link>
    </div>
  );
};

export default NotFound;
