import React, { useState, useEffect } from 'react';
import { User, Mail, Shield, CheckCircle, AlertCircle, Edit, Calculator, GraduationCap } from 'lucide-react';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';

const Profile = () => {
  const { user, updateProfile } = useAuth();
  const [profile, setProfile] = useState(null);
  const [subjects, setSubjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState(null);
  
  // Profile form states
  const [isEditing, setIsEditing] = useState(false);
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [updateSuccess, setUpdateSuccess] = useState('');

  // CGPA Calculator states
  const [selectedGrades, setSelectedGrades] = useState({});
  const [projectionResult, setProjectionResult] = useState(null);

  const gradePoints = { 'A': 4.0, 'B': 3.0, 'C': 2.0, 'D': 1.0, 'F': 0.0 };

  useEffect(() => {
    fetchProfileData();
  }, []);

  const fetchProfileData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const profRes = await api.get('/auth/profile');
      const subRes = await api.post('/mcp/getAttendance'); // Returns list containing course codes/names
      
      setProfile(profRes.data);
      setFullName(profRes.data.full_name);
      setEmail(profRes.data.email);
      
      // Filter unique subjects
      const uniqueSubs = [];
      const seen = new Set();
      subRes.data.forEach(item => {
        if (!seen.has(item.subject_id)) {
          seen.add(item.subject_id);
          uniqueSubs.push({ code: item.code, name: item.name });
        }
      });
      setSubjects(uniqueSubs);
      
      // Initialize default projection grades to 'A'
      const initGrades = {};
      uniqueSubs.forEach(s => {
        initGrades[s.code] = 'A';
      });
      setSelectedGrades(initGrades);
      
    } catch (err) {
      console.error(err);
      setError('Could not retrieve profile metadata.');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    try {
      setUpdating(true);
      setUpdateSuccess('');
      setError(null);
      const res = await api.put('/auth/profile', {
        full_name: fullName,
        email: email
      });
      setProfile(prev => ({ ...prev, full_name: fullName, email: email }));
      updateProfile({ full_name: fullName, email: email });
      setUpdateSuccess('Profile updated successfully.');
      setIsEditing(false);
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to update profile.');
    } finally {
      setUpdating(false);
    }
  };

  const handleCalculateProjection = async () => {
    const gradesArray = Object.keys(selectedGrades).map(code => ({
      code,
      grade: selectedGrades[code]
    }));
    
    try {
      const res = await api.post('/mcp/calculateCGPA', {
        grades: gradesArray
      });
      setProjectionResult(res.data);
    } catch (err) {
      console.error(err);
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
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-800 dark:text-white">Student Profile Settings</h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
          Review configuration details, edit contacts, and run projected cumulative CGPA equations.
        </p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-xl text-xs border border-red-100">{error}</div>
      )}

      {updateSuccess && (
        <div className="p-4 bg-green-500/10 border border-green-500/20 text-green-600 dark:text-green-400 rounded-xl text-xs flex items-center gap-2">
          <CheckCircle size={16} />
          {updateSuccess}
        </div>
      )}

      {/* Grid split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Profile Card & edit forms */}
        <div className="glass-panel p-6 lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
            <h3 className="font-bold text-sm text-slate-800 dark:text-white flex items-center gap-2">
              <User className="text-brand-500" size={18} />
              Personal Credentials
            </h3>
            {!isEditing && (
              <button 
                onClick={() => setIsEditing(true)}
                className="text-xs text-brand-500 hover:underline flex items-center gap-1 font-semibold"
              >
                <Edit size={14} />
                Edit Profile
              </button>
            )}
          </div>

          {isEditing ? (
            <form onSubmit={handleUpdateProfile} className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-slate-400 font-semibold block mb-1">Full Name</label>
                  <input 
                    type="text" 
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="w-full p-2.5 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-xl focus:outline-none focus:border-brand-500 dark:text-white"
                    required
                  />
                </div>
                <div>
                  <label className="text-slate-400 font-semibold block mb-1">Email Address</label>
                  <input 
                    type="email" 
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full p-2.5 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-xl focus:outline-none focus:border-brand-500 dark:text-white"
                    required
                  />
                </div>
              </div>

              <div className="flex gap-2 justify-end pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setIsEditing(false);
                    setFullName(profile.full_name);
                    setEmail(profile.email);
                  }}
                  className="px-4 py-2 border border-slate-200 dark:border-slate-800 text-slate-500 rounded-xl font-bold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updating}
                  className="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-xl font-bold shadow"
                >
                  {updating ? 'Saving...' : 'Save Settings'}
                </button>
              </div>
            </form>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 text-xs">
              <div className="p-4 bg-slate-50 dark:bg-slate-800/30 rounded-xl border border-slate-100 dark:border-slate-850">
                <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Full Name</span>
                <p className="text-slate-700 dark:text-slate-200 font-bold mt-1 text-sm">{profile.full_name}</p>
              </div>

              <div className="p-4 bg-slate-50 dark:bg-slate-800/30 rounded-xl border border-slate-100 dark:border-slate-850">
                <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Email Address</span>
                <p className="text-slate-700 dark:text-slate-200 font-bold mt-1 text-sm">{profile.email}</p>
              </div>

              <div className="p-4 bg-slate-50 dark:bg-slate-800/30 rounded-xl border border-slate-100 dark:border-slate-850">
                <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Matriculation Code</span>
                <p className="text-slate-700 dark:text-slate-200 font-bold mt-1 text-sm">{profile.matric_number}</p>
              </div>

              <div className="p-4 bg-slate-50 dark:bg-slate-800/30 rounded-xl border border-slate-100 dark:border-slate-850">
                <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Active Semester</span>
                <p className="text-slate-700 dark:text-slate-200 font-bold mt-1 text-sm">Semester {profile.current_semester}</p>
              </div>
            </div>
          )}

          {/* Role details details warning */}
          <div className="p-4 bg-blue-500/10 border border-brand-500/20 text-xs rounded-xl flex items-start gap-3">
            <Shield className="text-brand-500 shrink-0 mt-0.5" size={16} />
            <div className="leading-relaxed">
              <span className="font-bold text-slate-800 dark:text-slate-200">Role Status: {profile.username === 'student' ? 'Student Concierge' : 'System Admin'}</span>
              <p className="text-slate-500 dark:text-slate-400 mt-0.5">
                Privilege levels are managed by security roles. Profile editing updates contact credentials only.
              </p>
            </div>
          </div>
        </div>

        {/* CGPA Projection Calculator */}
        <div className="glass-panel p-6 flex flex-col justify-between h-[450px]">
          <div>
            <h3 className="font-bold text-sm text-slate-800 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-3 mb-4 flex items-center gap-2">
              <Calculator className="text-indigo-500" size={18} />
              CGPA Equation Projections
            </h3>

            {subjects.length > 0 ? (
              <div className="space-y-4 max-h-60 overflow-y-auto pr-1 text-xs">
                {subjects.map((sub) => (
                  <div key={sub.code} className="flex justify-between items-center py-1">
                    <span className="text-slate-500 font-semibold">{sub.code} ({sub.name})</span>
                    <select
                      value={selectedGrades[sub.code]}
                      onChange={(e) => setSelectedGrades({ ...selectedGrades, [sub.code]: e.target.value })}
                      className="p-1 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-lg text-xs"
                    >
                      {Object.keys(gradePoints).map(g => (
                        <option key={g} value={g}>{g}</option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400">No subjects registered to project grades.</p>
            )}
          </div>

          <div className="border-t border-slate-100 dark:border-slate-800 pt-4 space-y-3">
            {projectionResult && (
              <div className="p-3 bg-brand-500/10 border border-brand-500/20 text-xs rounded-xl flex items-center justify-between">
                <div>
                  <span className="text-slate-400 uppercase tracking-wide text-[9px] block font-bold">Projected CGPA</span>
                  <span className="font-bold text-slate-800 dark:text-white text-base block mt-0.5">
                    {projectionResult.projected_cgpa}
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-slate-400 uppercase tracking-wide text-[9px] block font-bold">Semester GPA</span>
                  <span className="font-bold text-indigo-500 text-base block mt-0.5">
                    {projectionResult.semester_gpa}
                  </span>
                </div>
              </div>
            )}

            <button
              onClick={handleCalculateProjection}
              disabled={subjects.length === 0}
              className="w-full py-2.5 bg-brand-500 hover:bg-brand-600 active:bg-brand-700 text-white rounded-xl text-xs font-bold shadow flex items-center justify-center gap-2"
            >
              <GraduationCap size={16} />
              Calculate Projections
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};

export default Profile;
