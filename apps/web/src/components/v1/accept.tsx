'use client';
import type { ApplicationView } from '@/lib/market-types';

/** Accepting an offer (FLOW-3/4, CAL-1..3) arrives in phase 4. */
export function AcceptOffer(_: { application: ApplicationView; onAccepted: () => Promise<void> }) {
  return null;
}

export function EngagementActions(_: {
  application: ApplicationView;
  onChange: () => Promise<void>;
}) {
  return null;
}
