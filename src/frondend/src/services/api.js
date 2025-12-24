/**
 * API service để gọi backend
 */

import axios from "axios";

// Base URL của API backend
const API_BASE_URL = "http://localhost:8000/api/v1";

// Tạo axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// ============================ STOCK API ===============================
/**
 * Lấy danh sách tất cả stocks
 */
export const getAllStocks = async () => {
  const response = await apiClient.get("/stocks/");
  return response.data;
};

/**
 * Lấy tóm tắt stock
 */
export const getStockSummary = async (ticker) => {
  const response = await apiClient.get(`/stocks/${ticker}/summary`);
  return response.data;
};

/**
 * Lấy lịch sử giá
 */
export const getStockHistory = async (ticker, days = 30) => {
  const response = await apiClient.get(`/stocks/${ticker}/history`, {
    params: { days },
  });
  return response.data;
};

/**
 * Lấy giá mới nhất
 */
export const getLatestPrice = async (ticker) => {
  const response = await apiClient.get(`/stocks/${ticker}/latest`);
  return response.data;
};

/**
 * Tìm kiếm stocks
 */
export const searchStocks = async (criteria) => {
  const response = await apiClient.post(`/stocks/search/`, criteria);
  return response.data;
};

// ================================== PREDICTIONS API ============================

/**
 * Lấy predictions
 */
export const getPredictions = async (ticker) => {
  const response = await apiClient.get(`/predictions/${ticker}`);
  return response.data;
};

/**
 * Lấy 3-day predictions
 */
export const get3DayPrediction = async (ticker) => {
  const response = await apiClient.get(`/predictions/${ticker}/3day`);
  return response.data;
};

// =================================== ALERTS API =================================

/**
 * Lấy danh sách alerts
 */
export const getAlerts = async (ticker = null, limit = 50) => {
  const params = { limit };
  if (ticker) params.ticker = ticker;

  const response = await apiClient.get(`/alerts`, { params });
  return response.data;
};

/**
 * Lấy alerts của ticker
 */
export const getAlertByTicker = async (ticker, limit = 50) => {
  const response = await apiClient.get(`/alerts/${ticker}`, {
    params: { limit },
  });
  return response.data;
};

// Export default
export default {
  getAllStocks,
  getStockSummary,
  getStockHistory,
  getPredictions,
  getLatestPrice,
  get3DayPrediction,
  searchStocks,
  getAlerts,
  getAlertByTicker,
};
