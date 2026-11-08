import type { Metadata } from 'next';
import { AdaptiveWorkspace } from '@/components/adaptive-workspace';
import { AuthGate } from '@/components/auth-gate';

export const metadata: Metadata = { title: 'Legacy planner (unlinked) — Shift' };

/**
 * CREW-6: the original text-wall planner (SHIFT Adaptive) is no longer linked from the
 * product; /crew replaces it. Kept here, unlinked, so its recovery flows and tests survive.
 */
export default function LegacyPlannerPage() {
  return (
    <AuthGate>
      <AdaptiveWorkspace />
    </AuthGate>
  );
}
