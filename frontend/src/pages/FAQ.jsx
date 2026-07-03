import React, { useState, useEffect } from 'react';
import { HelpCircle, Send, BookOpen, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react';
import api from '../services/api';

const FAQ = () => {
  const [query, setQuery] = useState('');
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  
  // Categorized FAQ listing (for quick browsing)
  const [categories, setCategories] = useState({});
  const [openFaqId, setOpenFaqId] = useState(null);
  const [loadingList, setLoadingList] = useState(true);

  useEffect(() => {
    fetchFaqList();
  }, []);

  const fetchFaqList = async () => {
    try {
      setLoadingList(true);
      const res = await api.post('/mcp/searchFAQ', { query: '' });
      // Group by category
      const grouped = {};
      res.data.forEach(item => {
        if (!grouped[item.category]) {
          grouped[item.category] = [];
        }
        grouped[item.category].push(item);
      });
      setCategories(grouped);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingList(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    try {
      setLoading(true);
      setResponse(null);
      const res = await api.post('/agents/faq', { query });
      setResponse(res.data);
    } catch (err) {
      console.error(err);
      setResponse({
        answer: 'I encountered an issue searching the directory. Please make sure the backend is active.'
      });
    } finally {
      setLoading(false);
    }
  };

  const toggleAccordion = (id) => {
    setOpenFaqId(prev => prev === id ? null : id);
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Title */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-800 dark:text-white">Campus FAQ Concierge</h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
          Chat with the offline concierge search agent or browse categories for instant guides.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Chat / Search box panel */}
        <div className="glass-panel p-6 lg:col-span-2 flex flex-col justify-between h-[420px]">
          <div>
            <h3 className="font-bold text-sm text-slate-800 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-3 mb-4 flex items-center gap-2">
              <HelpCircle className="text-brand-500" size={18} />
              Inquire Academic Information
            </h3>

            {/* Answer Display */}
            <div className="bg-slate-50 dark:bg-slate-800/30 p-4 rounded-2xl h-60 overflow-y-auto pr-1 text-xs border border-slate-100 dark:border-slate-800/40">
              {loading ? (
                <div className="flex flex-col items-center justify-center h-full gap-2 text-slate-400">
                  <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
                  Searching local index...
                </div>
              ) : response ? (
                <div className="space-y-3">
                  {response.matched_question && (
                    <p className="text-[10px] font-bold text-brand-500 dark:text-brand-400 uppercase tracking-wide">
                      Top Match: "{response.matched_question}"
                    </p>
                  )}
                  <p className="text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-line">
                    {response.answer}
                  </p>
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-slate-400 text-center">
                  Ask me anything about advisors, attendance policy, library, transcripts, exam MC, etc.
                </div>
              )}
            </div>
          </div>

          {/* Search Input bar */}
          <form onSubmit={handleSearch} className="flex gap-2 mt-4">
            <input 
              type="text" 
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Type your question..."
              className="flex-1 p-3 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-xl focus:outline-none focus:border-brand-500 dark:text-white text-xs"
              required
            />
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="p-3 bg-brand-500 hover:bg-brand-600 active:bg-brand-700 disabled:bg-brand-500/50 text-white rounded-xl shadow transition shrink-0"
            >
              <Send size={16} />
            </button>
          </form>
        </div>

        {/* Categories checklist accordion directory */}
        <div className="glass-panel p-6 flex flex-col h-[420px] overflow-hidden">
          <h3 className="font-bold text-sm text-slate-800 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-3 mb-4 flex items-center gap-2">
            <BookOpen className="text-indigo-500" size={18} />
            Browse FAQ Topics
          </h3>

          <div className="flex-1 overflow-y-auto space-y-4 pr-1">
            {loadingList ? (
              <div className="text-center py-10 text-xs text-slate-400">Loading Directory...</div>
            ) : Object.keys(categories).length === 0 ? (
              <div className="text-center py-10 text-xs text-slate-400">No FAQ categories found.</div>
            ) : (
              Object.keys(categories).map((cat) => (
                <div key={cat} className="space-y-2">
                  <h4 className="font-bold text-[10px] text-slate-400 dark:text-slate-500 uppercase tracking-widest block mb-1">
                    {cat}
                  </h4>
                  <div className="space-y-1.5">
                    {categories[cat].map((faq) => (
                      <div 
                        key={faq.id} 
                        className="border border-slate-100 dark:border-slate-800/60 rounded-xl overflow-hidden text-xs"
                      >
                        <button
                          onClick={() => toggleAccordion(faq.id)}
                          className="w-full p-3 text-left font-bold text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-850 flex items-center justify-between transition-colors gap-2"
                        >
                          <span>{faq.question}</span>
                          {openFaqId === faq.id ? <ChevronUp size={14} className="shrink-0 text-slate-400" /> : <ChevronDown size={14} className="shrink-0 text-slate-400" />}
                        </button>
                        {openFaqId === faq.id && (
                          <div className="p-3 bg-slate-50/50 dark:bg-slate-850/30 border-t border-slate-100 dark:border-slate-800/60 text-slate-500 dark:text-slate-400 leading-relaxed">
                            {faq.answer}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

      </div>
    </div>
  );
};

export default FAQ;
