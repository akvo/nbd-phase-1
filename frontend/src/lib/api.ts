import axios from "axios";

export const apiClient = axios.create({
  baseURL: "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true,
});

// Intercept 401 responses and redirect to login
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Only redirect if we're in a browser and on an admin page
      if (
        typeof window !== "undefined" &&
        window.location.pathname.startsWith("/admin")
      ) {
        window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname)}`;
      }
    }
    return Promise.reject(error);
  }
);

export const getBasins = async (): Promise<any[]> => {
  const response = await apiClient.get("/basins");
  return response.data;
};
