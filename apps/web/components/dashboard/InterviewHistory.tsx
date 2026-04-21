'use client';

import { useRouter } from 'next/navigation';
import { Clock, CheckCircle2, XCircle, AlertCircle, ArrowRight } from 'lucide-react';

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

interface InterviewHistoryProps {
  interviews: InterviewItem[];
}

const STATUS_CONFIG: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  completed: {
    icon: <CheckCircle2 className="w-4 h-4" />,
    color: 'text-emerald-600 bg-emerald-50',
    label: 'Completed',
  },
  active: {
    icon: <Clock className="w-4 h-4" />,
    color: 'text-blue-600 bg-blue-50',
    label: 'In Progress',
  },
  abandoned: {
    icon: <XCircle className="w-4 h-4" />,
    color: 'text-gray-500 bg-gray-100',
    label: 'Abandoned',
  },
  created: {
    icon: <AlertCircle className="w-4 h-4" />,
    color: 'text-amber-600 bg-amber-50',
    label: 'Not Started',
  },
  error: {
    icon: <XCircle className="w-4 h-4" />,
    color: 'text-red-600 bg-red-50',
    label: 'Error',
  },
};

export function InterviewHistory({ interviews }: InterviewHistoryProps) {
  const router = useRouter();

  if (interviews.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-gray-400">
        <Clock className="w-10 h-10 mb-3 opacity-50" />
        <p className="text-sm">No interviews yet</p>
        <button
          onClick={() => router.push('/interview/setup')}
          className="mt-3 text-primary-600 text-sm font-medium hover:underline"
        >
          Start your first interview →
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {interviews.map((interview) => {
        const config = STATUS_CONFIG[interview.status] || STATUS_CONFIG.error;
        const date = interview.started_at
          ? new Date(interview.started_at).toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric',
              year: 'numeric',
            })
          : 'Not started';

        return (
          <button
            key={interview.id}
            onClick={() => {
              if (interview.status === 'completed') {
                router.push(`/interview/${interview.id}`);
              }
            }}
            className="w-full flex items-center gap-3 p-3 rounded-xl hover:bg-gray-50 transition-colors text-left group"
          >
            {/* Score badge */}
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
              interview.overall_score !== null
                ? interview.overall_score >= 70
                  ? 'bg-emerald-100'
                  : interview.overall_score >= 40
                  ? 'bg-amber-100'
                  : 'bg-red-100'
                : 'bg-gray-100'
            }`}>
              <span className={`text-sm font-bold ${
                interview.overall_score !== null
                  ? interview.overall_score >= 70
                    ? 'text-emerald-700'
                    : interview.overall_score >= 40
                    ? 'text-amber-700'
                    : 'text-red-700'
                  : 'text-gray-400'
              }`}>
                {interview.overall_score !== null ? Math.round(interview.overall_score) : '—'}
              </span>
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-gray-900 truncate">
                  {interview.role_name}
                </span>
                <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${config.color}`}>
                  {config.icon}
                  {config.label}
                </span>
              </div>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-xs text-gray-500">{date}</span>
                <span className="text-xs text-gray-300">•</span>
                <span className="text-xs text-gray-500 capitalize">{interview.difficulty}</span>
                {interview.duration_seconds && (
                  <>
                    <span className="text-xs text-gray-300">•</span>
                    <span className="text-xs text-gray-500">
                      {Math.floor(interview.duration_seconds / 60)}m
                    </span>
                  </>
                )}
              </div>
            </div>

            {/* Arrow */}
            {interview.status === 'completed' && (
              <ArrowRight className="w-4 h-4 text-gray-300 group-hover:text-primary-500 transition-colors flex-shrink-0" />
            )}
          </button>
        );
      })}
    </div>
  );
}
