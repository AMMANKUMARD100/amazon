import React, { useState, useEffect } from 'react';
import { 
  BarChart2, 
  BookOpen, 
  Calendar, 
  Clock, 
  CheckCircle, 
  CheckCircle2,
  Circle,
  TrendingUp, 
  AlertTriangle,
  Plus,
  Trash2,
  GraduationCap,
  Sparkles
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
import AlexaSimulator from '../components/AlexaSimulator';

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
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Quick Add Task state
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [newTaskDate, setNewTaskDate] = useState('');
  const [newTaskPriority, setNewTaskPriority] = useState('Medium');
  const [addingTask, setAddingTask] = useState(false);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [dashRes, remRes, taskRes] = await Promise.all([
        api.get('/agents/dashboard'),
        api.get('/agents/reminders'),
        api.get('/tasks/')
      ]);
      setData(dashRes.data);
      setReminders(remRes.data.reminders || []);
      setTasks(taskRes.data || []);
    } catch (err) {
      console.error(err);
      setError('Could not retrieve dashboard analytics. Please ensure backend server is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleTask = async (taskId, currentStatus) => {
    try {
      if (currentStatus === 'Pending') {
        await api.post(`/tasks/${taskId}/complete`);
      } else {
        await api.put(`/tasks/${taskId}`, { status: 'Pending' });
      }
      fetchDashboardData();
    } catch (err) {
      console.error("Failed to toggle task", err);
    }
  };

  const handleDeleteTask = async (taskId) => {
    try {
      await api.delete(`/tasks/${taskId}`);
      fetchDashboardData();
    } catch (err) {
      console.error("Failed to delete task", err);
    }
  };

  const handleQuickAddTask = async (e) => {
    e.preventDefault();
    if (!newTaskTitle.trim() || !newTaskDate) return;
    try {
      setAddingTask(true);
      await api.post('/tasks/', {
        title: newTaskTitle.trim(),
        due_date: newTaskDate,
        priority: newTaskPriority
      });
      setNewTaskTitle('');
      setNewTaskDate('');
      fetchDashboardData();
    } catch (err) {
      console.error("Failed to add task", err);
    } finally {
      setAddingTask(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh]">
        <div className="w-12 h-12 border-4 border-brand-500 border-t-transparent rounded-full animate-spin mb-4" />
        <span className="text-slate-500 text-sm font-medium">Consulting agents for analytical insights...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-center max-w-lg mx-auto mt-10">
        <div className="p-5 bg-red-100 dark:bg-red-950/20 text-red-700 dark:text-red-400 rounded-2xl border border-red-200 dark:border-red-900/50 mb-4">
          <AlertTriangle className="mx-auto mb-2" size={32} />
          <p className="font-semibold text-sm">{error}</p>
        </div>
        <button 
          onClick={fetchDashboardData}
          className="px-5 py-2.5 bg-brand-500 text-white rounded-xl text-sm font-semibold shadow hover:bg-brand-600 transition"
        >
          Try Again
        </button>
      </div>
    );
  }

  const { metrics, charts, student_name, cgpa } = data || {
    metrics: { overall_attendance: 100, pending_assignments: 0, completed_assignments: 0, scheduled_study_hours: 0 },
    charts: { attendance: { labels: [], data: [], colors: [] }, assignments: { labels: [], data: [], colors: [] }, study_progress: { scheduled_hours: 0, weekly_target: 15, completion_percentage: 0 } },
    student_name: "Student",
    cgpa: 3.8
  };

  const attendanceChartData = {
    labels: charts?.attendance?.labels || [],
    datasets: [{
      label: 'Attendance %',
      data: charts?.attendance?.data || [],
      backgroundColor: charts?.attendance?.colors || [],
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

  const pendingTasks = tasks.filter(t => t.status === 'Pending');
  const completedTasks = tasks.filter(t => t.status === 'Completed');

  return (
    <div className="space-y-8 animate-fade-in pb-12">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-800 dark:text-white">
              Hello, {student_name}!
            </h1>
            <span className="p-1 text-brand-500 bg-brand-500/10 rounded-lg">
              <Sparkles size={18} />
            </span>
          </div>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
            CampusMate AI Concierge · Alexa+ Track Simulation Active
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs font-semibold px-4 py-2 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 rounded-xl border border-emerald-500/20">
            <TrendingUp size={16} />
            CGPA: {cgpa} / 4.0
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="glass-panel p-6 flex items-center justify-between rounded-2xl">
          <div>
            <span className="text-slate-400 text-xs font-bold uppercase tracking-wider block">Attendance</span>
            <span className="text-2xl font-extrabold text-slate-800 dark:text-white mt-1 block">
              {metrics?.overall_attendance}%
            </span>
            <span className="text-[10px] font-medium text-slate-400 mt-1 block">
              {metrics?.overall_attendance >= 75 ? 'Eligibility Safe' : 'Action Required (<75%)'}
            </span>
          </div>
          <div className={`p-3 rounded-xl ${metrics?.overall_attendance >= 75 ? 'bg-blue-500/10 text-blue-500' : 'bg-red-500/10 text-red-500'}`}>
            <BarChart2 size={24} />
          </div>
        </div>

        <div className="glass-panel p-6 flex items-center justify-between rounded-2xl">
          <div>
            <span className="text-slate-400 text-xs font-bold uppercase tracking-wider block">Pending Tasks</span>
            <span className="text-2xl font-extrabold text-slate-800 dark:text-white mt-1 block">
              {pendingTasks.length}
            </span>
            <span className="text-[10px] font-medium text-slate-400 mt-1 block">
              {completedTasks.length} tasks completed
            </span>
          </div>
          <div className="p-3 bg-amber-500/10 text-amber-500 rounded-xl">
            <BookOpen size={24} />
          </div>
        </div>

        <div className="glass-panel p-6 flex items-center justify-between rounded-2xl">
          <div>
            <span className="text-slate-400 text-xs font-bold uppercase tracking-wider block">Weekly Study</span>
            <span className="text-2xl font-extrabold text-slate-800 dark:text-white mt-1 block">
              {metrics?.scheduled_study_hours}h
            </span>
            <span className="text-[10px] font-medium text-slate-400 mt-1 block">
              Target: {charts?.study_progress?.weekly_target || 15}h
            </span>
          </div>
          <div className="p-3 bg-indigo-500/10 text-indigo-500 rounded-xl">
            <Clock size={24} />
          </div>
        </div>

        <div className="glass-panel p-6 flex items-center justify-between rounded-2xl">
          <div>
            <span className="text-slate-400 text-xs font-bold uppercase tracking-wider block">Upcoming Exams</span>
            <span className="text-2xl font-extrabold text-slate-800 dark:text-white mt-1 block">
              {metrics?.upcoming_exams_count || 0} Scheduled
            </span>
            <span className="text-[10px] font-medium text-slate-400 mt-1 block truncate max-w-[140px]">
              {metrics?.upcoming_exams && metrics.upcoming_exams.length > 0
                ? metrics.upcoming_exams.map(e => `${e.code || 'GEN'} (${e.exam_date})`).slice(0, 2).join(', ')
                : 'No upcoming exams'}
            </span>
          </div>
          <div className="p-3 bg-cyan-500/10 text-cyan-500 rounded-xl">
            <GraduationCap size={24} />
          </div>
        </div>
      </div>

      {/* Main Split: Alexa+ Assistant Simulator (Left) and Today's Tasks & Exams (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: Alexa+ Simulated Assistant Drawer */}
        <div className="lg:col-span-6">
          <AlexaSimulator onTaskAction={() => fetchDashboardData()} />
        </div>

        {/* Right Column: Interactive Tasks Management & Quick Add */}
        <div className="lg:col-span-6 space-y-6">
          
          {/* Today's Tasks Card */}
          <div className="glass-panel p-6 rounded-2xl flex flex-col h-[520px]">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3 mb-4">
              <div className="flex items-center gap-2">
                <CheckCircle className="text-brand-500" size={18} />
                <h3 className="font-bold text-sm text-slate-800 dark:text-white">
                  Today & Pending Tasks ({pendingTasks.length})
                </h3>
              </div>
              <span className="text-[10px] font-semibold text-slate-400">
                Validated & Persisted
              </span>
            </div>

            {/* Quick Add Task Form */}
            <form onSubmit={handleQuickAddTask} className="flex gap-2 mb-4">
              <input
                type="text"
                placeholder="New task title..."
                value={newTaskTitle}
                onChange={(e) => setNewTaskTitle(e.target.value)}
                className="flex-1 px-3 py-2 text-xs bg-slate-50 dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700 focus:outline-none focus:border-brand-500"
                required
              />
              <input
                type="date"
                value={newTaskDate}
                onChange={(e) => setNewTaskDate(e.target.value)}
                className="px-2.5 py-2 text-xs bg-slate-50 dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700 focus:outline-none focus:border-brand-500"
                required
              />
              <button
                type="submit"
                disabled={addingTask}
                className="px-3 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-xl text-xs font-semibold flex items-center gap-1 shadow-sm transition"
              >
                <Plus size={14} /> Add
              </button>
            </form>

            {/* Tasks Scrollable List */}
            <div className="flex-1 overflow-y-auto space-y-2.5 pr-1">
              {tasks.length === 0 ? (
                <div className="text-center py-12 text-slate-400 text-xs">
                  No tasks recorded yet. Use the form above or voice prompt Alexa!
                </div>
              ) : (
                tasks.map((task) => (
                  <div 
                    key={task.id}
                    className={`flex items-center justify-between p-3 rounded-xl border transition ${
                      task.status === 'Completed'
                        ? 'bg-slate-50/50 dark:bg-slate-900/30 border-slate-200/50 dark:border-slate-800/50 opacity-60'
                        : 'bg-white dark:bg-slate-800/50 border-slate-200 dark:border-slate-700/60 shadow-xs'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <button 
                        onClick={() => handleToggleTask(task.id, task.status)}
                        className="text-slate-400 hover:text-brand-500 transition"
                      >
                        {task.status === 'Completed' ? (
                          <CheckCircle2 size={18} className="text-emerald-500" />
                        ) : (
                          <Circle size={18} />
                        )}
                      </button>
                      <div>
                        <h4 className={`text-xs font-semibold ${task.status === 'Completed' ? 'line-through text-slate-400' : 'text-slate-800 dark:text-slate-200'}`}>
                          {task.title}
                        </h4>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[10px] text-slate-400">
                            Due: {task.due_date}
                          </span>
                          <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded ${
                            task.priority === 'High' ? 'bg-red-500/10 text-red-500' : 
                            task.priority === 'Low' ? 'bg-slate-500/10 text-slate-500' : 'bg-amber-500/10 text-amber-500'
                          }`}>
                            {task.priority}
                          </span>
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={() => handleDeleteTask(task.id)}
                      className="p-1.5 text-slate-400 hover:text-red-500 rounded-lg transition"
                      title="Delete Task"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

        </div>

      </div>

      {/* Secondary Row: Attendance by Subject & Study Progress Ring */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="glass-panel p-6 lg:col-span-2 rounded-2xl flex flex-col h-80">
          <h3 className="font-bold text-sm text-slate-800 dark:text-white mb-4">
            Attendance Status by Subject
          </h3>
          <div className="flex-1 relative min-h-0">
            <Bar data={attendanceChartData} options={attendanceChartOptions} />
          </div>
        </div>

        <div className="glass-panel p-6 rounded-2xl flex flex-col items-center justify-center text-center">
          <h3 className="font-bold text-sm text-slate-800 dark:text-white mb-2 self-start">
            Weekly Study Target
          </h3>
          <div className="my-3">
            <ProgressRing 
              radius={72} 
              stroke={10} 
              progress={charts?.study_progress?.completion_percentage || 0} 
              color="stroke-indigo-500" 
            />
          </div>
          <p className="text-xs font-semibold text-slate-800 dark:text-slate-200">
            {charts?.study_progress?.scheduled_hours || 0} hrs scheduled of {charts?.study_progress?.weekly_target || 15} hrs target
          </p>
          <p className="text-[10px] text-slate-400 mt-1 max-w-[200px]">
            Synthesized by StudyAgent based on course credit limits.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
