import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';

// Pages
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Attendance from './pages/Attendance';
import Assignments from './pages/Assignments';
import StudyPlanner from './pages/StudyPlanner';
import FAQ from './pages/FAQ';
import Profile from './pages/Profile';
import NotFound from './pages/NotFound';
import ServerError from './pages/ServerError';

// Components
import Sidebar from './components/Sidebar';
import Navbar from './components/Navbar';

// Route Guard for Authenticated Users
const PrivateRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-50 dark:bg-slate-950">
        <div className="w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

// Main Layout Wrapper
const AppLayout = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const toggleSidebar = () => setSidebarOpen(!sidebarOpen);

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors duration-300">
      
      {/* Sidebar Navigation */}
      <Sidebar isOpen={sidebarOpen} toggleSidebar={toggleSidebar} />

      {/* Screen Backdrop for Mobile sidebar */}
      {sidebarOpen && (
        <div 
          onClick={toggleSidebar}
          className="fixed inset-0 z-10 bg-slate-900/40 backdrop-blur-xs lg:hidden"
        />
      )}

      {/* Content View Container */}
      <div className="flex flex-col flex-1 overflow-hidden">
        <Navbar toggleSidebar={toggleSidebar} />
        
        <main className="flex-1 overflow-y-auto px-6 py-8">
          <div className="max-w-6xl mx-auto">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/attendance" element={<Attendance />} />
              <Route path="/assignments" element={<Assignments />} />
              <Route path="/study-planner" element={<StudyPlanner />} />
              <Route path="/faq" element={<FAQ />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/500" element={<ServerError />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </div>
        </main>
      </div>

    </div>
  );
};

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public Login Route */}
            <Route path="/login" element={<Login />} />
            
            {/* Protected App Routes */}
            <Route 
              path="/*" 
              element={
                <PrivateRoute>
                  <AppLayout />
                </PrivateRoute>
              } 
            />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
