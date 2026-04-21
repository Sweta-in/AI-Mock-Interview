'use client';

import { useRouter } from 'next/navigation';
import { ArrowRight, Brain, BarChart3, MessageSquare, Sparkles, Shield, Zap } from 'lucide-react';

export default function LandingPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-surface-100">
      {/* ── Navigation ────────────────────────────────────────────────── */}
      <nav className="fixed top-0 w-full z-50 glass border-b border-white/20">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold gradient-text">PrepAI</span>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push('/auth/login')}
              className="px-4 py-2 text-sm font-medium text-primary-600 hover:text-primary-700 transition-colors"
            >
              Log In
            </button>
            <button
              onClick={() => router.push('/auth/signup')}
              className="btn-primary text-sm px-5 py-2.5"
            >
              Get Started Free
            </button>
          </div>
        </div>
      </nav>

      {/* ── Hero Section ──────────────────────────────────────────────── */}
      <section className="relative pt-32 pb-20 px-6 overflow-hidden">
        {/* Background decoration */}
        <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[800px] h-[800px] bg-primary-200/30 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute top-40 right-10 w-64 h-64 bg-purple-200/20 rounded-full blur-2xl pointer-events-none" />

        <div className="relative max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary-50 border border-primary-200 text-primary-700 text-sm font-medium mb-6 animate-fade-in">
            <Sparkles className="w-4 h-4" />
            AI-Powered Interview Coaching
          </div>

          <h1 className="text-5xl md:text-6xl lg:text-7xl font-extrabold leading-tight mb-6 animate-slide-up">
            Ace Your Next Interview with{' '}
            <span className="gradient-text">AI Precision</span>
          </h1>

          <p className="text-lg md:text-xl text-gray-600 max-w-2xl mx-auto mb-10 leading-relaxed animate-slide-up" style={{ animationDelay: '0.1s' }}>
            Practice with realistic AI interviewers tailored to your target role.
            Get specific, phrase-level feedback on every answer — not generic advice.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center animate-slide-up" style={{ animationDelay: '0.2s' }}>
            <button
              onClick={() => router.push('/auth/signup')}
              className="btn-primary text-lg px-8 py-4 flex items-center justify-center gap-2"
            >
              Start Practicing Free
              <ArrowRight className="w-5 h-5" />
            </button>
            <button
              onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })}
              className="px-8 py-4 rounded-xl border-2 border-primary-200 text-primary-600 font-semibold hover:bg-primary-50 transition-all text-lg"
            >
              See How It Works
            </button>
          </div>

          {/* Stats */}
          <div className="flex flex-wrap justify-center gap-8 mt-16 animate-fade-in" style={{ animationDelay: '0.4s' }}>
            {[
              { value: '5', label: 'Role Specializations' },
              { value: '10', label: 'Questions Per Session' },
              { value: '5D', label: 'Scoring Dimensions' },
              { value: 'Free', label: 'To Get Started' },
            ].map((stat) => (
              <div key={stat.label} className="text-center">
                <div className="text-3xl font-bold gradient-text">{stat.value}</div>
                <div className="text-sm text-gray-500 mt-1">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features Section ──────────────────────────────────────────── */}
      <section id="features" className="py-24 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Why PrepAI is <span className="gradient-text">Different</span>
            </h2>
            <p className="text-gray-600 text-lg max-w-2xl mx-auto">
              Unlike generic chatbots, PrepAI uses expert interviewer personas with
              role-specific evaluation rubrics.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: <MessageSquare className="w-6 h-6" />,
                title: 'Realistic Conversations',
                description: 'AI interviewers with named personas, industry experience, and authentic questioning styles. They probe vague answers and push on excellent ones.',
                color: 'from-blue-500 to-indigo-600',
              },
              {
                icon: <BarChart3 className="w-6 h-6" />,
                title: 'Phrase-Level Feedback',
                description: 'Every strength and weakness cites specific phrases from YOUR answer. No generic "good communication" — only actionable, specific insights.',
                color: 'from-emerald-500 to-teal-600',
              },
              {
                icon: <Zap className="w-6 h-6" />,
                title: 'Adaptive Difficulty',
                description: 'Questions calibrate in real-time based on your performance. Struggling? The AI adjusts. Excelling? It pushes you to staff-level territory.',
                color: 'from-amber-500 to-orange-600',
              },
            ].map((feature) => (
              <div
                key={feature.title}
                className="p-8 rounded-2xl bg-white border border-gray-100 card-hover"
              >
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${feature.color} flex items-center justify-center text-white mb-5`}>
                  {feature.icon}
                </div>
                <h3 className="text-xl font-semibold mb-3">{feature.title}</h3>
                <p className="text-gray-600 leading-relaxed">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Roles Section ─────────────────────────────────────────────── */}
      <section className="py-24 px-6 bg-white/50">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              Practice for <span className="gradient-text">Your Role</span>
            </h2>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              { title: 'Backend Engineer', icon: '⚙️', topics: 'System Design, APIs, Databases, Distributed Systems' },
              { title: 'Frontend Engineer', icon: '🎨', topics: 'React, Performance, Accessibility, State Management' },
              { title: 'Product Manager', icon: '📊', topics: 'Product Strategy, Metrics, Prioritization, User Research' },
              { title: 'Data Scientist', icon: '🧪', topics: 'ML Pipelines, Statistics, Experimentation, SQL' },
              { title: 'Engineering Manager', icon: '👥', topics: 'Team Leadership, Technical Strategy, Hiring, Performance' },
              { title: 'More Coming Soon', icon: '🚀', topics: 'DevOps, Design, Marketing, Sales, and more...' },
            ].map((role) => (
              <div
                key={role.title}
                className="p-6 rounded-xl border border-gray-200 bg-white card-hover cursor-pointer"
                onClick={() => router.push('/auth/signup')}
              >
                <div className="text-3xl mb-3">{role.icon}</div>
                <h3 className="text-lg font-semibold mb-2">{role.title}</h3>
                <p className="text-sm text-gray-500">{role.topics}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA Section ───────────────────────────────────────────────── */}
      <section className="py-24 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <div className="p-12 rounded-3xl bg-gradient-to-br from-primary-600 to-primary-800 text-white relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/2 blur-2xl" />
            <div className="relative">
              <Shield className="w-12 h-12 mx-auto mb-6 opacity-90" />
              <h2 className="text-3xl md:text-4xl font-bold mb-4">
                Start Your First Interview
              </h2>
              <p className="text-primary-100 text-lg mb-8 max-w-lg mx-auto">
                3 free interviews per month. No credit card required.
                Get real feedback in under 15 minutes.
              </p>
              <button
                onClick={() => router.push('/auth/signup')}
                className="px-8 py-4 rounded-xl bg-white text-primary-700 font-bold text-lg hover:bg-primary-50 transition-all hover:shadow-xl"
              >
                Create Free Account
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────────────────────── */}
      <footer className="py-12 px-6 border-t border-gray-200">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-primary-500" />
            <span className="font-semibold text-gray-700">PrepAI</span>
          </div>
          <p className="text-sm text-gray-500">
            © {new Date().getFullYear()} PrepAI. Open source under MIT License.
          </p>
        </div>
      </footer>
    </div>
  );
}
