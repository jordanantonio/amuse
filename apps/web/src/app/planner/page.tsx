import type { Metadata } from 'next';
import { AdaptiveWorkspace } from '@/components/adaptive-workspace';
import { AuthGate } from '@/components/auth-gate';

export const metadata: Metadata = { title: 'Crew planner — Shift' };

/** The CP-SAT crew planner (SHIFT Adaptive), kept as a business-side tool. */
export default function PlannerPage() {
  return (
    <AuthGate>
      <AdaptiveWorkspace />
    </AuthGate>
  );
}
