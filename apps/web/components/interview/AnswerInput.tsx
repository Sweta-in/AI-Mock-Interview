'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { Send, Loader2 } from 'lucide-react';

interface AnswerInputProps {
  onSubmit: (text: string) => void;
  disabled: boolean;
  isEvaluating: boolean;
}

export function AnswerInput({ onSubmit, disabled, isEvaluating }: AnswerInputProps) {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const wordCount = text.trim().split(/\s+/).filter(Boolean).length;
  const charCount = text.length;
  const maxChars = 5000;

  // Auto-focus textarea when enabled
  useEffect(() => {
    if (!disabled && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [disabled]);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [text]);

  const handleSubmit = useCallback(() => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setText('');
  }, [text, disabled, onSubmit]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      // Cmd/Ctrl + Enter to submit
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  return (
    <div className={`relative ${disabled && !isEvaluating ? 'opacity-50' : ''}`}>
      {/* Word count hint */}
      <div className="flex items-center justify-between mb-2 px-1">
        <span className="text-xs text-gray-400">
          {isEvaluating ? (
            <span className="flex items-center gap-1.5 text-primary-500">
              <Loader2 className="w-3 h-3 animate-spin" />
              Evaluating your answer...
            </span>
          ) : disabled ? (
            'Waiting for question...'
          ) : (
            'Aim for 100–200 words for depth'
          )}
        </span>
        <span className={`text-xs ${wordCount > 200 ? 'text-amber-500' : 'text-gray-400'}`}>
          {wordCount} words · {charCount}/{maxChars}
        </span>
      </div>

      <div className="flex gap-2 items-end">
        <textarea
          ref={textareaRef}
          id="answer-input"
          value={text}
          onChange={(e) => {
            if (e.target.value.length <= maxChars) {
              setText(e.target.value);
            }
          }}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={
            disabled
              ? 'Waiting for question...'
              : 'Type your answer here... (Ctrl+Enter to submit)'
          }
          rows={3}
          className="flex-1 resize-none rounded-xl border-2 border-gray-200 focus:border-primary-400 px-4 py-3 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition-colors disabled:bg-gray-50 disabled:cursor-not-allowed"
        />

        <button
          id="submit-answer-btn"
          onClick={handleSubmit}
          disabled={disabled || text.trim().length === 0}
          className="flex-shrink-0 w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 text-white flex items-center justify-center hover:shadow-lg disabled:opacity-40 disabled:cursor-not-allowed transition-all hover:-translate-y-0.5 active:translate-y-0"
        >
          {isEvaluating ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
        </button>
      </div>

      {/* Keyboard shortcut hint */}
      {!disabled && (
        <div className="mt-1.5 px-1">
          <kbd className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 font-mono">
            Ctrl+Enter
          </kbd>
          <span className="text-[10px] text-gray-400 ml-1">to submit</span>
        </div>
      )}
    </div>
  );
}
