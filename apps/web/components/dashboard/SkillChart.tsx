'use client';

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts';

interface SkillSnapshot {
  snapshot_date: string;
  skill_scores: Record<string, number>;
  interviews_count: number;
}

interface SkillChartProps {
  snapshots: SkillSnapshot[];
}

const SKILL_COLORS: Record<string, string> = {
  technical_knowledge: '#6366F1',
  problem_solving: '#10B981',
  communication: '#F59E0B',
  depth_of_understanding: '#EF4444',
  practical_experience: '#8B5CF6',
};

export function SkillChart({ snapshots }: SkillChartProps) {
  // Transform snapshots into chart data
  const chartData = [...snapshots].reverse().map((s) => {
    const entry: Record<string, string | number> = {
      date: new Date(s.snapshot_date).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      }),
    };
    Object.entries(s.skill_scores).forEach(([skill, score]) => {
      entry[skill] = Math.round(score);
    });
    return entry;
  });

  // Get all unique skill keys
  const allSkills = new Set<string>();
  snapshots.forEach((s) => {
    Object.keys(s.skill_scores).forEach((k) => allSkills.add(k));
  });

  if (chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400 text-sm">
        No data yet
      </div>
    );
  }

  return (
    <div className="w-full h-72">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: '#9CA3AF' }}
            axisLine={{ stroke: '#E5E7EB' }}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fontSize: 11, fill: '#9CA3AF' }}
            axisLine={{ stroke: '#E5E7EB' }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#fff',
              border: '1px solid #E5E7EB',
              borderRadius: '10px',
              fontSize: '12px',
              boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: '11px' }}
            formatter={(value: string) => value.replace(/_/g, ' ')}
          />
          {Array.from(allSkills).map((skill) => (
            <Line
              key={skill}
              type="monotone"
              dataKey={skill}
              stroke={SKILL_COLORS[skill] || '#6B7280'}
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
              name={skill}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
