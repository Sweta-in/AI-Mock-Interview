'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getAccessToken } from '@/lib/supabase';
import { api } from '@/lib/api';
import { useInterviewStore } from '@/lib/store';
import { connectToInterview, submitAnswer, disconnectSocket } from '@/lib/socket';
import { ChatBubble } from '@/components/interview/ChatBubble';
import { AnswerInput } from '@/components/interview/AnswerInput';
import { FeedbackCard } from '@/components/interview/FeedbackCard';
import { ScoreRadar } from '@/components/interview/ScoreRadar';
import { InterviewTimer } from '@/components/interview/InterviewTimer';
import { Brain, ArrowLeft, AlertCircle, CheckCircle2 } from 'lucide-react';

export default function LiveInterviewPage() {
  const params = useParams();
  const router = useRouter();
  const interviewId = params.id as string;
  const chatEndRef = useRef<HTMLDivElement>(null);
  const [answerStartTime, setAnswerStartTime] = useState<number>(Date.now());
  const [showFeedback, setShowFeedback] = useState(false);

  const {
    currentInterview,
    currentQuestion,
    sessionStatus,
    messages,
    liveScores,
    error,
    setInterview,
    setStatus,
    setError,
    reset,
  } = useInterviewStore();

  // Initialize interview
  useEffect(() => {
    initializeInterview();
    return () => {
      disconnectSocket();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [interviewId]);

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Reset answer timer when new question arrives
  useEffect(() => {
    if (currentQuestion) {
      setAnswerStartTime(Date.now());
      setShowFeedback(false);
    }
  }, [currentQuestion?.question_id]);

  // Show feedback when evaluation completes
  useEffect(() => {
    if (sessionStatus === 'active' && liveScores) {
      setShowFeedback(true);
    }
  }, [liveScores, sessionStatus]);

  const initializeInterview = async () => {
    try {
      const token = await getAccessToken();
      if (!token) { router.push('/auth/login'); return; }

      // Start the interview
      const startData = await api.startInterview(token, interviewId);

      setInterview({
        id: interviewId,
        session_token: startData.session_token,
        role_slug: '',
        role_name: '',
        status: 'active',
        difficulty: '',
        interview_type: '',
        started_at: new Date().toISOString(),
        completed_at: null,
        duration_seconds: null,
        overall_score: null,
        technical_score: null,
        behavioral_score: null,
        communication_score: null,
        question_count: 0,
      });

      // Connect WebSocket
      connectToInterview(interviewId, startData.session_token);
    } catch (err) {
      console.error('Failed to initialize interview:', err);
      setError('Failed to start interview. Please try again.');
      setStatus('idle');
    }
  };

  const handleSubmitAnswer = useCallback((text: string) => {
    if (!currentQuestion || sessionStatus !== 'active') return;

    const responseTime = (Date.now() - answerStartTime) / 1000;
    submitAnswer(interviewId, currentQuestion.question_id, text, responseTime);
    setShowFeedback(false);
  }, [currentQuestion, sessionStatus, answerStartTime, interviewId]);

  const handleAbandon = async () => {
    if (!confirm('Are you sure you want to end this interview?')) return;
    try {
      const token = await getAccessToken();
      if (token) await api.abandonInterview(token, interviewId);
    } catch { /* ignore */ }
    disconnectSocket();
    reset();
    router.push('/dashboard');
  };

  // ── Interview Complete State ────────────────────────────────────────
  if (sessionStatus === 'complete') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-100 px-4">
        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-10 max-w-md text-center animate-slide-up">
          <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-5">
            <CheckCircle2 className="w-8 h-8 text-green-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Interview Complete! 🎉</h1>
          <p className="text-gray-600 mb-6">
            Your detailed report is being generated. View your feedback and scores on the report page.
          </p>
          <div className="flex flex-col gap-3">
            <button
              onClick={() => router.push(`/interview/${interviewId}`)}
              className="btn-primary py-3 w-full"
            >
              View Report
            </button>
            <button
              onClick={() => router.push('/dashboard')}
              className="py-3 w-full rounded-xl border-2 border-gray-200 text-gray-700 font-medium hover:bg-gray-50 transition-colors"
            >
              Back to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Main Interview UI ──────────────────────────────────────────────
  return (
    <div className="h-screen flex flex-col bg-surface-100">
      {/* Header */}
      <header className="flex-shrink-0 glass border-b border-white/20 px-4 h-14 flex items-center justify-between z-40">
        <div className="flex items-center gap-3">
          <button onClick={handleAbandon} className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors" title="End interview">
            <ArrowLeft className="w-4 h-4 text-gray-500" />
          </button>
          <Brain className="w-5 h-5 text-primary-500" />
          <span className="font-semibold text-gray-800 text-sm">Mock Interview</span>
        </div>
        <InterviewTimer
          questionNum={currentQuestion?.question_num || 0}
          totalQuestions={currentQuestion?.total_questions || 10}
        />
      </header>

      {/* Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Chat Panel */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-4 chat-scroll">
            {error && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm mb-4">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                {error}
              </div>
            )}

            {messages.length === 0 && sessionStatus === 'connecting' && (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <div className="w-12 h-12 border-3 border-primary-200 border-t-primary-600 rounded-full animate-spin mx-auto mb-4" />
                  <p className="text-gray-500 font-medium">Connecting to your interview...</p>
                  <p className="text-gray-400 text-sm mt-1">Your AI interviewer is preparing</p>
                </div>
              </div>
            )}

            <div className="max-w-3xl mx-auto space-y-4">
              {messages.map((msg) => (
                <ChatBubble key={msg.id} message={msg} />
              ))}
              <div ref={chatEndRef} />
            </div>
          </div>

          {/* Input */}
          <div className="flex-shrink-0 border-t border-gray-200 bg-white px-4 py-3">
            <div className="max-w-3xl mx-auto">
              <AnswerInput
                onSubmit={handleSubmitAnswer}
                disabled={sessionStatus !== 'active'}
                isEvaluating={sessionStatus === 'evaluating'}
              />
            </div>
          </div>
        </div>

        {/* Side Panel — Feedback & Radar */}
        <div className="hidden lg:flex flex-col w-80 border-l border-gray-200 bg-white overflow-y-auto">
          <div className="p-4 border-b border-gray-100">
            <h3 className="font-semibold text-gray-800 text-sm">Performance</h3>
          </div>

          {/* Radar Chart */}
          <div className="p-4">
            <ScoreRadar scores={liveScores} />
          </div>

          {/* Latest Feedback */}
          {showFeedback && messages.length > 0 && (
            <div className="p-4 border-t border-gray-100">
              <FeedbackCard
                scores={messages[messages.length - 1]?.scores || null}
                strengths={messages[messages.length - 1]?.strengths || []}
                weaknesses={messages[messages.length - 1]?.weaknesses || []}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
