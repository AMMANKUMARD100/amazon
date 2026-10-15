import React, { useState, useEffect } from 'react';
import { 
  CalendarDays, 
  HelpCircle, 
  BookOpen, 
  Sparkles,
  CheckCircle,
  Plus,
  Loader2,
  Calendar,
  Clock,
  AlertCircle,
  Save,
  CheckCircle2
} from 'lucide-react';
import api from '../services/api';

const StudyPlanner = () => {
  const [plannerData, setPlannerData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState('');
  
  // Custom User Inputs for Grounded Planning
  const [dailyHours, setDailyHours] = useState(3.0);
  const [examDateCS, setExamDateCS] = useState('2026-11-15');
  const [priorityCS, setPriorityCS] = useState('High');
  const [examDateMAT, setExamDateMAT] = useState('2026-11-20');
  const [priorityMAT, setPriorityMAT] = useState('Medium');

  const handleGeneratePlan = async () => {
    try {
      setLoading(true);
      setError(null);
      setSuccessMsg('');

      const preferences = {
        daily_hours: parseFloat(dailyHours),
        exam_dates: {
          "CS101": examDateCS,
          "MAT201": examDateMAT
        },
        priorities: {
          "CS101": priorityCS,
          "MAT201": priorityMAT
        }
      };

      const res = await api.post('/agents/planner', preferences);
      setPlannerData(res.data);
    } catch (err) {
      console.error(err);
      setError('Could not run PlannerAgent. Please ensure backend server is reachable.');
    } finally {
      setLoading(false);
    }
  };

  const handleSavePlan = async () => {
    if (!plannerData || !plannerData.study_plan || plannerData.study_plan.length === 0) return;
    try {
      setSaving(true);
      setError(null);
      const res = await api.post('/agents/planner/save', {
        slots: plannerData.study_plan
      });
      setSuccessMsg(res.data.message || 'Weekly study schedule successfully persisted to your calendar!');
      setPlannerData(null);
    } catch (err) {
      console.error(err);
      setError(err?.response?.data?.message || 'Failed to persist study slots in database.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in pb-12">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-800 dark:text-white">
              Grounded Study Planner Agent
            </h1>
            <span className="px-2.5 py-0.5 text-[10px] font-bold bg-brand-500/10 text-brand-500 dark:text-brand-400 rounded-full border border-brand-500/20">
              Agent-Verified
            </span>
          </div>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
            Generate and schedule personalized study sessions based on verified exam dates, available hours, and pending tasks.
          </p>
        </div>
        <button
          onClick={handleGeneratePlan}
          disabled={loading}
          className="flex items-center justify-center gap-2 px-5 py-2.5 bg-brand-500 hover:bg-brand-600 disabled:opacity-50 text-white rounded-xl text-xs font-bold shadow-md shadow-brand-500/20 transition cursor-pointer"
        >
          {loading ? <Loader2 className="animate-spin" size={16} /> : <Sparkles size={16} />}
          <span>Synthesize Study Plan</span>
        </button>
      </div>

      {/* Notifications / Alerts */}
      {error && (
        <div className="p-4 bg-red-100 dark:bg-red-950/20 text-red-700 dark:text-red-400 rounded-xl border border-red-200 dark:border-red-900/50 flex items-center gap-3 text-xs font-medium">
          <AlertCircle size={18} />
          {error}
        </div>
      )}

      {successMsg && (
        <div className="p-4 bg-emerald-100 dark:bg-emerald-950/20 text-emerald-700 dark:text-emerald-400 rounded-xl border border-emerald-200 dark:border-emerald-900/50 flex items-center gap-3 text-xs font-medium">
          <CheckCircle2 size={18} />
          {successMsg}
        </div>
      )}

      {/* User Preferences Card */}
      <div className="glass-panel p-6 rounded-2xl space-y-4">
        <h3 className="font-bold text-sm text-slate-800 dark:text-white flex items-center gap-2">
          <Clock size={16} className="text-brand-500" />
          Study Preferences & Exam Dates (No Invented Data)
        </h3>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          The planner requires verified user inputs. Only real exam dates and designated study hours will be scheduled.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
          {/* Daily Study Hours */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
              Daily Available Hours
            </label>
            <input 
              type="number" 
              step="0.5" 
              min="1.0" 
              max="8.0"
              value={dailyHours}
              onChange={(e) => setDailyHours(e.target.value)}
              className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 focus:outline-none focus:border-brand-500"
            />
          </div>

          {/* CS101 Exam Date */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
              CS101 Exam Date
            </label>
            <input 
              type="date" 
              value={examDateCS}
              onChange={(e) => setExamDateCS(e.target.value)}
              className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 focus:outline-none focus:border-brand-500"
            />
          </div>

          {/* MAT201 Exam Date */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
              MAT201 Exam Date
            </label>
            <input 
              type="date" 
              value={examDateMAT}
              onChange={(e) => setExamDateMAT(e.target.value)}
              className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 focus:outline-none focus:border-brand-500"
            />
          </div>
        </div>
      </div>

      {/* Generated Study Plan Output */}
      {plannerData && plannerData.study_plan && (
        <div className="glass-panel p-6 rounded-2xl space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 dark:border-slate-800 pb-4">
            <div>
              <h3 className="font-bold text-sm text-slate-800 dark:text-white">
                Generated 7-Day Study Schedule ({plannerData.study_plan.length} Sessions)
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Targeting {plannerData.daily_target_hours} hours/day with exam proximity sprint weighting.
              </p>
            </div>
            <button
              onClick={handleSavePlan}
              disabled={saving}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-xl text-xs font-semibold transition shadow-sm cursor-pointer"
            >
              {saving ? <Loader2 className="animate-spin" size={14} /> : <Save size={14} />}
              <span>Confirm & Persist to Database</span>
            </button>
          </div>

          {/* Slots Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {plannerData.study_plan.map((slot, index) => (
              <div 
                key={index}
                className="p-4 bg-white dark:bg-slate-800/60 rounded-xl border border-slate-200 dark:border-slate-700/60 space-y-2 hover:border-brand-500/50 transition"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-xs text-brand-600 dark:text-brand-400">
                    {slot.code} · {slot.name}
                  </span>
                  <span className="text-[10px] font-semibold px-2 py-0.5 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded">
                    {slot.date}
                  </span>
                </div>
                <p className="text-xs text-slate-700 dark:text-slate-300 font-medium">
                  {slot.topic}
                </p>
                <div className="flex items-center gap-1.5 text-[11px] text-slate-400 pt-1">
                  <Clock size={12} />
                  <span>{slot.start_time} - {slot.end_time}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default StudyPlanner;
