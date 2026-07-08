"use client";

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import { getBasins, getSites, getForms, getForm } from "@/lib/api";

interface StaticDataContextType {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  basins: Record<string, any>[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  sites: Record<string, any>[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  formsListCache: Record<string, Record<string, any>[]>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  formDetailsCache: Record<string, Record<number, Record<string, any>>>;
  isLoading: {
    basins: boolean;
    sites: boolean;
    forms: boolean;
  };
  refreshData: () => Promise<void>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getFormDetails: (
    formId: number,
    lang: string
  ) => Promise<Record<string, any> | null>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getFormsList: (lang: string) => Promise<Record<string, any>[]>;
}

const StaticDataContext = createContext<StaticDataContextType | null>(null);

export function StaticDataProvider({
  children,
  initialLocale: _initialLocale = "en",
}: {
  children: React.ReactNode;
  initialLocale?: string;
}) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [basins, setBasins] = useState<Record<string, any>[]>([]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [sites, setSites] = useState<Record<string, any>[]>([]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [formsListCache, setFormsListCache] = useState<
    Record<string, Record<string, any>[]>
  >({});
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [formDetailsCache, setFormDetailsCache] = useState<
    Record<string, Record<number, Record<string, any>>>
  >({});

  const [isLoading, setIsLoading] = useState({
    basins: false,
    sites: false,
    forms: false,
  });

  const fetchBasins = useCallback(async () => {
    setIsLoading((prev) => ({ ...prev, basins: true }));
    try {
      const data = await getBasins();
      setBasins(data);
    } catch (err) {
      console.error("Error loading basins:", err);
    } finally {
      setIsLoading((prev) => ({ ...prev, basins: false }));
    }
  }, []);

  const fetchSites = useCallback(async () => {
    setIsLoading((prev) => ({ ...prev, sites: true }));
    try {
      const data = await getSites();
      setSites(data);
    } catch (err) {
      console.error("Error loading sites:", err);
    } finally {
      setIsLoading((prev) => ({ ...prev, sites: false }));
    }
  }, []);

  const getFormsList = useCallback(
    async (lang: string) => {
      if (formsListCache[lang]) {
        return formsListCache[lang];
      }
      setIsLoading((prev) => ({ ...prev, forms: true }));
      try {
        const data = await getForms({ lang });
        setFormsListCache((prev) => ({ ...prev, [lang]: data }));
        return data;
      } catch (err) {
        console.error(`Error loading forms list for language ${lang}:`, err);
        return [];
      } finally {
        setIsLoading((prev) => ({ ...prev, forms: false }));
      }
    },
    [formsListCache]
  );

  const getFormDetails = useCallback(
    async (formId: number, lang: string) => {
      if (formDetailsCache[lang]?.[formId]) {
        return formDetailsCache[lang][formId];
      }
      try {
        const data = await getForm(formId, { lang });
        setFormDetailsCache((prev) => ({
          ...prev,
          [lang]: {
            ...(prev[lang] || {}),
            [formId]: data,
          },
        }));
        return data;
      } catch (err) {
        console.error(
          `Error loading form ${formId} details for language ${lang}:`,
          err
        );
        return null;
      }
    },
    [formDetailsCache]
  );

  const refreshData = useCallback(async () => {
    setFormsListCache({});
    setFormDetailsCache({});
    await Promise.all([fetchBasins(), fetchSites()]);
  }, [fetchBasins, fetchSites]);

  // Load baseline datasets on mount
  useEffect(() => {
    fetchBasins();
    fetchSites();
  }, [fetchBasins, fetchSites]);

  return (
    <StaticDataContext.Provider
      value={{
        basins,
        sites,
        formsListCache,
        formDetailsCache,
        isLoading,
        refreshData,
        getFormDetails,
        getFormsList,
      }}
    >
      {children}
    </StaticDataContext.Provider>
  );
}

export function useStaticData() {
  const context = useContext(StaticDataContext);
  if (!context) {
    throw new Error("useStaticData must be used within a StaticDataProvider");
  }
  return context;
}
