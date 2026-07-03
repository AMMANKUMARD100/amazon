import React, { useState, useEffect } from 'react';
import { 
  CalendarCheck, 
  Plus, 
  Minus, 
  AlertTriangle, 
  CheckCircle,
  HelpCircle,
  TrendingDown
} from 'lucide-react';
import api from '../services/api';

const Attendance = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Projection calculator states
  const [selectedSubject, setSelectedSubject] = useState(null);
  const [simulateMiss, setSimulateMiss] = useState(1);
  const [projectionResult, setProjectionResult] = useState(null);

  useEffect(() => {
    fetchAttendance();
  }, []);

  const fetchAttendance = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/agents/attendance');
      setData(res.data);
      if (res.data.details && res.data.details.length > 0) {
        setSelectedSubject(res.data.details[0]);
      }
    } catch (err) {
      console.error(err);
      setError('Failed to fetch attendance analysis.');
    } finally {
      setLoading(false);
    }
  };

  // Run projection math
  useEffect(() => {
    if (selectedSubject) {
      const p = selectedSubject.present;
      const a = selectedSubject.absent;
      const newAbsent = a + parseInt(simulateMiss || 0);
      const newTotal = p + newAbsent;
      const newPct = newTotal > 0 ? (p / newTotal) * 100 : 100;
      
      setProjectionResult({
        percentage: newPct.toFixed(1),
        isSafe: newPct >= 75.0,
        classesNeeded: newPct < 75.0 ? Math.max(0, 3 * newAbsent - p) : 0
      });
    }
  }, [selectedSubject, simulateMiss]);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[60vh]">
        <div className="w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-center max-w-md mx-auto">
        <div className="p-4 bg-red-50 text-red-700 rounded-xl mb-4 border border-red-100">{error}</div>
        <button onClick={fetchAttendance} className="px-4 py-2 bg-brand-500 text-white rounded-xl text-xs font-bold">Retry</button>
      </div>
    );
  }

  const { details, overall_percentage, at_risk_subjects, status } = data;

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Title */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-800 dark:text-white">Attendance Concierge</h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
          Review academic criteria percentages and calculate consecutive attendance targets.
        </p>
      </div>

      {/* Numerical Stats overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="glass-panel p-5 flex items-center gap-4">
          <div className="p-3 bg-brand-500/10 text-brand-500 rounded-xl">
            <CalendarCheck size={24} />
          </div>
          <div>
            <span className="text-xs text-slate-400 font-bold uppercase tracking-wider block">Overall Average</span>
            <span className="text-xl font-bold text-slate-800 dark:text-white block">{overall_percentage}%</span>
          </div>
        </div>

        <div className="glass-panel p-5 flex items-center gap-4">
          <div className={`p-3 rounded-xl ${at_risk_subjects > 0 ? 'bg-red-500/10 text-red-500' : 'bg-green-500/10 text-green-500'}`}>
            <AlertTriangle size={24} />
          </div>
          <div>
            <span className="text-xs text-slate-400 font-bold uppercase tracking-wider block">At-Risk Courses</span>
            <span className="text-xl font-bold text-slate-800 dark:text-white block">{at_risk_subjects} Subjects</span>
          </div>
        </div>

        <div className="glass-panel p-5 flex items-center gap-4">
          <div className={`p-3 rounded-xl ${status === 'Good' ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'}`}>
            <CheckCircle size={24} />
          </div>
          <div>
            <span className="text-xs text-slate-400 font-bold uppercase tracking-wider block">Status Summary</span>
            <span className="text-xl font-bold text-slate-800 dark:text-white block">{status}</span>
          </div>
        </div>
      </div>

      {/* Main grids: Detail list and calculator */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Detailed subject listing */}
        <div className="glass-panel p-6 lg:col-span-2 space-y-6">
          <h3 className="font-bold text-sm text-slate-800 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-3">
            Academic Course Breakdown
          </h3>

          <div className="space-y-4">
            {details.map((subject) => (
              <div 
                key={subject.subject_id}
                onClick={() => setSelectedSubject(subject)}
                className={`p-4 rounded-2xl border transition-all cursor-pointer flex flex-col md:flex-row md:items-center justify-between gap-4
                  ${selectedSubject?.subject_id === subject.subject_id 
                    ? 'border-brand-500 bg-brand-50/10 dark:bg-brand-950/10 shadow' 
                    : 'border-slate-100 dark:border-slate-800/60 hover:bg-slate-50 dark:hover:bg-slate-800/20'}`}
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 bg-slate-100 dark:bg-slate-800 text-[10px] font-bold rounded text-slate-500">
                      {subject.code}
                    </span>
                    <h4 className="font-bold text-xs text-slate-800 dark:text-slate-200">
                      {subject.name}
                    </h4>
                  </div>
                  <p className="text-xs text-slate-400">
                    Lectures: {subject.present} present, {subject.absent} absent ({subject.total_classes} total)
                  </p>
                  <p className="text-[11px] font-medium text-brand-500 dark:text-brand-400 mt-1">
                    {subject.advice}
                  </p>
                </div>

                <div className="flex items-center gap-4">
                  {/* Visual Bar */}
                  <div className="w-32 bg-slate-200 dark:bg-slate-800 h-2.5 rounded-full overflow-hidden hidden sm:block">
                    <div 
                      className={`h-full rounded-full ${subject.percentage >= 75 ? 'bg-brand-500' : 'bg-red-500'}`}
                      style={{ width: `${subject.percentage}%` }}
                    />
                  </div>
                  <span className={`text-sm font-bold w-12 text-right
                    ${subject.percentage >= 75 ? 'text-slate-800 dark:text-slate-200' : 'text-red-500'}`}
                  >
                    {subject.percentage}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Interactive Projection calculator */}
        <div className="glass-panel p-6 flex flex-col justify-between">
          <div>
            <h3 className="font-bold text-sm text-slate-800 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-3 mb-4">
              Concierge Skip Calculator
            </h3>

            {selectedSubject ? (
              <div className="space-y-5 text-xs">
                <div>
                  <label className="text-slate-400 font-semibold block mb-1">Target Subject</label>
                  <select 
                    value={selectedSubject.subject_id}
                    onChange={(e) => setSelectedSubject(details.find(d => d.subject_id === parseInt(e.target.value)))}
                    className="w-full p-2.5 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-xl focus:outline-none focus:border-brand-500 dark:text-white"
                  >
                    {details.map(d => (
                      <option key={d.subject_id} value={d.subject_id}>{d.code} - {d.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-slate-400 font-semibold block mb-2">Simulate skipping future classes</label>
                  <div className="flex items-center gap-3">
                    <button 
                      onClick={() => setSimulateMiss(prev => Math.max(1, prev - 1))}
                      className="p-2 border border-slate-200 dark:border-slate-800 rounded-xl text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
                    >
                      <Minus size={16} />
                    </button>
                    <span className="font-bold text-slate-800 dark:text-white text-sm w-12 text-center">
                      {simulateMiss}
                    </span>
                    <button 
                      onClick={() => setSimulateMiss(prev => prev + 1)}
                      className="p-2 border border-slate-200 dark:border-slate-800 rounded-xl text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
                    >
                      <Plus size={16} />
                    </button>
                  </div>
                </div>

                {projectionResult && (
                  <div className="pt-4 border-t border-slate-100 dark:border-slate-800 space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Projected Attendance</span>
                      <span className={`font-bold text-sm ${projectionResult.isSafe ? 'text-slate-800 dark:text-white' : 'text-red-500'}`}>
                        {projectionResult.percentage}%
                      </span>
                    </div>

                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Status</span>
                      <span className={`font-bold px-2 py-0.5 rounded text-[10px] uppercase
                        ${projectionResult.isSafe 
                          ? 'bg-green-150/10 text-green-600 dark:text-green-400' 
                          : 'bg-red-50/10 text-red-500'}`}
                      >
                        {projectionResult.isSafe ? 'SAFE' : 'RISKY'}
                      </span>
                    </div>

                    {!projectionResult.isSafe && (
                      <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 rounded-xl leading-relaxed">
                        If you miss {simulateMiss} classes, you must attend {projectionResult.classesNeeded} consecutive classes after to reach 75%.
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <p className="text-slate-400 text-xs">No subjects available for projection.</p>
            )}
          </div>
          
          <div className="text-[10px] text-slate-400 mt-6 leading-relaxed flex gap-2">
            <HelpCircle size={14} className="shrink-0 text-slate-400 mt-0.5" />
            Calculations are rules-based. Safe margins adjust automatically with present counts.
          </div>
        </div>

      </div>
    </div>
  );
};

export default Attendance;
