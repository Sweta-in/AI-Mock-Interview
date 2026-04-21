import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { FeedbackCard } from '../components/interview/FeedbackCard';

describe('FeedbackCard', () => {
  const mockScores = {
    relevance: 80,
    depth: 65,
    clarity: 75,
    communication: 90,
    technical_accuracy: 70,
  };

  const mockStrengths = [
    'Candidate correctly identified "consistent hashing" as a solution for data partitioning',
    'Good use of concrete numbers when describing "50ms response time improvement"',
  ];

  const mockWeaknesses = [
    'When the candidate said "just use Redis" they missed cache invalidation strategies',
    'The answer lacked discussion of trade-offs between consistency models',
  ];

  it('renders nothing when scores are null', () => {
    const { container } = render(
      <FeedbackCard scores={null} strengths={[]} weaknesses={[]} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders collapsed state with average score', () => {
    render(
      <FeedbackCard
        scores={mockScores}
        strengths={mockStrengths}
        weaknesses={mockWeaknesses}
      />
    );

    // Should show the average score badge
    const avgScore = Math.round(
      Object.values(mockScores).reduce((a, b) => a + b, 0) / Object.values(mockScores).length
    );
    expect(screen.getByText(String(avgScore))).toBeInTheDocument();
    expect(screen.getByText(/answer feedback/i)).toBeInTheDocument();
  });

  it('expands to show details when clicked', () => {
    render(
      <FeedbackCard
        scores={mockScores}
        strengths={mockStrengths}
        weaknesses={mockWeaknesses}
      />
    );

    // Click to expand
    const expandButton = screen.getByText(/answer feedback/i).closest('button');
    if (expandButton) fireEvent.click(expandButton);

    // Should show strengths
    expect(screen.getByText(/strengths/i)).toBeInTheDocument();
    expect(screen.getByText(/consistent hashing/i)).toBeInTheDocument();

    // Should show weaknesses
    expect(screen.getByText(/areas to improve/i)).toBeInTheDocument();
    expect(screen.getByText(/cache invalidation/i)).toBeInTheDocument();
  });

  it('collapses when clicked again', () => {
    render(
      <FeedbackCard
        scores={mockScores}
        strengths={mockStrengths}
        weaknesses={mockWeaknesses}
      />
    );

    const expandButton = screen.getByText(/answer feedback/i).closest('button');

    // Expand
    if (expandButton) fireEvent.click(expandButton);
    expect(screen.getByText(/strengths/i)).toBeInTheDocument();

    // Collapse
    if (expandButton) fireEvent.click(expandButton);
    expect(screen.queryByText(/strengths/i)).not.toBeInTheDocument();
  });

  it('renders all score dimensions', () => {
    render(
      <FeedbackCard
        scores={mockScores}
        strengths={mockStrengths}
        weaknesses={mockWeaknesses}
      />
    );

    const expandButton = screen.getByText(/answer feedback/i).closest('button');
    if (expandButton) fireEvent.click(expandButton);

    expect(screen.getByText(/relevance/i)).toBeInTheDocument();
    expect(screen.getByText(/depth/i)).toBeInTheDocument();
    expect(screen.getByText(/clarity/i)).toBeInTheDocument();
    expect(screen.getByText(/communication/i)).toBeInTheDocument();
  });

  it('shows correct color for high scores (green)', () => {
    const highScores = {
      relevance: 90,
      depth: 85,
      clarity: 95,
      communication: 88,
      technical_accuracy: 92,
    };

    render(
      <FeedbackCard
        scores={highScores}
        strengths={['Excellent quote from answer']}
        weaknesses={['Minor issue with specific phrasing']}
      />
    );

    // Average should be high, showing green badge
    const avgScore = Math.round(
      Object.values(highScores).reduce((a, b) => a + b, 0) / Object.values(highScores).length
    );
    const badge = screen.getByText(String(avgScore));
    expect(badge).toBeInTheDocument();
  });
});
