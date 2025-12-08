import axios, { AxiosError, AxiosResponse } from 'axios';

/**
 * Wrapper for axios library.
 * Use httpClient instance to configure axios http instance.
 */
const httpClient = axios.create({
  timeout: 60000, // 60 seconds for AI operations
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: false,
});

/**
 * Attach request interceptor to add any auth tokens if needed
 */
httpClient.interceptors.request.use(
  (config) => {
    // Add auth token here if needed
    // const token = localStorage.getItem('token');
    // if (token && config.headers) {
    //   config.headers.set('Authorization', `Bearer ${token}`);
    // }
    return config;
  },
  (error: AxiosError) => Promise.reject(error)
);

/**
 * Attach response interceptor to handle errors
 */
httpClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    if (error.response) {
      // Server responded with error status
      console.error('API Error:', error.response.status, error.response.data);
      return Promise.reject(new Error(`${error.response.data}` || 'Unknown error'));
    }
    if (error.request) {
      // Request made but no response received
      console.error('Network Error:', error.message);
      return Promise.reject(new Error('No response received from server.'));
    }
    // Something else happened
    return Promise.reject(new Error(error.message));
  }
);

export default httpClient;
