'use client';

import { useState } from 'react';
import type { ScoreMap } from '@/lib/store';
import { ChevronDown, ChevronUp, CheckCircle2, XCircle } from 'lucide-react';

interface FeedbackCardProps {
  scores: ScoreMap | null;
  strengths: string[];
  weaknesses: string[];
}

export function FeedbackCard({ scores, strengths, weaknesses }: FeedbackCardProps) {
  const [expanded, setExpanded] = useState(false);

  if (!scores) {
    return null;
  }

  const scoreEntries = Object.entries(scores);
  const avgScore = scoreEntries.reduce((sum, [, v]) => sum + v, 0) / scoreEntries.length;

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'bg-emerald-500';
    if (score >= 40) return 'bg-amber-500';
    return 'bg-red-500';
  };

  const getScoreBg = (score: number) => {
    if (score >= 70) return 'bg-emerald-50';
    if (score >= 40) return 'bg-amber-50';
    return 'bg-red-50';
  };

  return (
    <div className="animate-slide-right">
      {/* Collapsed header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-3 rounded-xl bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          <div className={`w-8 h-8 rounded-lg ${getScoreBg(avgScore)} flex items-center justify-center`}>
            <span className={`text-sm font-bold ${avgScore >= 70 ? 'text-emerald-700' : avgScore >= 40 ? 'text-amber-700' : 'text-red-700'}`}>
              {Math.round(avgScore)}
            </span>
          </div>
          <span className="text-sm font-medium text-gray-700">Answer Feedback</span>
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        )}
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="mt-3 space-y-4 animate-fade-in">
          {/* Score bars */}
          <div className="space-y-2">
            {scoreEntries.map(([key, value]) => (
              <div key={key} className="flex items-center gap-2">
                <span className="text-xs text-gray-500 w-24 capitalize">
                  {key.replace(/_/g, ' ')}
                </span>
                <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${getScoreColor(value)} score-bar-fill`}
                    style={{ '--score-width': `${value}%` } as React.CSSProperties}
                  />
                </div>
                <span className="text-xs font-medium text-gray-700 w-8 text-right">
                  {Math.round(value)}
                </span>
              </div>
            ))}
          </div>

          {/* Strengths */}
          {strengths.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-emerald-700 uppercase tracking-wide mb-1.5">
                Strengths
              </h4>
              <ul className="space-y-1.5">
                {strengths.map((s, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-gray-700">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0 mt-0.5" />
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Weaknesses */}
          {weaknesses.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-red-700 uppercase tracking-wide mb-1.5">
                Areas to Improve
              </h4>
              <ul className="space-y-1.5">
                {weaknesses.map((w, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-gray-700">
                    <XCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0 mt-0.5" />
                    <span>{w}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
