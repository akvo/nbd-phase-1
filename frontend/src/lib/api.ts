import axios from "axios";

export const apiClient = axios.create({
  baseURL: "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

export const getBasins = async (): Promise<any[]> => {
  const response = await apiClient.get("/basins");
  return response.data;
};
