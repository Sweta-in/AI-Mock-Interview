/**
 * PrepAI — Socket.IO client for real-time interview communication.
 */

import { io, Socket } from 'socket.io-client';
import { useInterviewStore, type ScoreMap, type Message } from './store';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'http://localhost:8000';

let socket: Socket | null = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;

/**
 * Connect to the interview WebSocket and join the interview room.
 */
export function connectToInterview(interviewId: string, sessionToken: string): Socket {
  const store = useInterviewStore.getState();
  store.setStatus('connecting');

  // Disconnect existing socket if any
  if (socket?.connected) {
    socket.disconnect();
  }

  socket = io(`${WS_URL}/ws`, {
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionAttempts: MAX_RECONNECT_ATTEMPTS,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    timeout: 10000,
  });

  // ── Connection Events ─────────────────────────────────────────────────

  socket.on('connect', () => {
    console.log('[WS] Connected, joining interview...');
    reconnectAttempts = 0;

    socket?.emit('join_interview', {
      interview_id: interviewId,
      session_token: sessionToken,
    });
  });

  socket.on('disconnect', (reason: string) => {
    console.log(`[WS] Disconnected: ${reason}`);
    if (reason === 'io server disconnect') {
      // Server disconnected us — don't reconnect
      store.setStatus('idle');
    }
  });

  socket.on('connect_error', (error: Error) => {
    console.error('[WS] Connection error:', error.message);
    reconnectAttempts++;

    if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
      store.setError('Connection lost. Please refresh the page.');
      store.setStatus('idle');
    }
  });

  // ── Interview Events ──────────────────────────────────────────────────

  socket.on('question', (data: {
    question_id: string;
    question_text: string;
    question_num: number;
    total_questions: number;
    question_type: string;
  }) => {
    console.log('[WS] Received question:', data.question_num);
    const store = useInterviewStore.getState();

    store.setCurrentQuestion(data);
    store.setStatus('active');

    // Add interviewer message
    const message: Message = {
      id: data.question_id,
      role: 'interviewer',
      content: data.question_text,
      timestamp: new Date().toISOString(),
    };
    store.addMessage(message);
  });

  socket.on('evaluation_complete', (data: {
    question_id: string;
    scores: ScoreMap;
    strengths: string[];
    weaknesses: string[];
  }) => {
    console.log('[WS] Evaluation complete:', data.question_id);
    const store = useInterviewStore.getState();

    store.setLiveScores(data.scores);
    store.setStatus('active');

    // Update the candidate message with scores
    const messages = store.messages;
    const candidateMsg = [...messages].reverse().find(
      (m) => m.role === 'candidate'
    );
    if (candidateMsg) {
      store.updateLastMessage({
        scores: data.scores,
        strengths: data.strengths,
        weaknesses: data.weaknesses,
      });
    }

    // Add thinking indicator for next question
    const thinkingMessage: Message = {
      id: `thinking-${Date.now()}`,
      role: 'interviewer',
      content: '',
      timestamp: new Date().toISOString(),
      isThinking: true,
    };
    store.addMessage(thinkingMessage);
  });

  socket.on('interview_complete', (data: { report_id: string }) => {
    console.log('[WS] Interview complete:', data.report_id);
    const store = useInterviewStore.getState();
    store.setStatus('complete');
  });

  socket.on('error', (data: { code: string; message: string }) => {
    console.error('[WS] Server error:', data);
    const store = useInterviewStore.getState();
    store.setError(data.message);
  });

  return socket;
}

/**
 * Submit an answer to the current question.
 */
export function submitAnswer(
  interviewId: string,
  questionId: string,
  responseText: string,
  responseTimeSeconds: number,
): void {
  if (!socket?.connected) {
    console.error('[WS] Not connected');
    return;
  }

  const store = useInterviewStore.getState();
  store.setStatus('evaluating');

  // Add candidate message
  const message: Message = {
    id: `response-${Date.now()}`,
    role: 'candidate',
    content: responseText,
    timestamp: new Date().toISOString(),
  };
  store.addMessage(message);

  socket.emit('submit_answer', {
    interview_id: interviewId,
    question_id: questionId,
    response_text: responseText,
    response_time_seconds: responseTimeSeconds,
  });
}

/**
 * Disconnect the socket and clean up.
 */
export function disconnectSocket(): void {
  if (socket) {
    socket.disconnect();
    socket = null;
  }
  reconnectAttempts = 0;
}

/**
 * Get the current socket instance.
 */
export function getSocket(): Socket | null {
  return socket;
}
