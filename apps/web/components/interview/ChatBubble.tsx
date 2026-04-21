'use client';

import type { Message } from '@/lib/store';
import { Brain } from 'lucide-react';

interface ChatBubbleProps {
  message: Message;
}

export function ChatBubble({ message }: ChatBubbleProps) {
  const isInterviewer = message.role === 'interviewer';

  // Thinking state (animated dots)
  if (message.isThinking) {
    return (
      <div className="flex items-start gap-3 animate-fade-in">
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center flex-shrink-0">
          <Brain className="w-4 h-4 text-white" />
        </div>
        <div className="bg-gradient-to-br from-primary-50 to-indigo-50 rounded-2xl rounded-tl-md px-5 py-4 max-w-lg border border-primary-100">
          <div className="flex gap-1.5">
            <span className="w-2 h-2 rounded-full bg-primary-400 typing-dot" />
            <span className="w-2 h-2 rounded-full bg-primary-400 typing-dot" />
            <span className="w-2 h-2 rounded-full bg-primary-400 typing-dot" />
          </div>
        </div>
      </div>
    );
  }

  if (isInterviewer) {
    return (
      <div className="flex items-start gap-3 animate-slide-up">
        {/* AI Avatar */}
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center flex-shrink-0 shadow-md">
          <Brain className="w-4 h-4 text-white" />
        </div>

        {/* Bubble */}
        <div className="bg-gradient-to-br from-primary-50 to-indigo-50 rounded-2xl rounded-tl-md px-5 py-4 max-w-xl border border-primary-100 shadow-sm">
          <p className="text-gray-800 leading-relaxed whitespace-pre-wrap text-sm">
            {message.content}
          </p>
        </div>
      </div>
    );
  }

  // Candidate message
  return (
    <div className="flex items-start gap-3 justify-end animate-slide-up">
      <div className="bg-white rounded-2xl rounded-tr-md px-5 py-4 max-w-xl border border-gray-200 shadow-sm">
        <p className="text-gray-800 leading-relaxed whitespace-pre-wrap text-sm">
          {message.content}
        </p>
        {message.scores && (
          <div className="mt-3 pt-3 border-t border-gray-100 flex gap-2 flex-wrap">
            {Object.entries(message.scores).map(([key, value]) => (
              <span
                key={key}
                className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  value >= 70
                    ? 'bg-green-100 text-green-700'
                    : value >= 40
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-red-100 text-red-700'
                }`}
              >
                {key.replace(/_/g, ' ')}: {Math.round(value)}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* User Avatar */}
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-gray-200 to-gray-300 flex items-center justify-center flex-shrink-0 text-gray-600 text-xs font-bold">
        You
      </div>
    </div>
  );
}
