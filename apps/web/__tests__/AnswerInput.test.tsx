import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { AnswerInput } from '../components/interview/AnswerInput';

describe('AnswerInput', () => {
  const mockSubmit = jest.fn();

  beforeEach(() => {
    mockSubmit.mockClear();
  });

  it('renders correctly when enabled', () => {
    render(<AnswerInput onSubmit={mockSubmit} disabled={false} isEvaluating={false} />);

    const textarea = screen.getByPlaceholderText(/type your answer/i);
    expect(textarea).toBeInTheDocument();
    expect(textarea).not.toBeDisabled();

    const submitBtn = screen.getByRole('button', { name: '' }); // Send icon button
    expect(submitBtn).toBeInTheDocument();
  });

  it('renders disabled state correctly', () => {
    render(<AnswerInput onSubmit={mockSubmit} disabled={true} isEvaluating={false} />);

    const textarea = screen.getByPlaceholderText(/waiting for question/i);
    expect(textarea).toBeDisabled();
  });

  it('shows evaluating state', () => {
    render(<AnswerInput onSubmit={mockSubmit} disabled={true} isEvaluating={true} />);

    expect(screen.getByText(/evaluating/i)).toBeInTheDocument();
  });

  it('fires onSubmit callback with text', () => {
    render(<AnswerInput onSubmit={mockSubmit} disabled={false} isEvaluating={false} />);

    const textarea = screen.getByPlaceholderText(/type your answer/i);
    fireEvent.change(textarea, { target: { value: 'My answer about distributed systems' } });

    const submitBtn = document.getElementById('submit-answer-btn');
    if (submitBtn) fireEvent.click(submitBtn);

    expect(mockSubmit).toHaveBeenCalledWith('My answer about distributed systems');
  });

  it('does not submit empty text', () => {
    render(<AnswerInput onSubmit={mockSubmit} disabled={false} isEvaluating={false} />);

    const submitBtn = document.getElementById('submit-answer-btn');
    if (submitBtn) fireEvent.click(submitBtn);

    expect(mockSubmit).not.toHaveBeenCalled();
  });

  it('handles Ctrl+Enter keyboard shortcut', () => {
    render(<AnswerInput onSubmit={mockSubmit} disabled={false} isEvaluating={false} />);

    const textarea = screen.getByPlaceholderText(/type your answer/i);
    fireEvent.change(textarea, { target: { value: 'Keyboard shortcut test' } });
    fireEvent.keyDown(textarea, { key: 'Enter', ctrlKey: true });

    expect(mockSubmit).toHaveBeenCalledWith('Keyboard shortcut test');
  });

  it('shows word count', () => {
    render(<AnswerInput onSubmit={mockSubmit} disabled={false} isEvaluating={false} />);

    const textarea = screen.getByPlaceholderText(/type your answer/i);
    fireEvent.change(textarea, { target: { value: 'one two three four five' } });

    expect(screen.getByText(/5 words/)).toBeInTheDocument();
  });

  it('submit button is disabled when evaluating', () => {
    render(<AnswerInput onSubmit={mockSubmit} disabled={true} isEvaluating={true} />);

    const submitBtn = document.getElementById('submit-answer-btn');
    expect(submitBtn).toBeDisabled();
  });
});
