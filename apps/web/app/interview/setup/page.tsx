'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getAccessToken } from '@/lib/supabase';
import { api, ApiError } from '@/lib/api';
import {
  Brain, ArrowLeft, ArrowRight, Code2, Layout, BarChart3,
  FlaskConical, Users, Gauge, Zap, Target
} from 'lucide-react';

interface Role {
  id: string;
  slug: string;
  display_name: string;
  category: string;
  competencies: string[];
}

const ROLE_ICONS: Record<string, React.ReactNode> = {
  'software-engineer-backend': <Code2 className="w-7 h-7" />,
  'software-engineer-frontend': <Layout className="w-7 h-7" />,
  'product-manager': <BarChart3 className="w-7 h-7" />,
  'data-scientist': <FlaskConical className="w-7 h-7" />,
  'engineering-manager': <Users className="w-7 h-7" />,
};

const ROLE_COLORS: Record<string, string> = {
  'software-engineer-backend': 'from-blue-500 to-indigo-600',
  'software-engineer-frontend': 'from-pink-500 to-rose-600',
  'product-manager': 'from-amber-500 to-orange-600',
  'data-scientist': 'from-emerald-500 to-teal-600',
  'engineering-manager': 'from-purple-500 to-violet-600',
};

const DIFFICULTIES = [
  { value: 'easy', label: 'Easy', desc: 'Junior / Entry Level', icon: <Gauge className="w-4 h-4" /> },
  { value: 'medium', label: 'Medium', desc: 'Mid / Senior Level', icon: <Target className="w-4 h-4" /> },
  { value: 'hard', label: 'Hard', desc: 'Staff+ / Principal', icon: <Zap className="w-4 h-4" /> },
];

const TYPES = [
  { value: 'technical', label: 'Technical', desc: 'System design, coding, architecture' },
  { value: 'behavioral', label: 'Behavioral', desc: 'Leadership, conflict, teamwork' },
  { value: 'mixed', label: 'Mixed', desc: 'Blend of technical and behavioral' },
];

export default function InterviewSetupPage() {
  const router = useRouter();
  const [roles, setRoles] = useState<Role[]>([]);
  const [selectedRole, setSelectedRole] = useState<string>('');
  const [difficulty, setDifficulty] = useState('medium');
  const [interviewType, setInterviewType] = useState('mixed');
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadRoles();
  }, []);

  const loadRoles = async () => {
    try {
      const token = await getAccessToken();
      if (!token) { router.push('/auth/login'); return; }
      const data = await api.getRoles(token);
      setRoles(data);
      if (data.length > 0) setSelectedRole(data[0].slug);
    } catch (err) {
      console.error('Failed to load roles:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleStartInterview = async () => {
    setCreating(true);
    setError(null);
    try {
      const token = await getAccessToken();
      if (!token) { router.push('/auth/login'); return; }

      const result = await api.createInterview(token, {
        role_slug: selectedRole,
        difficulty,
        interview_type: interviewType,
      });

      router.push(`/interview/${result.id}`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 402) {
        setError('You\'ve reached your free plan limit (3 interviews/month). Upgrade to Pro for unlimited interviews.');
      } else {
        setError('Failed to create interview. Please try again.');
      }
      setCreating(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-100">
        <div className="w-8 h-8 border-3 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface-100">
      {/* Nav */}
      <nav className="sticky top-0 z-50 glass border-b border-white/20">
        <div className="max-w-5xl mx-auto px-6 h-16 flex items-center gap-4">
          <button onClick={() => router.push('/dashboard')} className="p-2 rounded-lg hover:bg-gray-100 transition-colors">
            <ArrowLeft className="w-5 h-5 text-gray-600" />
          </button>
          <div className="flex items-center gap-2">
            <Brain className="w-6 h-6 text-primary-500" />
            <span className="text-lg font-bold gradient-text">New Interview</span>
          </div>
        </div>
      </nav>

      <main className="max-w-3xl mx-auto px-6 py-10">
        {/* Step 1: Role */}
        <section className="mb-10">
          <h2 className="text-xl font-bold text-gray-900 mb-1">Choose Your Role</h2>
          <p className="text-gray-500 text-sm mb-5">Select the role you&apos;re preparing for</p>

          <div className="grid sm:grid-cols-2 gap-3">
            {roles.map((role) => (
              <button
                key={role.slug}
                onClick={() => setSelectedRole(role.slug)}
                className={`relative p-5 rounded-xl border-2 text-left transition-all ${
                  selectedRole === role.slug
                    ? 'border-primary-400 bg-primary-50/50 shadow-md'
                    : 'border-gray-200 bg-white hover:border-primary-200 hover:bg-primary-50/30'
                }`}
              >
                <div className="flex items-start gap-4">
                  <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${ROLE_COLORS[role.slug] || 'from-gray-400 to-gray-600'} flex items-center justify-center text-white flex-shrink-0`}>
                    {ROLE_ICONS[role.slug] || <Code2 className="w-6 h-6" />}
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{role.display_name}</h3>
                    <p className="text-xs text-gray-500 mt-1 capitalize">{role.category}</p>
                    <div className="flex flex-wrap gap-1 mt-2">
                      {role.competencies.slice(0, 3).map((c) => (
                        <span key={c} className="text-[10px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">
                          {c.replace(/_/g, ' ')}
                        </span>
                      ))}
                      {role.competencies.length > 3 && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
                          +{role.competencies.length - 3}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                {selectedRole === role.slug && (
                  <div className="absolute top-3 right-3 w-5 h-5 rounded-full bg-primary-500 flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                )}
              </button>
            ))}
          </div>
        </section>

        {/* Step 2: Difficulty */}
        <section className="mb-10">
          <h2 className="text-xl font-bold text-gray-900 mb-1">Difficulty Level</h2>
          <p className="text-gray-500 text-sm mb-5">Questions are calibrated to your target seniority</p>

          <div className="grid grid-cols-3 gap-3">
            {DIFFICULTIES.map((d) => (
              <button
                key={d.value}
                onClick={() => setDifficulty(d.value)}
                className={`p-4 rounded-xl border-2 text-center transition-all ${
                  difficulty === d.value
                    ? 'border-primary-400 bg-primary-50/50 shadow-md'
                    : 'border-gray-200 bg-white hover:border-primary-200'
                }`}
              >
                <div className="flex justify-center mb-2 text-primary-500">{d.icon}</div>
                <div className="font-semibold text-gray-900 text-sm">{d.label}</div>
                <div className="text-xs text-gray-500 mt-0.5">{d.desc}</div>
              </button>
            ))}
          </div>
        </section>

        {/* Step 3: Type */}
        <section className="mb-10">
          <h2 className="text-xl font-bold text-gray-900 mb-1">Interview Type</h2>
          <p className="text-gray-500 text-sm mb-5">Choose the focus area for your practice</p>

          <div className="grid grid-cols-3 gap-3">
            {TYPES.map((t) => (
              <button
                key={t.value}
                onClick={() => setInterviewType(t.value)}
                className={`p-4 rounded-xl border-2 text-center transition-all ${
                  interviewType === t.value
                    ? 'border-primary-400 bg-primary-50/50 shadow-md'
                    : 'border-gray-200 bg-white hover:border-primary-200'
                }`}
              >
                <div className="font-semibold text-gray-900 text-sm">{t.label}</div>
                <div className="text-xs text-gray-500 mt-1">{t.desc}</div>
              </button>
            ))}
          </div>
        </section>

        {/* Summary & Start */}
        <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm">
          <h3 className="font-semibold text-gray-900 mb-3">Interview Summary</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm mb-6">
            <div>
              <span className="text-gray-500">Role</span>
              <p className="font-medium capitalize">{selectedRole.replace(/-/g, ' ')}</p>
            </div>
            <div>
              <span className="text-gray-500">Difficulty</span>
              <p className="font-medium capitalize">{difficulty}</p>
            </div>
            <div>
              <span className="text-gray-500">Type</span>
              <p className="font-medium capitalize">{interviewType}</p>
            </div>
            <div>
              <span className="text-gray-500">Questions</span>
              <p className="font-medium">10 questions</p>
            </div>
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm mb-4">{error}</div>
          )}

          <button
            onClick={handleStartInterview}
            disabled={creating || !selectedRole}
            className="w-full btn-primary py-4 text-lg flex items-center justify-center gap-2"
          >
            {creating ? (
              <>
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Starting...
              </>
            ) : (
              <>
                Start Interview
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </div>
      </main>
    </div>
  );
}
