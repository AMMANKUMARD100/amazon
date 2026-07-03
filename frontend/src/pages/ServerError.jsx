import React from 'react';
import { AlertCircle, RotateCcw } from 'lucide-react';

const ServerError = () => {
  const handleReload = () => {
    window.location.href = '/';
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[75vh] text-center p-6 select-none">
      <div className="p-4 bg-red-500/10 text-red-500 rounded-full mb-4">
        <AlertCircle size={48} />
      </div>
      <h1 className="text-3xl font-extrabold text-slate-800 dark:text-white">500 - Server Error</h1>
      <p className="text-slate-500 dark:text-slate-400 text-sm mt-2 max-w-sm">
        The backend concierge server encountered an issue or is currently offline. Please ensure Flask app is running.
      </p>
      <button 
        onClick={handleReload} 
        className="mt-6 flex items-center gap-2 px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-xl text-xs font-bold shadow transition"
      >
        <RotateCcw size={16} />
        Reload Application
      </button>
    </div>
  );
};

export default ServerError;
