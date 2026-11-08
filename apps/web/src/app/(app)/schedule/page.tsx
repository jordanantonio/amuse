'use client';
import { EmptyState } from '@/components/v1/ui';

export default function SchedulePage() {
  return (
    <section>
      <h1 className="page-title">Schedule</h1>
      <EmptyState title="Nothing booked yet">
        Contracts you accept appear here and block those dates.
      </EmptyState>
    </section>
  );
}
