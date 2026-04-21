import '@testing-library/jest-dom';

// Mock recharts to avoid SSR issues in tests
jest.mock('recharts', () => ({
  RadarChart: ({ children }: { children: React.ReactNode }) => children,
  PolarGrid: () => null,
  PolarAngleAxis: () => null,
  PolarRadiusAxis: () => null,
  Radar: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => children,
  Tooltip: () => null,
  LineChart: ({ children }: { children: React.ReactNode }) => children,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Legend: () => null,
}));
