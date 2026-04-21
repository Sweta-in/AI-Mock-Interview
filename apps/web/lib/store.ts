/**
 * PrepAI — Zustand store for global interview state management.
 */

import { create } from 'zustand';

// ── Types ──────────────────────────────────────────────────────────────────

export interface Interview {
  id: string;
  role_slug: string;
  role_name: string;
  status: string;
  difficulty: string;
  interview_type: string;
  session_token: string;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  overall_score: number | null;
  technical_score: number | null;
  behavioral_score: number | null;
  communication_score: number | null;
  question_count: number;
}

export interface Question {
  question_id: string;
  question_text: string;
  question_num: number;
  total_questions: number;
  question_type: string;
}

export interface ScoreMap {
  relevance: number;
  depth: number;
  clarity: number;
  communication: number;
  technical_accuracy: number;
}

export interface Message {
  id: string;
  role: 'interviewer' | 'candidate';
  content: string;
  timestamp: string;
  scores?: ScoreMap;
  strengths?: string[];
  weaknesses?: string[];
  isThinking?: boolean;
}

export type SessionStatus = 'idle' | 'connecting' | 'active' | 'evaluating' | 'complete';

// ── Store Interface ────────────────────────────────────────────────────────

interface InterviewStore {
  // State
  currentInterview: Interview | null;
  currentQuestion: Question | null;
  sessionStatus: SessionStatus;
  messages: Message[];
  liveScores: ScoreMap | null;
  elapsedSeconds: number;
  error: string | null;

  // Actions
  setInterview: (interview: Interview) => void;
  setCurrentQuestion: (question: Question) => void;
  addMessage: (message: Message) => void;
  updateLastMessage: (updates: Partial<Message>) => void;
  setLiveScores: (scores: ScoreMap) => void;
  setStatus: (status: SessionStatus) => void;
  setElapsedSeconds: (seconds: number) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

// ── Store Implementation ───────────────────────────────────────────────────

export const useInterviewStore = create<InterviewStore>((set) => ({
  currentInterview: null,
  currentQuestion: null,
  sessionStatus: 'idle',
  messages: [],
  liveScores: null,
  elapsedSeconds: 0,
  error: null,

  setInterview: (interview) => set({ currentInterview: interview }),

  setCurrentQuestion: (question) => set({ currentQuestion: question }),

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages.filter((m) => !m.isThinking), message],
    })),

  updateLastMessage: (updates) =>
    set((state) => {
      const messages = [...state.messages];
      if (messages.length > 0) {
        messages[messages.length - 1] = { ...messages[messages.length - 1], ...updates };
      }
      return { messages };
    }),

  setLiveScores: (scores) => set({ liveScores: scores }),

  setStatus: (status) => set({ sessionStatus: status }),

  setElapsedSeconds: (seconds) => set({ elapsedSeconds: seconds }),

  setError: (error) => set({ error }),

  reset: () =>
    set({
      currentInterview: null,
      currentQuestion: null,
      sessionStatus: 'idle',
      messages: [],
      liveScores: null,
      elapsedSeconds: 0,
      error: null,
    }),
}));
