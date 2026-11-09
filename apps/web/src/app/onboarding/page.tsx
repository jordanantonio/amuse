'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { HardHat, Building2, Users } from 'lucide-react';
import { market } from '@/lib/market';
import type { Me, Meta, Mode } from '@/lib/market-types';
import { RequireSession, useSession } from '@/components/v1/session';

const roles: { mode: Mode; title: string; detail: string; icon: typeof HardHat }[] = [
  {
    mode: 'worker',
    title: 'I’m looking for work',
    detail: 'Find contracts that fit your certifications and schedule.',
    icon: HardHat,
  },
  {
    mode: 'business',
    title: 'I’m hiring',
    detail: 'Post contracts and hire certified workers.',
    icon: Building2,
  },
  {
    mode: 'agency',
    title: 'I run a contracting company',
    detail: 'Offer your crew for larger jobs.',
    icon: Users,
  },
];

export default function OnboardingPage() {
  return (
    <RequireSession allowIncomplete fallback={<main className="v1-center" aria-busy="true" />}>
      <Onboarding />
    </RequireSession>
  );
}

function Onboarding() {
  const router = useRouter();
  const { me, refresh } = useSession();
  const [meta, setMeta] = useState<Meta | null>(null);
  const [step, setStep] = useState(me.mode ? 1 : 0);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const worker = me.mode === 'worker';
  const [form, setForm] = useState({
    full_name: me.user.full_name,
    headline: me.worker_profile?.headline || '',
    org_name: me.organization?.name || '',
    trades: me.worker_profile?.trades || [],
    industry: me.organization?.industry || '',
    city: me.worker_profile?.city || me.organization?.city || '',
    travel_radius_km: me.worker_profile?.travel_radius_km || 50,
  });
  useEffect(() => {
    if (me.onboarded) router.replace('/home');
    market<Meta>('/meta').then(setMeta, (e) => setError((e as Error).message));
  }, [me.onboarded, router]);

  const save = async (body: Record<string, unknown>, next: number | 'home') => {
    setBusy(true);
    setError('');
    try {
      await market<Me>('/onboarding', { method: 'PUT', body });
      await refresh();
      if (next === 'home') router.replace('/home');
      else setStep(next);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const set = (patch: Partial<typeof form>) => setForm((f) => ({ ...f, ...patch }));

  if (step === 0)
    return (
      <main className="onboarding">
        <h1>How will you use Shift?</h1>
        <p className="v1-lede">You can’t change this later on this account.</p>
        {error && (
          <p className="v1-inline-error" role="alert">
            {error}
          </p>
        )}
        <div className="role-choices">
          {roles.map((r) => (
            <button
              key={r.mode}
              className="role-choice"
              disabled={busy}
              onClick={() => void save({ role: r.mode }, 1)}
            >
              <r.icon size={28} aria-hidden="true" />
              <strong>{r.title}</strong>
              <span>{r.detail}</span>
            </button>
          ))}
        </div>
      </main>
    );

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (step === 1)
      void save(
        worker
          ? { full_name: form.full_name, headline: form.headline }
          : { full_name: form.full_name, org_name: form.org_name },
        2,
      );
    else if (step === 2)
      void save(worker ? { trades: form.trades } : { industry: form.industry || null }, 3);
    else
      void save(
        {
          city: form.city || null,
          ...(worker ? { travel_radius_km: form.travel_radius_km } : {}),
          finish: true,
        },
        'home',
      );
  };

  return (
    <main className="onboarding">
      <p className="step-count">Step {step} of 3</p>
      <form className="onboarding-form" onSubmit={submit}>
        {step === 1 && (
          <>
            <h1>{worker ? 'The basics' : 'About your company'}</h1>
            <label>
              Your name
              <input
                value={form.full_name}
                onChange={(e) => set({ full_name: e.target.value })}
                required
                maxLength={160}
              />
            </label>
            {worker ? (
              <label>
                Headline
                <input
                  value={form.headline}
                  onChange={(e) => set({ headline: e.target.value })}
                  placeholder="Journeyperson electrician, 9 yrs"
                  maxLength={160}
                />
                <small>One line that tells a hiring manager what you do.</small>
              </label>
            ) : (
              <label>
                Company name
                <input
                  value={form.org_name}
                  onChange={(e) => set({ org_name: e.target.value })}
                  required
                  maxLength={160}
                />
              </label>
            )}
          </>
        )}
        {step === 2 && worker && (
          <fieldset className="chip-field">
            <legend>
              <h1>Your trades</h1>
            </legend>
            <p className="v1-lede">Pick every trade you’d take a contract in.</p>
            <div className="chips">
              {meta?.trades.map((t) => {
                const on = form.trades.includes(t);
                return (
                  <label key={t} className={`chip ${on ? 'on' : ''}`}>
                    <input
                      type="checkbox"
                      checked={on}
                      onChange={() =>
                        set({
                          trades: on ? form.trades.filter((x) => x !== t) : [...form.trades, t],
                        })
                      }
                    />
                    {t}
                  </label>
                );
              })}
            </div>
          </fieldset>
        )}
        {step === 2 && !worker && (
          <>
            <h1>Your industry</h1>
            <label>
              Industry
              <select value={form.industry} onChange={(e) => set({ industry: e.target.value })}>
                <option value="">Choose an industry</option>
                {meta?.industries.map((i) => (
                  <option key={i}>{i}</option>
                ))}
              </select>
            </label>
          </>
        )}
        {step === 3 && (
          <>
            <h1>{worker ? 'Where you work' : 'Where you’re based'}</h1>
            <label>
              {worker ? 'Home city' : 'City'}
              <select value={form.city} onChange={(e) => set({ city: e.target.value })} required>
                <option value="">Choose a city</option>
                {meta?.cities.map((c) => (
                  <option key={c.name}>{c.name}</option>
                ))}
              </select>
            </label>
            {worker && (
              <label>
                How far you’ll travel: <strong>{form.travel_radius_km} km</strong>
                <input
                  type="range"
                  min={5}
                  max={300}
                  step={5}
                  value={form.travel_radius_km}
                  onChange={(e) => set({ travel_radius_km: Number(e.target.value) })}
                />
              </label>
            )}
          </>
        )}
        {error && (
          <p className="v1-inline-error" role="alert">
            {error}
          </p>
        )}
        <div className="onboarding-actions">
          <button className="button button-primary" disabled={busy}>
            {busy ? 'Saving…' : step === 3 ? 'Finish' : 'Continue'}
          </button>
          {step > 1 && (
            <button type="button" className="text-button" onClick={() => setStep(step - 1)}>
              Back
            </button>
          )}
          <button
            type="button"
            className="text-button skip"
            disabled={busy}
            onClick={() => void save({ finish: true }, 'home')}
          >
            Skip to Home
          </button>
        </div>
      </form>
    </main>
  );
}
