'use client';
import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { ArrowLeft, Lock, MapPinned } from 'lucide-react';
import { market } from '@/lib/market';
import type { PostingDetail } from '@/lib/market-types';
import { useSession } from '@/components/v1/session';
import { ContractFacts, EligibilityBox, OrgLine, Pay } from '@/components/v1/contract';
import { ApplySheet } from '@/components/v1/apply-sheet';
import { WhySheet } from '@/components/v1/why-sheet';
import { ApplicationStatusBlock } from '@/components/v1/applications';
import { AcceptOffer, EngagementActions } from '@/components/v1/accept';
import { ErrorNote, Skeleton, StatusChip } from '@/components/v1/ui';
import { CompanyBadge } from '@/components/v1/avatar';

export default function PostingPage() {
  const { id } = useParams<{ id: string }>();
  const { me } = useSession();
  const [data, setData] = useState<PostingDetail | null>(null);
  const [error, setError] = useState('');
  const [whyOpen, setWhyOpen] = useState(false);
  const [applyOpen, setApplyOpen] = useState(false);
  const load = useCallback(async () => {
    try {
      setData(await market<PostingDetail>(`/postings/${id}`));
      setError('');
    } catch (e) {
      setError((e as Error).message);
    }
  }, [id]);
  useEffect(() => {
    void load();
  }, [load]);
  if (error && !data) return <ErrorNote message={error} retry={() => void load()} />;
  if (!data) return <Skeleton lines={3} />;
  const p = data.posting;
  const mine = data.my_application;
  const canApply =
    !data.is_owner &&
    p.status === 'open' &&
    p.eligible &&
    ((me.mode === 'worker' && p.posting_type === 'individual') ||
      (me.mode === 'agency' && p.posting_type === 'agency')) &&
    (!mine || mine.status === 'withdrawn');
  return (
    <article className="posting-page">
      <Link href={data.is_owner ? '/work' : '/home'} className="back-link">
        <ArrowLeft size={18} aria-hidden="true" />
        {data.is_owner ? 'Back to Work' : 'Back to Home'}
      </Link>
      <header className="posting-head">
        <CompanyBadge name={p.org.name} industry={p.org.industry} size={56} />
        <div className="posting-head-main">
          <h1>{p.title}</h1>
          <div className="contract-card-head">
            <OrgLine card={p} />
          </div>
        </div>
        {p.status !== 'open' && (
          <StatusChip
            status="closed"
            label={p.status === 'filled' ? 'Filled' : p.status === 'draft' ? 'Draft' : 'Closed'}
          />
        )}
      </header>
      <ContractFacts card={p} />
      <Pay card={p} />
      <p className="site-address">
        {p.site_address ? (
          <>
            <MapPinned size={18} aria-hidden="true" />
            Site: {p.site_address}
          </>
        ) : (
          <>
            <Lock size={18} aria-hidden="true" />
            The site address is shared once you get an offer.
          </>
        )}
      </p>

      {!data.is_owner && <EligibilityBox items={p.match.items} reasons={p.reasons} />}
      {!data.is_owner && p.score_breakdown && p.score_breakdown.length > 0 && (
        <button className="text-button why-link" onClick={() => setWhyOpen(true)}>
          Why am I seeing this?
        </button>
      )}
      {whyOpen && (
        <WhySheet
          card={p}
          onClose={() => setWhyOpen(false)}
          onApply={
            canApply
              ? () => {
                  setWhyOpen(false);
                  setApplyOpen(true);
                }
              : undefined
          }
        />
      )}
      {applyOpen && (
        <ApplySheet
          postingId={p.id}
          onClose={() => setApplyOpen(false)}
          onApplied={() => void load()}
        />
      )}

      {data.description && (
        <section className="v1-section">
          <h2>About the work</h2>
          <p className="posting-description">{data.description}</p>
        </section>
      )}

      <section className="v1-section posting-action">
        {error && <ErrorNote message={error} />}
        {data.is_owner && (
          <Link className="button button-primary" href={`/work?tab=applicants&posting=${p.id}`}>
            Review {p.applicants || 0} {p.applicants === 1 ? 'applicant' : 'applicants'}
          </Link>
        )}
        {mine && mine.status !== 'withdrawn' && (
          <ApplicationStatusBlock
            application={mine}
            onChange={load}
            acceptSlot={<AcceptOffer application={mine} onAccepted={load} />}
          />
        )}
        {mine?.status === 'accepted' && mine.engagement?.status === 'active' && (
          <EngagementActions application={mine} onChange={load} />
        )}
        {canApply && (
          <button className="button button-primary" onClick={() => setApplyOpen(true)}>
            Apply
          </button>
        )}
        {!data.is_owner && !p.eligible && !mine && (
          <Link className="button button-outline" href="/profile">
            Add the missing certifications
          </Link>
        )}
      </section>
    </article>
  );
}
