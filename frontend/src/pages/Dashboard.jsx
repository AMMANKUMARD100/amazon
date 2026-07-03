import React, { useState, useEffect } from 'react';
import { 
  BarChart2, 
  BookOpen, 
  Calendar, 
  Clock, 
  CheckCircle,
  FileText,
  HelpCircle,
  TrendingUp,
  AlertTriangle
} from 'lucide-react';
import { Bar, Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
} from 'chart.js';
import api from '../services/api';
import ProgressRing from '../components/ProgressRing';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

const Dashboard = () => {
  const [data, setData] = useState(null);
  const [reminders, setReminders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      const dashRes = await api.get('/agents/dashboard');
      const remRes = await api.get('/agents/reminders');
      setData(dashRes.data);
      setReminders(remRes.data.reminders || []);
    } catch (err) {
      console.error(err);
      setError('Could not retrieve dashboard analytics. Please ensure server is running.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[80vh]">
        <div className="w-12 h-12 border-4 border-brand-500 border-t-transparent rounded-full animate-spin mb-4" />
        <span className="text-slate-500 text-sm">Consulting agents for analytical insights...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-center max-w-lg mx-auto mt-10">
        <div className="p-4 bg-red-100 dark:bg-red-950/20 text-red-700 dark:text-red-400 rounded-2xl border border-red-200 dark:border-red-900/50 mb-4">
          <AlertTriangle className="mx-auto mb-2" size={32} />
          <p className="font-semibold">{error}</p>
        </div>
        <button 
          onClick={fetchDashboardData}
          className="px-4 py-2 bg-brand-500 text-white rounded-xl text-sm font-semibold shadow hover:bg-brand-600 transition"
        >
          Try Again
        </button>
      </div>
    );
  }

  const { metrics, charts, student_name, cgpa } = data;

  // Chart configs
  const attendanceChartData = {
    labels: charts.attendance.labels,
    datasets: [{
      label: 'Attendance %',
      data: charts.attendance.data,
      backgroundColor: charts.attendance.colors,
      borderRadius: 8,
      borderWidth: 0,
      maxBarThickness: 32
    }]
  };

  const attendanceChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (context) => `Attendance: ${context.parsed.y}%`
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
        grid: { color: 'rgba(148, 163, 184, 0.1)' },
        ticks: { color: '#64748b', font: { family: 'Inter' } }
      },
      x: {
        grid: { display: false },
        ticks: { color: '#64748b', font: { family: 'Inter' } }
      }
    }
  };

  const assignmentChartData = {
    labels: charts.assignments.labels,
    datasets: [{
      data: charts.assignments.data,
      backgroundColor: charts.assignments.colors,
      borderWidth: 0,
      hoverOffset: 4
    }]
  };

  const assignmentChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          color: '#64748b',
          boxWidth: 12,
          padding: 16,
          font: { family: 'Inter', size: 11 }
        }
      }
    },
    cutout: '75%'
  };

  return (
    <div className="space-y-8 animate-fade-in p-1">
      {/* Welcome Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-800 dark:text-white">
            Hello, {student_name}!
          </h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
            Here is your personalized concierge academic overview for today.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-semibold px-4 py-2 bg-brand-500/10 text-brand-500 dark:text-brand-400 rounded-xl border border-brand-500/20">
          <TrendingUp size={16} />
          Current CGPA: {cgpa}
        </div>
      </div>

      {/* Numerical Cards grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        
        {/* Attendance Widget */}
        <div className="glass-panel card-hover p-6 flex items-center justify-between">
          <div>
            <span className="text-slate-400 text-xs font-bold uppercase tracking-wider block">Attendance</span>
            <span className="text-2xl font-extrabold text-slate-800 dark:text-white mt-1 block">
              {metrics.overall_attendance}%
            </span>
            <span className="text-[10px] font-medium text-slate-400 mt-1 block">
              {metrics.overall_attendance >= 75 ? 'Eligibility status: Safe' : 'Warning: Action required'}
            </span>
          </div>
          <div className={`p-3 rounded-xl ${metrics.overall_attendance >= 75 ? 'bg-blue-500/10 text-blue-500' : 'bg-red-500/10 text-red-500'}`}>
            <BarChart2 size={24} />
          </div>
        </div>

        {/* Assignments Widget */}
        <div className="glass-panel card-hover p-6 flex items-center justify-between">
          <div>
            <span className="text-slate-400 text-xs font-bold uppercase tracking-wider block">Pending Tasks</span>
            <span className="text-2xl font-extrabold text-slate-800 dark:text-white mt-1 block">
              {metrics.pending_assignments}
            </span>
            <span className="text-[10px] font-medium text-slate-400 mt-1 block">
              {metrics.completed_assignments} tasks completed
            </span>
          </div>
          <div className="p-3 bg-amber-500/10 text-amber-500 rounded-xl">
            <BookOpen size={24} />
          </div>
        </div>

        {/* Study Hours Widget */}
        <div className="glass-panel card-hover p-6 flex items-center justify-between">
          <div>
            <span className="text-slate-400 text-xs font-bold uppercase tracking-wider block">Weekly Study</span>
            <span className="text-2xl font-extrabold text-slate-800 dark:text-white mt-1 block">
              {metrics.scheduled_study_hours}h
            </span>
            <span className="text-[10px] font-medium text-slate-400 mt-1 block">
              Hours scheduled this week
            </span>
          </div>
          <div className="p-3 bg-indigo-500/10 text-indigo-500 rounded-xl">
            <Clock size={24} />
          </div>
        </div>

        {/* CGPA Widget */}
        <div className="glass-panel card-hover p-6 flex items-center justify-between">
          <div>
            <span className="text-slate-400 text-xs font-bold uppercase tracking-wider block">Academic Stand</span>
            <span className="text-2xl font-extrabold text-slate-800 dark:text-white mt-1 block">
              {cgpa}
            </span>
            <span className="text-[10px] font-medium text-slate-400 mt-1 block">
              Cumulative score out of 4.0
            </span>
          </div>
          <div className="p-3 bg-emerald-500/10 text-emerald-500 rounded-xl">
            <TrendingUp size={24} />
          </div>
        </div>

      </div>

      {/* Main Charts and Reminders Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Attendance chart card */}
        <div className="glass-panel p-6 lg:col-span-2 flex flex-col h-80">
          <h3 className="font-bold text-sm text-slate-800 dark:text-white mb-4">
            Attendance Status by Subject
          </h3>
          <div className="flex-1 relative min-h-0">
            <Bar data={attendanceChartData} options={attendanceChartOptions} />
          </div>
        </div>

        {/* Assignments Chart Card */}
        <div className="glass-panel p-6 flex flex-col h-80 justify-between">
          <h3 className="font-bold text-sm text-slate-800 dark:text-white mb-2">
            Assignments Completion Rate
          </h3>
          <div className="flex-1 relative max-h-[180px] my-auto">
            {metrics.pending_assignments === 0 && metrics.completed_assignments === 0 ? (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">
                No active assignments.
              </div>
            ) : (
              <Doughnut data={assignmentChartData} options={assignmentChartOptions} />
            )}
          </div>
        </div>

      </div>

      {/* Secondary split grid: study progress and reminders list */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Weekly Study Ring Progress Widget */}
        <div className="glass-panel p-6 flex flex-col items-center justify-center text-center">
          <h3 className="font-bold text-sm text-slate-800 dark:text-white mb-4 self-start">
            Weekly Study Target
          </h3>
          <div className="my-3">
            <ProgressRing 
              radius={80} 
              stroke={12} 
              progress={charts.study_progress.completion_percentage} 
              color="stroke-indigo-500" 
            />
          </div>
          <p className="text-xs font-semibold text-slate-800 dark:text-slate-200 mt-2">
            {charts.study_progress.scheduled_hours} hrs scheduled of {charts.study_progress.weekly_target} hrs target
          </p>
          <p className="text-[10px] text-slate-400 mt-1 max-w-[200px]">
            Goal formulated based on registration credit limits.
          </p>
        </div>

        {/* Today's Schedule reminders list */}
        <div className="glass-panel p-6 lg:col-span-2 flex flex-col">
          <div className="flex items-center gap-2 border-b border-slate-100 dark:border-slate-800 pb-3 mb-4">
            <Calendar className="text-brand-500" size={18} />
            <h3 className="font-bold text-sm text-slate-800 dark:text-white">
              Today's Concierge Reminders
            </h3>
          </div>
          <div className="space-y-4 max-h-[220px] overflow-y-auto pr-1">
            {reminders.length === 0 ? (
              <div className="text-center py-8 text-xs text-slate-400">
                No lectures or study plans scheduled for today. Great time to relax!
              </div>
            ) : (
              reminders.map((r, idx) => (
                <div key={idx} className="flex gap-4 items-start p-3 bg-slate-50 dark:bg-slate-800/30 rounded-xl">
                  <div className={`px-2.5 py-1 text-[10px] font-bold rounded-lg uppercase shrink-0
                    ${r.type === 'Class' ? 'bg-blue-500/10 text-blue-500' : ''}
                    ${r.type === 'Study' ? 'bg-indigo-500/10 text-indigo-500' : ''}
                    ${r.type === 'Assignment' ? 'bg-amber-500/10 text-amber-500' : ''}
                  `}>
                    {r.type}
                  </div>
                  <div className="text-xs flex-1">
                    <h4 className="font-bold text-slate-800 dark:text-slate-200">{r.title}</h4>
                    <p className="text-slate-500 dark:text-slate-400 mt-0.5">{r.detail}</p>
                  </div>
                  <span className="text-[10px] font-semibold text-slate-400 shrink-0">
                    {r.time}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

      </div>
    </div>
  );
};

export default Dashboard;
