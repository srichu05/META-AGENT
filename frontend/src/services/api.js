import axios from 'axios';

// Get base URL from environment or fallback
const rawBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000/api';
// Normalize base URL: strip trailing slash
const BASE_URL = rawBaseUrl.endsWith('/') ? rawBaseUrl.slice(0, -1) : rawBaseUrl;

const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 120000, // 2 minutes for heavy multi-agent reasoning / debate runs
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor to handle data unpacking and descriptive errors
apiClient.interceptors.response.use(
  (response) => {
    // Backend returns { success: true, ... } or { success: true, data: { ... } }
    if (response.data && typeof response.data === 'object') {
      if (response.data.success === false) {
        const errorMsg = response.data.error || response.data.message || 'Operation failed on server';
        return Promise.reject(new Error(errorMsg));
      }
      if ('data' in response.data && response.data.data !== undefined) {
        return response.data.data;
      }
    }
    return response.data;
  },
  (error) => {
    if (error.response) {
      const serverMsg = error.response.data?.error || error.response.data?.message;
      const statusText = `HTTP ${error.response.status}`;
      return Promise.reject(new Error(serverMsg || `${statusText}: Server request failed`));
    } else if (error.request) {
      return Promise.reject(new Error(`Backend connection refused at ${BASE_URL}. Ensure the Flask server is running.`));
    }
    return Promise.reject(error);
  }
);

export const api = {
  // Check backend server health
  checkHealth: async () => {
    return apiClient.get('/health');
  },

  // Solve a math problem
  solveProblem: async (problem) => {
    return apiClient.post('/solve', { problem });
  },

  // Run multi-agent debate
  runDebate: async (problem, rounds = 3) => {
    return apiClient.post('/debate', { problem, rounds: Number(rounds) });
  },

  // Analyze problem patterns & get hints
  analyzeProblem: async (problem) => {
    return apiClient.post('/analyze', { problem });
  },

  // Get system statistics
  getSystemStats: async () => {
    return apiClient.get('/stats');
  },

  // Get sample benchmark problems
  getSampleProblems: async () => {
    return apiClient.get('/problems');
  },

  // Get last evaluation run metrics
  getLastEvaluation: async () => {
    return apiClient.get('/evaluation/last');
  },

  // Get active corpus documents
  getCorpus: async () => {
    return apiClient.get('/corpus');
  },

  // Upload and index new knowledge corpus (JSON or JSONL)
  uploadCorpus: async (file, onUploadProgress) => {
    const formData = new FormData();
    formData.append('file', file);

    return apiClient.post('/upload_corpus', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress,
      timeout: 300000, // 5 min for large embedding generation
    });
  },

  getBaseUrl: () => BASE_URL,
};

export default api;
