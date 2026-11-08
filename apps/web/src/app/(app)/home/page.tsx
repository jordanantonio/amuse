'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { TriangleAlert } from 'lucide-react';
import { market } from '@/lib/market';
import type { Profile } from '@/lib/market-types';
import { day } from '@/lib/format';
import { useSession } from '@/components/v1/session';

export default function HomePage() {
  const { me } = useSession();
  const [profile, setProfile] = useState<Profile | null>(null);
  useEffect(() => {
    if (me.mode === 'worker') market<Profile>('/me/profile').then(setProfile, () => undefined);
  }, [me.mode]);
  const expiring = profile?.credentials.filter((c) => c.expiring_soon) || [];
  return (
    <section>
      <h1 className="page-title">Good to see you, {me.user.full_name.split(' ')[0]}</h1>
      {expiring.map((c) => (
        <Link key={c.id} href="/profile" className="today-item warn">
          <TriangleAlert size={20} aria-hidden="true" />
          <span>
            <strong>
              {c.name} expires {day(c.expires_on!)}
            </strong>
            Renew it to keep qualifying for contracts that need it.
          </span>
        </Link>
      ))}
      <p className="v1-lede">
        {me.mode === 'worker'
          ? 'Contracts that fit your tickets will appear here.'
          : 'Applicants and offers for your postings will appear here.'}
      </p>
    </section>
  );
}
