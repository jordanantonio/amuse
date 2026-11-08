'use client';
import { useCallback, useEffect, useState } from 'react';
import { MapPin, Pencil, Plus, BadgeCheck, Globe } from 'lucide-react';
import { market } from '@/lib/market';
import type { Meta, OrgProfile, Profile, WorkHistory } from '@/lib/market-types';
import { day, dollars, initials } from '@/lib/format';
import { useSession } from '@/components/v1/session';
import { CredentialWallet } from '@/components/v1/wallet';
import { EmptyState, ErrorNote, Modal, Skeleton, StatusChip } from '@/components/v1/ui';
import { CompanyBadge, PersonAvatar } from '@/components/v1/avatar';

export default function ProfilePage() {
  const { me } = useSession();
  return me.mode === 'worker' ? <WorkerProfilePage /> : <CompanyProfilePage />;
}

function useMeta() {
  const [meta, setMeta] = useState<Meta | null>(null);
  useEffect(() => {
    market<Meta>('/meta').then(setMeta, () => undefined);
  }, []);
  return meta;
}

function WorkerProfilePage() {
  const { refresh: refreshSession } = useSession();
  const [data, setData] = useState<Profile | null>(null);
  const [error, setError] = useState('');
  const [editing, setEditing] = useState(false);
  const [entry, setEntry] = useState<WorkHistory | 'new' | null>(null);
  const meta = useMeta();
  const load = useCallback(async () => {
    try {
      setData(await market<Profile>('/me/profile'));
      setError('');
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);
  useEffect(() => {
    void load();
  }, [load]);
  if (error) return <ErrorNote message={error} retry={() => void load()} />;
  if (!data) return <Skeleton lines={4} />;
  const { profile, user, completeness } = data;
  const unlockType = completeness.next_step?.credential_type_id;
  return (
    <>
      <section className="profile-hero">
        <PersonAvatar id={user.id} name={user.full_name} size={88} ring />
        <div className="profile-hero-text">
          <h1>{user.full_name}</h1>
          <p className="profile-headline">
            {profile.headline || 'Add a headline so businesses know what you do'}
          </p>
          <ul className="contract-facts">
            <li>
              <MapPin size={16} aria-hidden="true" />
              {profile.city
                ? `${profile.city}, travels up to ${profile.travel_radius_km} km`
                : 'Home city not set'}
            </li>
            {profile.rate_min_cents != null && (
              <li>
                {dollars(profile.rate_min_cents)}
                {profile.rate_max_cents ? `–${dollars(profile.rate_max_cents)}` : '+'} per hour
              </li>
            )}
          </ul>
          {!!profile.trades.length && (
            <ul className="tag-list" aria-label="Trades">
              {profile.trades.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          )}
          {profile.bio && <p className="profile-bio">{profile.bio}</p>}
        </div>
        <button className="button button-outline" onClick={() => setEditing(true)}>
          <Pencil size={18} aria-hidden="true" />
          Edit profile
        </button>
      </section>

      <section className="completeness" aria-label="Profile completeness">
        <div className="completeness-top">
          <strong>Profile {completeness.percent}% complete</strong>
          {completeness.next_step && <span>Next: {completeness.next_step.label}</span>}
        </div>
        <div
          className="meter"
          role="progressbar"
          aria-valuenow={completeness.percent}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Profile completeness"
        >
          <span style={{ width: `${completeness.percent}%` }} />
        </div>
      </section>

      <CredentialWallet
        credentials={data.credentials}
        scope="me"
        highlightType={unlockType}
        onChange={async () => {
          await load();
        }}
      />

      <section className="v1-section" aria-labelledby="history-title">
        <div className="v1-section-head">
          <h2 id="history-title">Work history</h2>
          <button className="button button-outline" onClick={() => setEntry('new')}>
            <Plus size={18} aria-hidden="true" />
            Add a job
          </button>
        </div>
        {data.history.length ? (
          <ol className="history-list">
            {data.history.map((h) => (
              <li key={h.id}>
                <div>
                  <strong>
                    {h.role}, {h.company}
                  </strong>
                  <p className="wallet-meta">
                    {day(h.start_date, true)} – {h.end_date ? day(h.end_date, true) : 'present'}
                    {h.city ? ` · ${h.city}` : ''}
                  </p>
                  {h.description && <p>{h.description}</p>}
                  {h.engagement_id && (
                    <StatusChip status="verified" label="Completed on Shift" icon={BadgeCheck} />
                  )}
                </div>
                {!h.engagement_id && (
                  <button
                    className="icon-button tap"
                    aria-label={`Edit ${h.role} at ${h.company}`}
                    onClick={() => setEntry(h)}
                  >
                    <Pencil size={18} />
                  </button>
                )}
              </li>
            ))}
          </ol>
        ) : (
          <EmptyState title="No past jobs yet">
            Add two or three recent jobs. Contracts you finish on Shift are added for you.
          </EmptyState>
        )}
      </section>

      {editing && meta && (
        <ProfileDialog
          data={data}
          meta={meta}
          onClose={() => setEditing(false)}
          onSaved={async () => {
            setEditing(false);
            await Promise.all([load(), refreshSession()]);
          }}
        />
      )}
      {entry && (
        <HistoryDialog
          entry={entry === 'new' ? null : entry}
          onClose={() => setEntry(null)}
          onSaved={async () => {
            setEntry(null);
            await load();
          }}
        />
      )}
    </>
  );
}

function ProfileDialog({
  data,
  meta,
  onClose,
  onSaved,
}: {
  data: Profile;
  meta: Meta;
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const p = data.profile;
  const [form, setForm] = useState({
    full_name: data.user.full_name,
    headline: p.headline,
    trades: p.trades,
    city: p.city,
    travel_radius_km: p.travel_radius_km,
    rate_min: p.rate_min_cents != null ? String(p.rate_min_cents / 100) : '',
    rate_max: p.rate_max_cents != null ? String(p.rate_max_cents / 100) : '',
    bio: p.bio,
    linkedin_url: p.linkedin_url || '',
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const set = (patch: Partial<typeof form>) => setForm((f) => ({ ...f, ...patch }));
  return (
    <Modal title="Edit profile" onClose={onClose} busy={busy}>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError('');
          try {
            await market('/me/profile', {
              method: 'PUT',
              body: {
                full_name: form.full_name,
                headline: form.headline,
                trades: form.trades,
                city: form.city || null,
                travel_radius_km: form.travel_radius_km,
                rate_min_cents: form.rate_min ? Math.round(Number(form.rate_min) * 100) : null,
                rate_max_cents: form.rate_max ? Math.round(Number(form.rate_max) * 100) : null,
                bio: form.bio,
                linkedin_url: form.linkedin_url,
              },
            });
            await onSaved();
          } catch (err) {
            setError((err as Error).message);
            setBusy(false);
          }
        }}
      >
        <div className="editor-fields">
          <label>
            Name
            <input
              value={form.full_name}
              onChange={(e) => set({ full_name: e.target.value })}
              required
              maxLength={160}
            />
          </label>
          <label>
            Headline
            <input
              value={form.headline}
              onChange={(e) => set({ headline: e.target.value })}
              maxLength={160}
            />
          </label>
          <fieldset className="chip-field">
            <legend>Trades</legend>
            <div className="chips">
              {meta.trades.map((t) => {
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
          <div className="field-row">
            <label>
              Home city
              <select value={form.city} onChange={(e) => set({ city: e.target.value })}>
                <option value="">Choose a city</option>
                {meta.cities.map((c) => (
                  <option key={c.name}>{c.name}</option>
                ))}
              </select>
            </label>
            <label>
              Travel radius (km)
              <input
                type="number"
                min={5}
                max={1000}
                value={form.travel_radius_km}
                onChange={(e) => set({ travel_radius_km: Number(e.target.value) })}
              />
            </label>
          </div>
          <div className="field-row">
            <label>
              Lowest hourly rate (CAD)
              <input
                type="number"
                min={0}
                step={1}
                value={form.rate_min}
                onChange={(e) => set({ rate_min: e.target.value })}
              />
            </label>
            <label>
              Highest hourly rate (CAD)
              <input
                type="number"
                min={0}
                step={1}
                value={form.rate_max}
                onChange={(e) => set({ rate_max: e.target.value })}
              />
            </label>
          </div>
          <label>
            Short bio
            <textarea
              value={form.bio}
              onChange={(e) => set({ bio: e.target.value })}
              maxLength={1000}
            />
          </label>
          <label>
            LinkedIn profile link <small>(optional)</small>
            <input
              type="url"
              value={form.linkedin_url}
              placeholder="https://www.linkedin.com/in/your-name"
              onChange={(e) => set({ linkedin_url: e.target.value })}
            />
          </label>
        </div>
        {error && (
          <div className="form-error" role="alert">
            {error}
          </div>
        )}
        <div className="editor-actions">
          <button type="button" className="button button-outline" disabled={busy} onClick={onClose}>
            Cancel
          </button>
          <button className="button button-primary" disabled={busy}>
            {busy ? 'Saving…' : 'Save profile'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function HistoryDialog({
  entry,
  onClose,
  onSaved,
}: {
  entry: WorkHistory | null;
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const [form, setForm] = useState({
    role: entry?.role || '',
    company: entry?.company || '',
    city: entry?.city || '',
    start_date: entry?.start_date || '',
    end_date: entry?.end_date || '',
    description: entry?.description || '',
    reference_name: entry?.reference_name || '',
    reference_contact: entry?.reference_contact || '',
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const set = (patch: Partial<typeof form>) => setForm((f) => ({ ...f, ...patch }));
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await market(entry ? `/work-history/${entry.id}` : '/work-history', {
        method: entry ? 'PUT' : 'POST',
        body: {
          ...form,
          end_date: form.end_date || null,
          reference_name: form.reference_name || null,
          reference_contact: form.reference_contact || null,
        },
      });
      await onSaved();
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  };
  return (
    <Modal title={entry ? 'Edit job' : 'Add a job'} onClose={onClose} busy={busy}>
      <form onSubmit={submit}>
        <div className="editor-fields">
          <div className="field-row">
            <label>
              Role
              <input
                value={form.role}
                onChange={(e) => set({ role: e.target.value })}
                required
                maxLength={160}
              />
            </label>
            <label>
              Company
              <input
                value={form.company}
                onChange={(e) => set({ company: e.target.value })}
                required
                maxLength={160}
              />
            </label>
          </div>
          <label>
            City
            <input
              value={form.city}
              onChange={(e) => set({ city: e.target.value })}
              maxLength={100}
            />
          </label>
          <div className="field-row">
            <label>
              Started
              <input
                type="date"
                value={form.start_date}
                onChange={(e) => set({ start_date: e.target.value })}
                required
              />
            </label>
            <label>
              Finished <small>(leave empty if current)</small>
              <input
                type="date"
                value={form.end_date}
                onChange={(e) => set({ end_date: e.target.value })}
              />
            </label>
          </div>
          <label>
            What you did
            <textarea
              value={form.description}
              onChange={(e) => set({ description: e.target.value })}
              maxLength={1000}
            />
          </label>
          <div className="field-row">
            <label>
              Reference name <small>(optional)</small>
              <input
                value={form.reference_name}
                onChange={(e) => set({ reference_name: e.target.value })}
                maxLength={160}
              />
            </label>
            <label>
              Reference phone or email <small>(optional)</small>
              <input
                value={form.reference_contact}
                onChange={(e) => set({ reference_contact: e.target.value })}
                maxLength={160}
              />
            </label>
          </div>
        </div>
        {error && (
          <div className="form-error" role="alert">
            {error}
          </div>
        )}
        <div className="editor-actions">
          {entry && (
            <button
              type="button"
              className="text-button danger-text"
              disabled={busy}
              onClick={async () => {
                if (!window.confirm('Delete this job from your history?')) return;
                setBusy(true);
                try {
                  await market(`/work-history/${entry.id}`, { method: 'DELETE' });
                  await onSaved();
                } catch (err) {
                  setError((err as Error).message);
                  setBusy(false);
                }
              }}
            >
              Delete
            </button>
          )}
          <button type="button" className="button button-outline" disabled={busy} onClick={onClose}>
            Cancel
          </button>
          <button className="button button-primary" disabled={busy}>
            {busy ? 'Saving…' : 'Save job'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function CompanyProfilePage() {
  const { refresh: refreshSession } = useSession();
  const [data, setData] = useState<OrgProfile | null>(null);
  const [error, setError] = useState('');
  const [editing, setEditing] = useState(false);
  const meta = useMeta();
  const load = useCallback(async () => {
    try {
      setData(await market<OrgProfile>('/org/profile'));
      setError('');
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);
  useEffect(() => {
    void load();
  }, [load]);
  if (error) return <ErrorNote message={error} retry={() => void load()} />;
  if (!data) return <Skeleton lines={3} />;
  const org = data.organization;
  return (
    <>
      <section className="profile-hero">
        <CompanyBadge name={org.name} industry={org.industry} size={80} />
        <div className="profile-hero-text">
          <h1>{org.name}</h1>
          <p className="profile-headline">
            {org.kind === 'agency' ? 'Contracting company' : 'Hiring business'}
            {org.industry ? ` · ${org.industry}` : ''}
          </p>
          <ul className="contract-facts">
            {org.city && (
              <li>
                <MapPin size={16} aria-hidden="true" />
                {org.city}
              </li>
            )}
            {org.website && (
              <li>
                <Globe size={16} aria-hidden="true" />
                <a href={org.website} target="_blank" rel="noreferrer">
                  {org.website.replace(/^https?:\/\//, '')}
                </a>
              </li>
            )}
            <li>
              <StatusChip
                status={org.verification_status === 'verified' ? 'verified' : 'self_reported'}
                label={
                  org.verification_status === 'verified' ? 'Verified business' : 'Not yet verified'
                }
              />
            </li>
          </ul>
          {org.about && <p className="profile-bio">{org.about}</p>}
        </div>
        <button className="button button-outline" onClick={() => setEditing(true)}>
          <Pencil size={18} aria-hidden="true" />
          Edit company
        </button>
      </section>
      <CredentialWallet credentials={data.credentials} scope="org" onChange={() => load()} />
      {editing && meta && (
        <CompanyDialog
          data={data}
          meta={meta}
          onClose={() => setEditing(false)}
          onSaved={async () => {
            setEditing(false);
            await Promise.all([load(), refreshSession()]);
          }}
        />
      )}
    </>
  );
}

function CompanyDialog({
  data,
  meta,
  onClose,
  onSaved,
}: {
  data: OrgProfile;
  meta: Meta;
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const o = data.organization;
  const [form, setForm] = useState({
    name: o.name,
    industry: o.industry || '',
    city: o.city || '',
    website: o.website || '',
    about: o.about || '',
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const set = (patch: Partial<typeof form>) => setForm((f) => ({ ...f, ...patch }));
  return (
    <Modal title="Edit company" onClose={onClose} busy={busy}>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError('');
          try {
            await market('/org/profile', {
              method: 'PUT',
              body: { ...form, industry: form.industry || null, city: form.city || null },
            });
            await onSaved();
          } catch (err) {
            setError((err as Error).message);
            setBusy(false);
          }
        }}
      >
        <div className="editor-fields">
          <label>
            Company name
            <input
              value={form.name}
              onChange={(e) => set({ name: e.target.value })}
              required
              maxLength={160}
            />
          </label>
          <div className="field-row">
            <label>
              Industry
              <select value={form.industry} onChange={(e) => set({ industry: e.target.value })}>
                <option value="">Choose an industry</option>
                {meta.industries.map((i) => (
                  <option key={i}>{i}</option>
                ))}
              </select>
            </label>
            <label>
              City
              <select value={form.city} onChange={(e) => set({ city: e.target.value })}>
                <option value="">Choose a city</option>
                {meta.cities.map((c) => (
                  <option key={c.name}>{c.name}</option>
                ))}
              </select>
            </label>
          </div>
          <label>
            Website <small>(optional)</small>
            <input
              type="url"
              value={form.website}
              onChange={(e) => set({ website: e.target.value })}
            />
          </label>
          <label>
            About
            <textarea
              value={form.about}
              onChange={(e) => set({ about: e.target.value })}
              maxLength={1000}
            />
          </label>
        </div>
        {error && (
          <div className="form-error" role="alert">
            {error}
          </div>
        )}
        <div className="editor-actions">
          <button type="button" className="button button-outline" disabled={busy} onClick={onClose}>
            Cancel
          </button>
          <button className="button button-primary" disabled={busy}>
            {busy ? 'Saving…' : 'Save company'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
