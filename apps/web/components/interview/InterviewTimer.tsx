'use client';

import { useEffect, useState } from 'react';
import { Clock, Hash } from 'lucide-react';

interface InterviewTimerProps {
  questionNum: number;
  totalQuestions: number;
}

export function InterviewTimer({ questionNum, totalQuestions }: InterviewTimerProps) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex items-center gap-4">
      {/* Question Counter */}
      <div className="flex items-center gap-1.5 text-sm">
        <Hash className="w-3.5 h-3.5 text-primary-500" />
        <span className="font-medium text-gray-700">
          Q{questionNum} <span className="text-gray-400">/ {totalQuestions}</span>
        </span>
      </div>

      {/* Timer */}
      <div className="flex items-center gap-1.5 text-sm">
        <Clock className="w-3.5 h-3.5 text-gray-400" />
        <span className="font-mono text-gray-600 tabular-nums">{formatTime(elapsed)}</span>
      </div>

      {/* Progress bar */}
      <div className="hidden sm:block w-24 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-primary-400 to-primary-600 rounded-full transition-all duration-500"
          style={{ width: `${totalQuestions > 0 ? (questionNum / totalQuestions) * 100 : 0}%` }}
        />
      </div>
    </div>
  );
}
