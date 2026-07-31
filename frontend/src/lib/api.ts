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

export const adminApiClient = axios.create({
  baseURL: "/api/v1/admin",
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true,
});

adminApiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
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

export const getBasins = async (): Promise<Record<string, unknown>[]> => {
  const response = await apiClient.get("/basins");
  return response.data;
};

export const getSites = async (params?: {
  search?: string;
  health_class?: string;
  basin?: string;
}): Promise<Record<string, unknown>[]> => {
  const response = await apiClient.get("/sites", { params });
  return response.data;
};

export const getSubmissions = async (params?: {
  status?: string;
  form_id?: number;
  domain?: string;
  brief?: boolean;
}): Promise<Record<string, unknown>[]> => {
  const response = await apiClient.get("/submissions", { params });
  return response.data;
};

export const getSubmissionDetails = async (
  id: string | number
): Promise<Record<string, unknown>> => {
  const response = await apiClient.get(`/submissions/${id}`);
  return response.data;
};

export interface GenericSamplingHistory {
  id: string;
  sampled_at: string;
  parameters: Record<string, unknown>;
}

export interface GenericScoreHistory {
  id: string;
  calculated_at: string;
  composite_score: number;
  ik_signal_value: number;
  adjusted_score: number;
  health_class: string;
  breakdown: Record<string, unknown>;
}

export const getSiteSamplings = async (
  siteId: string,
  params?: { date_from?: string; date_to?: string }
): Promise<GenericSamplingHistory[]> => {
  const response = await apiClient.get(`/sites/${siteId}/samplings`, {
    params,
  });
  return response.data;
};

export const getSiteScores = async (
  siteId: string,
  params?: { date_from?: string; date_to?: string }
): Promise<GenericScoreHistory[]> => {
  const response = await apiClient.get(`/sites/${siteId}/scores`, { params });
  return response.data;
};

export type MonitoringDomain = "wetland" | "pollution";

export interface IncidentSummary {
  id: string | number;
  form_name: string;
  basin_id?: string;
  site_id?: string;
  geo?: { type: string; coordinates: [number, number] };
  created_at?: string;
  status: string;
  description?: string;
  name?: string;
  image_url?: string;
  incident_type_name?: string;
  incident_type_id?: number | string;
  reported_location?: string;
  answers: Array<{
    name?: string;
    question_id?: number;
    question_label?: string;
    question_name?: string;
    value?: string;
    options?: Array<string | number>;
    read_url?: string;
  }>;
}

export const getForms = async (params?: {
  lang?: string;
}): Promise<Record<string, any>[]> => {
  const response = await apiClient.get("/forms", { params });
  return response.data;
};

export const getForm = async (
  formId: number | string,
  params?: { lang?: string }
): Promise<Record<string, any>> => {
  const response = await apiClient.get(`/forms/${formId}`, { params });
  return response.data;
};

export interface RasterLegendItem {
  value: number;
  color: string;
  label: string;
}

export interface RasterLayerDetail {
  name: string;
  url: string;
  attribution: string;
  legend: RasterLegendItem[];
}

export interface RasterLayersResponse {
  ndvi: RasterLayerDetail;
  water_extent: RasterLayerDetail;
}

export const getRasterLayers = async (): Promise<RasterLayersResponse> => {
  const response = await apiClient.get("/raster-layers");
  return response.data;
};
