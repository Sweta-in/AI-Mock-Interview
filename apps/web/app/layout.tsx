import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'PrepAI — AI-Powered Mock Interview Coach',
  description: 'Practice interviews with an AI interviewer. Get specific, rubric-based feedback on every answer. Track your progress over time.',
  keywords: ['mock interview', 'AI interview', 'interview practice', 'career prep', 'interview coach'],
  openGraph: {
    title: 'PrepAI — AI-Powered Mock Interview Coach',
    description: 'Practice interviews with an AI interviewer. Get specific feedback and track progress.',
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-surface-100">
        {children}
      </body>
    </html>
  );
}
