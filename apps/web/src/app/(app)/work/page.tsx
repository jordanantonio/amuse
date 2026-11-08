'use client';
import { EmptyState } from '@/components/v1/ui';
import { useSession } from '@/components/v1/session';

export default function WorkPage() {
  const { me } = useSession();
  return (
    <section>
      <h1 className="page-title">Work</h1>
      <EmptyState title={me.mode === 'worker' ? 'No applications yet' : 'No postings yet'}>
        {me.mode === 'worker'
          ? 'Contracts that fit you are on Home.'
          : 'Post a contract to start receiving applicants.'}
      </EmptyState>
    </section>
  );
}
