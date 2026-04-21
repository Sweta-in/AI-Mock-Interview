'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase, getAccessToken } from '@/lib/supabase';
import { api } from '@/lib/api';
import { SkillChart } from '@/components/dashboard/SkillChart';
import { InterviewHistory } from '@/components/dashboard/InterviewHistory';
import { Brain, Plus, LogOut, Crown, TrendingUp, Target, Clock } from 'lucide-react';

interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  plan: string;
  interviews_used_this_month: number;
}

interface InterviewItem {
  id: string;
  role_slug: string;
  role_name: string;
  status: string;
  difficulty: string;
  interview_type: string;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  overall_score: number | null;
  question_count: number;
}

interface SkillSnapshot {
  snapshot_date: string;
  skill_scores: Record<string, number>;
  interviews_count: number;
}

export default function DashboardPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [interviews, setInterviews] = useState<InterviewItem[]>([]);
  const [snapshots, setSnapshots] = useState<SkillSnapshot[]>([]);
  const [totalInterviews, setTotalInterviews] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const token = await getAccessToken();
      if (!token) {
        router.push('/auth/login');
        return;
      }

      const [profileData, interviewData, skillData] = await Promise.all([
        api.getProfile(token),
        api.listInterviews(token, 1, 10),
        api.getSkillSnapshots(token).catch(() => ({ snapshots: [] })),
      ]);

      setProfile(profileData);
      setInterviews(interviewData.interviews);
      setTotalInterviews(interviewData.total);
      setSnapshots(skillData.snapshots);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.push('/');
  };

  const avgScore = interviews
    .filter((i) => i.overall_score !== null)
    .reduce((sum, i, _, arr) => sum + (i.overall_score || 0) / arr.length, 0);

  const completedCount = interviews.filter((i) => i.status === 'completed').length;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-100">
        <div className="flex items-center gap-3 text-primary-600">
          <div className="w-8 h-8 border-3 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
          <span className="text-lg font-medium">Loading dashboard...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface-100">
      {/* ── Navigation ──────────────────────────────────────────────── */}
      <nav className="sticky top-0 z-50 glass border-b border-white/20">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold gradient-text">PrepAI</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary-50 border border-primary-200">
              <Crown className="w-4 h-4 text-primary-600" />
              <span className="text-sm font-medium text-primary-700 capitalize">{profile?.plan} Plan</span>
            </div>
            <button
              onClick={handleLogout}
              className="p-2 rounded-lg text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition-colors"
              title="Sign out"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </nav>

      {/* ── Main Content ────────────────────────────────────────────── */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Welcome & CTA */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              Welcome back, {profile?.full_name?.split(' ')[0] || 'there'} 👋
            </h1>
            <p className="text-gray-500 mt-1">
              {profile?.interviews_used_this_month || 0} of 3 free interviews used this month
            </p>
          </div>
          <button
            onClick={() => router.push('/interview/setup')}
            className="btn-primary flex items-center gap-2 mt-4 sm:mt-0"
          >
            <Plus className="w-5 h-5" />
            Start New Interview
          </button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[
            {
              icon: <Target className="w-5 h-5" />,
              label: 'Total Interviews',
              value: totalInterviews.toString(),
              color: 'from-blue-500 to-indigo-600',
              bg: 'bg-blue-50',
            },
            {
              icon: <TrendingUp className="w-5 h-5" />,
              label: 'Average Score',
              value: avgScore > 0 ? `${avgScore.toFixed(0)}/100` : '—',
              color: 'from-emerald-500 to-teal-600',
              bg: 'bg-emerald-50',
            },
            {
              icon: <Clock className="w-5 h-5" />,
              label: 'Completed',
              value: completedCount.toString(),
              color: 'from-amber-500 to-orange-600',
              bg: 'bg-amber-50',
            },
            {
              icon: <Crown className="w-5 h-5" />,
              label: 'Plan',
              value: profile?.plan === 'pro' ? 'Pro' : 'Free',
              color: 'from-purple-500 to-pink-600',
              bg: 'bg-purple-50',
            },
          ].map((stat) => (
            <div key={stat.label} className="bg-white rounded-xl border border-gray-100 p-5 card-hover">
              <div className="flex items-center gap-3 mb-3">
                <div className={`w-10 h-10 rounded-lg ${stat.bg} flex items-center justify-center`}>
                  <div className={`bg-gradient-to-br ${stat.color} bg-clip-text text-transparent`}>
                    {stat.icon}
                  </div>
                </div>
                <span className="text-sm text-gray-500">{stat.label}</span>
              </div>
              <div className="text-2xl font-bold text-gray-900">{stat.value}</div>
            </div>
          ))}
        </div>

        {/* Charts & History */}
        <div className="grid lg:grid-cols-5 gap-6">
          {/* Skill Chart — wider */}
          <div className="lg:col-span-3 bg-white rounded-xl border border-gray-100 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Skill Progress</h2>
            {snapshots.length > 0 ? (
              <SkillChart snapshots={snapshots} />
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-gray-400">
                <TrendingUp className="w-12 h-12 mb-3 opacity-50" />
                <p className="text-sm">Complete interviews to see your skill progress</p>
              </div>
            )}
          </div>

          {/* Interview History */}
          <div className="lg:col-span-2 bg-white rounded-xl border border-gray-100 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Interviews</h2>
            <InterviewHistory interviews={interviews} />
          </div>
        </div>
      </main>
    </div>
  );
}
