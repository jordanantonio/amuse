'use client';
import { useSession } from '@/components/v1/session';

export default function HomePage() {
  const { me } = useSession();
  return (
    <section>
      <h1>Welcome, {me.user.full_name.split(' ')[0]}</h1>
      <p className="v1-lede">
        {me.mode === 'worker'
          ? 'Contracts that fit your tickets will appear here.'
          : 'Applicants and offers for your postings will appear here.'}
      </p>
    </section>
  );
}
