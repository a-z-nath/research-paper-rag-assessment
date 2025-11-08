/**
 * API Configuration
 * 
 * Uses environment variables to configure the backend API URL.
 * Falls back to localhost:8000 for development.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const API_ENDPOINTS = {
  // Paper Management
  uploadPaper: `${API_BASE_URL}/api/papers/upload`,
  listPapers: `${API_BASE_URL}/api/papers`,
  getPaper: (id: number) => `${API_BASE_URL}/api/papers/${id}`,
  deletePaper: (id: number) => `${API_BASE_URL}/api/papers/${id}`,
  getPaperStats: (id: number) => `${API_BASE_URL}/api/papers/${id}/stats`,
  
  // Query System
  query: `${API_BASE_URL}/api/query`,
  queryHistory: `${API_BASE_URL}/api/queries/history`,
  
  // Analytics
  popularTopics: `${API_BASE_URL}/api/analytics/popular`,
  
  // Cache
  cacheStats: `${API_BASE_URL}/api/cache/stats`,
  clearCache: `${API_BASE_URL}/api/cache/clear`,
  cleanupCache: `${API_BASE_URL}/api/cache/cleanup`,
  
  // Health
  health: `${API_BASE_URL}/health`,
};

export default API_BASE_URL;
