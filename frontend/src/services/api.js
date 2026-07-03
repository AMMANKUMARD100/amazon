import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:5000/api',
  withCredentials: true, // Crucial for session cookies to function across ports
  headers: {
    'Content-Type': 'application/json',
  }
});

// Response interceptor to intercept session failures globally
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response ? error.response.status : null;
    
    if (status === 401) {
      // Session expired or unauthorized - clean up local states and redirect if not on login
      if (!window.location.pathname.endsWith('/login')) {
        window.location.href = '/login?expired=true';
      }
    } else if (status === 500) {
      // Server error - redirect to 500 page
      if (!window.location.pathname.endsWith('/500')) {
        window.location.href = '/500';
      }
    }
    
    return Promise.reject(error);
  }
);

export default api;
