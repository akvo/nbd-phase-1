'use client';

import React, { useState, useEffect, use } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api';
import { ArrowLeft, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import Link from 'next/link';

// Dynamically import akvo-react-form to prevent SSR issues if any
import dynamic from 'next/dynamic';
// const AkvoReactForm = dynamic(() => import('akvo-react-form'), {
//   ssr: false,
//   loading: () => (
//     <div className="flex items-center space-x-2 text-slate-500 py-4">
//       <Loader2 className="w-5 h-5 animate-spin" />
//       <span>Loading form builder...</span>
//     </div>
//   ),
// });

interface NewFormPageProps {
  params: Promise<{
    formId: string;
  }>;
}

export default function NewFormPage({ params }: NewFormPageProps) {
  const router = useRouter();
  const { formId } = use(params);
  const [blueprint, setBlueprint] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);
    apiClient
      .get(`/forms/${formId}/blueprint`)
      .then((res) => {
        if (active) {
          setBlueprint(res.data);
          setError(null);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err.response?.data?.detail || 'Failed to fetch form blueprint');
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [formId]);

  const handleFinish = async (values: any) => {
    setSubmitting(true);
    setError(null);
    try {
      let endpoint = '/internal/submit';
      let payload = { ...values, form_id: formId };

      if (formId === 'fgd') {
        endpoint = '/internal/fgd';
        // Format specific payload matching FGD expectation
        // FGD endpoint expects answers matching FgdPayload structure
        // we'll pass the form_id, wetland_id, and mapped answers array
        const wetlandId = values.wetland_id || values.geo_anchor || values.wetland;
        const answersList = Object.keys(values)
          .filter((key) => key !== 'wetland_id' && key !== 'wetland' && key !== 'geo_anchor' && key !== 'form_id')
          .map((key) => ({
            question_id: parseInt(key, 10) || 0,
            value: values[key],
          }));

        payload = {
          wetland_id: wetlandId,
          form_id: parseInt(formId, 10) || 1, // Fallback to 1 if NaN
          answers: answersList,
        };
      } else if (formId === 'lab-qa') {
        endpoint = '/internal/lab-qa';
        // Format specific payload matching LabQaPayload structure
        const siteId = values.site_id || values.geo_anchor || values.site;
        const samplingPeriod = values.sampling_period || '2026-Q2';
        const answersList = Object.keys(values)
          .filter(
            (key) =>
              key !== 'site_id' &&
              key !== 'site' &&
              key !== 'sampling_period' &&
              key !== 'geo_anchor' &&
              key !== 'form_id'
          )
          .map((key) => ({
            question_id: parseInt(key, 10) || 0,
            value: values[key],
          }));

        payload = {
          site_id: siteId,
          sampling_period: samplingPeriod,
          form_id: parseInt(formId, 10) || 2, // Fallback to 2 if NaN
          answers: answersList,
        };
      } else {
        // Generic submission
        const basinId = values.basin_id || values.basin;
        const wetlandId = values.wetland_id || values.wetland;
        const siteId = values.site_id || values.site;
        const answersList = Object.keys(values)
          .filter(
            (key) =>
              key !== 'basin_id' &&
              key !== 'basin' &&
              key !== 'wetland_id' &&
              key !== 'wetland' &&
              key !== 'site_id' &&
              key !== 'site' &&
              key !== 'form_id'
          )
          .map((key) => ({
            question_id: parseInt(key, 10) || 0,
            value: values[key],
          }));

        payload = {
          form_id: parseInt(formId, 10) || 3,
          basin_id: basinId,
          wetland_id: wetlandId,
          site_id: siteId,
          answers: answersList,
        };
      }

      await apiClient.post(endpoint, payload);
      setSuccess(true);
      setTimeout(() => {
        router.push('/admin/data');
      }, 1500);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit data. Please check your inputs.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
        <Loader2 className="w-8 h-8 text-sky-500 animate-spin" />
        <p className="text-slate-500 text-sm">Fetching form blueprint definition...</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto my-8 px-4">
      {/* Back Button */}
      <Link
        href="/admin/data"
        className="inline-flex items-center space-x-2 text-sm text-slate-500 hover:text-slate-800 mb-6 transition-colors group"
      >
        <ArrowLeft className="w-4 h-4 transition-transform group-hover:-translate-x-0.5" />
        <span>Back to Data Overview</span>
      </Link>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {/* Header Banner */}
        <div className="bg-gradient-to-r from-sky-500 to-indigo-600 p-6 text-white">
          <h1 className="text-2xl font-bold tracking-tight">Submit New Form Data</h1>
          <p className="text-sky-100/90 text-sm mt-1">
            Form Identifier: <span className="font-semibold font-mono bg-white/10 px-1.5 py-0.5 rounded text-xs">{formId}</span>
          </p>
        </div>

        {/* Content Area */}
        <div className="p-6">
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-100 rounded-xl flex items-start space-x-3 text-red-700 text-sm animate-shake">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {success ? (
            <div className="py-12 flex flex-col items-center justify-center space-y-4 text-center">
              <div className="w-16 h-16 bg-emerald-50 rounded-full flex items-center justify-center text-emerald-500 border border-emerald-100 animate-bounce">
                <CheckCircle2 className="w-10 h-10" />
              </div>
              <h2 className="text-xl font-bold text-slate-800">Submission Successful!</h2>
              <p className="text-slate-500 text-sm max-w-sm">
                Your data has been successfully ingested. Redirecting you back to the data overview...
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {blueprint ? (
                <div className="prose prose-slate max-w-none">
                  {/* <AkvoReactForm form={blueprint} onFinish={handleFinish} /> */}
                </div>
              ) : (
                <div className="text-center py-12 border-2 border-dashed border-slate-200 rounded-2xl">
                  <p className="text-slate-400 text-sm">No blueprint definition was loaded.</p>
                </div>
              )}

              {submitting && (
                <div className="fixed inset-0 bg-slate-900/25 backdrop-blur-sm flex items-center justify-center z-50">
                  <div className="bg-white rounded-2xl p-6 shadow-xl border border-slate-100 flex items-center space-x-4 max-w-xs">
                    <Loader2 className="w-6 h-6 text-sky-500 animate-spin" />
                    <span className="text-sm font-medium text-slate-700">Submitting response...</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
