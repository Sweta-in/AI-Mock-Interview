'use client';

import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  ResponsiveContainer, Tooltip,
} from 'recharts';
import type { ScoreMap } from '@/lib/store';

interface ScoreRadarProps {
  scores: ScoreMap | null;
}

const DIMENSION_LABELS: Record<string, string> = {
  relevance: 'Relevance',
  depth: 'Depth',
  clarity: 'Clarity',
  communication: 'Communication',
  technical_accuracy: 'Technical',
};

export function ScoreRadar({ scores }: ScoreRadarProps) {
  if (!scores) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
        <p>Scores appear here after your first answer</p>
      </div>
    );
  }

  const data = Object.entries(scores).map(([key, value]) => ({
    dimension: DIMENSION_LABELS[key] || key,
    score: Math.round(value),
    fullMark: 100,
  }));

  return (
    <div className="w-full h-56">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="75%">
          <PolarGrid
            stroke="#E5E7EB"
            strokeDasharray="3 3"
          />
          <PolarAngleAxis
            dataKey="dimension"
            tick={{ fontSize: 10, fill: '#6B7280' }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tick={{ fontSize: 9, fill: '#9CA3AF' }}
            axisLine={false}
          />
          <Radar
            name="Score"
            dataKey="score"
            stroke="#6366F1"
            fill="#6366F1"
            fillOpacity={0.2}
            strokeWidth={2}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#fff',
              border: '1px solid #E5E7EB',
              borderRadius: '8px',
              fontSize: '12px',
              boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
            }}
            formatter={(value: number) => [`${value}/100`, 'Score']}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
