import axios from "axios";
import { API_BASE_URL } from "../utils/constants";

// Create axios instance with base config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Response interceptor: normalise error responses
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail =
      error.response?.data?.detail ||
      error.message ||
      "An unexpected error occurred";
    return Promise.reject(new Error(detail));
  }
);

/**
 * GET request
 * @param {string} url - Endpoint path
 * @param {object} params - Query parameters
 * @returns {Promise<any>} Response data
 */
export async function get(url, params = {}) {
  const response = await apiClient.get(url, { params });
  return response.data;
}

/**
 * POST request
 * @param {string} url - Endpoint path
 * @param {object} body - Request body
 * @returns {Promise<any>} Response data
 */
export async function post(url, body) {
  const response = await apiClient.post(url, body);
  return response.data;
}

/**
 * PATCH request
 * @param {string} url - Endpoint path
 * @param {object} body - Request body
 * @returns {Promise<any>} Response data
 */
export async function patch(url, body) {
  const response = await apiClient.patch(url, body);
  return response.data;
}

export default apiClient;
