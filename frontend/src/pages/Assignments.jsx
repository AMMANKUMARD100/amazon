import React, { useState, useEffect } from 'react';
import { 
  BookOpen, 
  Plus, 
  Trash2, 
  CheckCircle2, 
  Clock, 
  AlertCircle,
  Calendar,
  X
} from 'lucide-react';
import api from '../services/api';

const Assignments = () => {
  const [assignments, setAssignments] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Tab filters: 'All', 'Pending', 'Completed'
  const [activeTab, setActiveTab] = useState('Pending');
  
  // Add assignment modal/form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newSubjectId, setNewSubjectId] = useState('');
  const [newDueDate, setNewDueDate] = useState('');
  const [newPriority, setNewPriority] = useState('Medium');
  const [formErrors, setFormErrors] = useState([]);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch assignments and registered subjects via MCP
      const assignRes = await api.post('/mcp/getAssignments');
      const subRes = await api.post('/mcp/getAttendance'); // Returns subject listing
      
      setAssignments(assignRes.data);
      
      // Extract unique subjects
      const uniqueSubs = [];
      const seen = new Set();
      subRes.data.forEach(item => {
        if (!seen.has(item.subject_id)) {
          seen.add(item.subject_id);
          uniqueSubs.push({ id: item.subject_id, code: item.code, name: item.name });
        }
      });
      setSubjects(uniqueSubs);
      if (uniqueSubs.length > 0) setNewSubjectId(uniqueSubs[0].id);
      
    } catch (err) {
      console.error(err);
      setError('Could not retrieve assignment lists.');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleStatus = async (id, currentStatus) => {
    const nextStatus = currentStatus === 'Pending' ? 'Completed' : 'Pending';
    try {
      await api.post('/mcp/updateAssignment', {
        assignment_id: id,
        status: nextStatus
      });
      // Update local state
      setAssignments(prev => prev.map(a => a.id === id ? { ...a, status: nextStatus } : a));
    } catch (err) {
      console.error('Failed to toggle status:', err);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this assignment?')) return;
    try {
      await api.delete('/mcp/deleteAssignment', {
        data: { assignment_id: id }
      });
      setAssignments(prev => prev.filter(a => a.id !== id));
    } catch (err) {
      console.error('Failed to delete assignment:', err);
    }
  };

  const handleAddAssignment = async (e) => {
    e.preventDefault();
    setFormErrors([]);
    
    if (!newTitle.trim()) {
      setFormErrors(['Title is required.']);
      return;
    }
    if (!newDueDate) {
      setFormErrors(['Due date is required.']);
      return;
    }

    try {
      const res = await api.post('/mcp/addAssignment', {
        subject_id: parseInt(newSubjectId),
        title: newTitle,
        due_date: newDueDate,
        priority: newPriority
      });
      
      if (res.status === 201) {
        // Re-fetch assignments to reflect changes
        const assignRes = await api.post('/mcp/getAssignments');
        setAssignments(assignRes.data);
        
        // Reset form
        setNewTitle('');
        setNewDueDate('');
        setNewPriority('Medium');
        setShowAddForm(false);
      }
    } catch (err) {
      const msgs = err.response?.data?.messages || [err.response?.data?.message] || ['Failed to add assignment.'];
      setFormErrors(msgs);
    }
  };

  // Filter tasks based on activeTab selection
  const filteredAssignments = assignments.filter(a => {
    if (activeTab === 'All') return true;
    return a.status === activeTab;
  });

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'High':
        return 'bg-red-500/10 text-red-500';
      case 'Medium':
        return 'bg-amber-500/10 text-amber-500';
      default:
        return 'bg-blue-500/10 text-blue-500';
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[60vh]">
        <div className="w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-800 dark:text-white">Assignment Manager</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
            Track, complete, and add deadlines for assignments.
          </p>
        </div>
        <button
          onClick={() => setShowAddForm(true)}
          className="flex items-center justify-center gap-2 px-4 py-2.5 bg-brand-500 hover:bg-brand-600 active:bg-brand-700 text-white rounded-xl text-xs font-bold shadow transition"
        >
          <Plus size={16} />
          Add Assignment
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-xl border border-red-100 text-xs">
          {error}
        </div>
      )}

      {/* Tabs Filter */}
      <div className="flex border-b border-slate-200 dark:border-slate-800 gap-6">
        {['Pending', 'Completed', 'All'].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`pb-3 text-xs font-bold transition-all relative
              ${activeTab === tab 
                ? 'text-brand-500 border-b-2 border-brand-500' 
                : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'}`}
          >
            {tab} Tasks
          </button>
        ))}
      </div>

      {/* Grid listing */}
      <div className="grid grid-cols-1 gap-4">
        {filteredAssignments.length === 0 ? (
          <div className="glass-panel p-12 text-center text-slate-400 text-xs">
            No {activeTab.toLowerCase()} assignments found.
          </div>
        ) : (
          filteredAssignments.map((a) => (
            <div 
              key={a.id}
              className="glass-panel card-hover p-5 flex items-center justify-between gap-4 border border-slate-100 dark:border-slate-800/60"
            >
              <div className="flex items-start gap-4">
                {/* Complete checkbox button */}
                <button 
                  onClick={() => handleToggleStatus(a.id, a.status)}
                  className={`mt-0.5 rounded-full p-0.5 transition-colors
                    ${a.status === 'Completed' 
                      ? 'text-emerald-500 hover:text-slate-400' 
                      : 'text-slate-300 hover:text-brand-500 dark:text-slate-700'}`}
                >
                  <CheckCircle2 size={22} fill={a.status === 'Completed' ? 'currentColor' : 'transparent'} />
                </button>

                <div className="space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="px-2 py-0.5 bg-slate-100 dark:bg-slate-800 text-[10px] font-bold rounded text-slate-500">
                      {a.code}
                    </span>
                    <h4 className={`font-bold text-xs text-slate-800 dark:text-slate-200
                      ${a.status === 'Completed' ? 'line-through text-slate-400 dark:text-slate-500' : ''}`}
                    >
                      {a.title}
                    </h4>
                    <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase ${getPriorityColor(a.priority)}`}>
                      {a.priority}
                    </span>
                  </div>

                  <div className="flex items-center gap-4 text-[11px] text-slate-400">
                    <span className="flex items-center gap-1">
                      <Calendar size={13} />
                      Due: {new Date(a.due_date).toLocaleDateString()}
                    </span>
                    {a.status === 'Pending' && (
                      <span className="flex items-center gap-1 font-semibold text-slate-500">
                        <Clock size={13} />
                        {Math.ceil((new Date(a.due_date) - new Date()) / (1000 * 60 * 60 * 24))} days left
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Action buttons */}
              <button 
                onClick={() => handleDelete(a.id)}
                className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/20 rounded-xl transition"
                title="Delete Assignment"
              >
                <Trash2 size={16} />
              </button>

            </div>
          ))
        )}
      </div>

      {/* Add Assignment Popup Modal */}
      {showAddForm && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="glass-panel bg-white dark:bg-slate-900 w-full max-w-md p-6 border border-slate-200 dark:border-slate-800 rounded-2xl relative shadow-2xl">
            <button 
              onClick={() => setShowAddForm(false)}
              className="absolute top-4 right-4 p-1 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            >
              <X size={18} />
            </button>

            <h3 className="font-bold text-sm text-slate-800 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-3 mb-4">
              Create New Assignment
            </h3>

            {formErrors.length > 0 && (
              <div className="mb-4 p-2.5 bg-red-500/10 border border-red-500/20 text-xs text-red-500 rounded-xl space-y-1">
                {formErrors.map((err, i) => <p key={i}>{err}</p>)}
              </div>
            )}

            <form onSubmit={handleAddAssignment} className="space-y-4 text-xs">
              <div>
                <label className="text-slate-400 font-semibold block mb-1">Subject</label>
                <select 
                  value={newSubjectId}
                  onChange={(e) => setNewSubjectId(e.target.value)}
                  className="w-full p-2.5 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-xl focus:outline-none focus:border-brand-500 dark:text-white"
                >
                  {subjects.map(s => (
                    <option key={s.id} value={s.id}>{s.code} - {s.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-slate-400 font-semibold block mb-1">Assignment Title</label>
                <input 
                  type="text" 
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="e.g. Midterm Project report"
                  className="w-full p-2.5 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-xl focus:outline-none focus:border-brand-500 dark:text-white"
                  required
                />
              </div>

              <div>
                <label className="text-slate-400 font-semibold block mb-1">Due Date</label>
                <input 
                  type="date" 
                  value={newDueDate}
                  onChange={(e) => setNewDueDate(e.target.value)}
                  className="w-full p-2.5 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-xl focus:outline-none focus:border-brand-500 dark:text-white"
                  required
                />
              </div>

              <div>
                <label className="text-slate-400 font-semibold block mb-1">Priority</label>
                <div className="flex gap-2">
                  {['Low', 'Medium', 'High'].map(p => (
                    <button
                      key={p}
                      type="button"
                      onClick={() => setNewPriority(p)}
                      className={`flex-1 py-2 rounded-xl font-bold border transition
                        ${newPriority === p 
                          ? 'border-brand-500 bg-brand-500/10 text-brand-500' 
                          : 'border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-500'}`}
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>

              <button
                type="submit"
                className="w-full mt-2 py-3 bg-brand-500 hover:bg-brand-600 active:bg-brand-700 text-white font-bold rounded-xl shadow transition"
              >
                Add Project
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Assignments;
