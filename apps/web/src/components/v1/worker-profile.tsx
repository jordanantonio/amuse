'use client';
import { useCallback, useEffect, useState } from 'react';
import {
  BadgeCheck,
  CalendarCheck,
  Languages,
  MapPin,
  Pencil,
  Plus,
  Star,
  Wrench,
} from 'lucide-react';
import { market } from '@/lib/market';
import type { Meta, Profile, WorkHistory } from '@/lib/market-types';
import { day, dollars } from '@/lib/format';
import { useSession } from './session';
import { Blueprint } from './blueprint';
import { CompanyBadge, PersonAvatar } from './avatar';
import { CredentialWallet } from './wallet';
import { EmptyState, ErrorNote, Skeleton, StatusChip } from './ui';

type Save = (body: Record<string, unknown>) => Promise<void>;

/** PROFILE-1..7: a LinkedIn-style page that reads like a person. */
export function WorkerProfile() {
  const { refresh: refreshSession } = useSession();
  const [data, setData] = useState<Profile | null>(null);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [error, setError] = useState('');
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
    market<Meta>('/meta').then(setMeta, () => undefined);
    // PROFILE-7: the profile uses the vibrant blueprint blue.
    const shell = document.querySelector('.v1-shell');
    shell?.classList.add('theme-vivid');
    return () => shell?.classList.remove('theme-vivid');
  }, [load]);
  const save: Save = async (body) => {
    setData(await market<Profile>('/me/profile', { method: 'PUT', body }));
    await refreshSession();
  };
  if (error && !data) return <ErrorNote message={error} retry={() => void load()} />;
  if (!data) return <Skeleton lines={4} />;
  const { profile, user, completeness } = data;
  return (
    <div className="lprofile">
      <Header data={data} meta={meta} save={save} />
      {completeness.percent < 100 && completeness.next_step && (
        <p className="lprofile-next">
          Profile {completeness.percent}% complete · Next: {completeness.next_step.label}
        </p>
      )}
      <Section
        title="About"
        editable
        renderEdit={(done) => <AboutEdit bio={profile.bio} save={save} done={done} />}
      >
        {profile.bio ? (
          <p className="lprofile-about">{profile.bio}</p>
        ) : (
          <p className="v1-lede">
            Say who you are, what you like working on and what you’re proud of.
          </p>
        )}
      </Section>
      <Experience history={data.history} reload={load} />
      <section className="lprofile-certs" aria-label="Certifications">
        <CredentialWallet
          credentials={data.credentials}
          scope="me"
          highlightType={completeness.next_step?.credential_type_id}
          onChange={() => load()}
        />
      </section>
      <div className="lprofile-grid">
        <Section
          title="Skills and trades"
          editable
          renderEdit={(done) => (
            <TradesEdit
              trades={profile.trades}
              options={meta?.trades || []}
              save={save}
              done={done}
            />
          )}
        >
          <Chips items={profile.trades} empty="Add the trades you work in" />
        </Section>
        <Section
          title="Tools and equipment I own"
          icon={Wrench}
          editable
          renderEdit={(done) => (
            <ListEdit
              label="Tools and equipment"
              items={profile.tools || []}
              field="tools"
              save={save}
              done={done}
            />
          )}
        >
          <Chips items={profile.tools || []} empty="List tools and equipment you bring" />
        </Section>
        <Section
          title="Languages"
          icon={Languages}
          editable
          renderEdit={(done) => (
            <ListEdit
              label="Languages"
              items={profile.languages || []}
              field="languages"
              save={save}
              done={done}
            />
          )}
        >
          <Chips items={profile.languages || []} empty="Add the languages you speak" />
        </Section>
      </div>
      <Section title="Reviews from employers on Shift">
        {data.reviews.length ? (
          <ul className="reviews">
            {data.reviews.map((r) => (
              <li key={r.id} className="review">
                <Stars rating={r.rating} />
                <blockquote>“{r.quote}”</blockquote>
                <div className="review-who">
                  <PersonAvatar name={r.author_name.split(',')[0]} size={36} />
                  <span>{r.author_name}</span>
                  <CompanyBadge name={r.org_name} industry={r.org_industry} size={28} />
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="v1-lede">Reviews appear after you finish contracts on Shift.</p>
        )}
      </Section>
      <p className="lprofile-foot">
        {user.email} · Profile {profile.is_public ? 'visible to businesses' : 'hidden'}
      </p>
    </div>
  );
}

function Header({ data, meta, save }: { data: Profile; meta: Meta | null; save: Save }) {
  const [editing, setEditing] = useState(false);
  const { profile, user, availability } = data;
  return (
    <section className="lprofile-head light-card">
      <div className="lprofile-banner">
        <Blueprint />
      </div>
      <div className="lprofile-id">
        <PersonAvatar
          id={user.id}
          name={user.full_name}
          size={128}
          ring
          className="lprofile-photo"
        />
        <button
          className="icon-button tap lprofile-pencil"
          aria-label="Edit name, headline and location"
          onClick={() => setEditing(!editing)}
        >
          <Pencil size={18} />
        </button>
        {!editing ? (
          <>
            <h1>{user.full_name}</h1>
            <p className="lprofile-headline">{profile.headline || 'Add a headline'}</p>
            <p className="lprofile-meta">
              <MapPin size={16} aria-hidden="true" />
              {profile.city || 'City not set'} · travels {profile.travel_radius_km} km
              {profile.rate_min_cents != null && ` · from ${dollars(profile.rate_min_cents)}/h`}
            </p>
            {availability && (
              <span className={`avail-pill ${availability.status}`}>
                <CalendarCheck size={16} aria-hidden="true" />
                {availability.label}
              </span>
            )}
          </>
        ) : (
          <HeaderEdit data={data} meta={meta} save={save} done={() => setEditing(false)} />
        )}
      </div>
    </section>
  );
}

function HeaderEdit({
  data,
  meta,
  save,
  done,
}: {
  data: Profile;
  meta: Meta | null;
  save: Save;
  done: () => void;
}) {
  const p = data.profile;
  const [form, setForm] = useState({
    full_name: data.user.full_name,
    headline: p.headline,
    city: p.city,
    travel_radius_km: p.travel_radius_km,
    rate_min: p.rate_min_cents != null ? String(p.rate_min_cents / 100) : '',
  });
  return (
    <InlineForm
      done={done}
      submit={() =>
        save({
          full_name: form.full_name,
          headline: form.headline,
          city: form.city || null,
          travel_radius_km: form.travel_radius_km,
          rate_min_cents: form.rate_min ? Math.round(Number(form.rate_min) * 100) : null,
        })
      }
    >
      <label>
        Name
        <input
          value={form.full_name}
          onChange={(e) => setForm({ ...form, full_name: e.target.value })}
          required
          maxLength={160}
        />
      </label>
      <label>
        Headline
        <input
          value={form.headline}
          onChange={(e) => setForm({ ...form, headline: e.target.value })}
          maxLength={160}
        />
      </label>
      <div className="field-row three">
        <label>
          City
          <select value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })}>
            <option value="">Choose a city</option>
            {meta?.cities.map((c) => (
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
            onChange={(e) => setForm({ ...form, travel_radius_km: Number(e.target.value) })}
          />
        </label>
        <label>
          Lowest rate (CAD/h)
          <input
            type="number"
            min={0}
            value={form.rate_min}
            onChange={(e) => setForm({ ...form, rate_min: e.target.value })}
          />
        </label>
      </div>
    </InlineForm>
  );
}

function Section({
  title,
  icon: Icon,
  editable = false,
  renderEdit,
  children,
}: {
  title: string;
  icon?: typeof Wrench;
  editable?: boolean;
  renderEdit?: (done: () => void) => React.ReactNode;
  children: React.ReactNode;
}) {
  const [editing, setEditing] = useState(false);
  return (
    <section className="lprofile-section light-card">
      <header>
        <h2>
          {Icon && <Icon size={20} aria-hidden="true" />} {title}
        </h2>
        {editable && (
          <button
            className="icon-button tap"
            aria-label={`Edit ${title}`}
            aria-pressed={editing}
            onClick={() => setEditing(!editing)}
          >
            <Pencil size={18} />
          </button>
        )}
      </header>
      {editing && renderEdit ? renderEdit(() => setEditing(false)) : children}
    </section>
  );
}

function InlineForm({
  submit,
  done,
  children,
}: {
  submit: () => Promise<void>;
  done: () => void;
  children: React.ReactNode;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  return (
    <form
      className="inline-form"
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        setError('');
        try {
          await submit();
          done();
        } catch (err) {
          setError((err as Error).message);
        } finally {
          setBusy(false);
        }
      }}
    >
      {children}
      {error && <p className="v1-inline-error">{error}</p>}
      <div className="actions">
        <button className="button button-primary button-sm" disabled={busy}>
          {busy ? 'Saving…' : 'Save'}
        </button>
        <button type="button" className="text-button" onClick={done} disabled={busy}>
          Cancel
        </button>
      </div>
    </form>
  );
}

function AboutEdit({ bio, save, done }: { bio: string; save: Save; done: () => void }) {
  const [value, setValue] = useState(bio);
  return (
    <InlineForm submit={() => save({ bio: value })} done={done}>
      <label>
        <span className="sr-only">About you</span>
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          maxLength={1000}
          rows={6}
          autoFocus
        />
      </label>
    </InlineForm>
  );
}

function TradesEdit({
  trades,
  options,
  save,
  done,
}: {
  trades: string[];
  options: string[];
  save: Save;
  done: () => void;
}) {
  const [value, setValue] = useState(trades);
  return (
    <InlineForm submit={() => save({ trades: value })} done={done}>
      <div className="chips">
        {options.map((t) => {
          const on = value.includes(t);
          return (
            <label key={t} className={`chip ${on ? 'on' : ''}`}>
              <input
                type="checkbox"
                checked={on}
                onChange={() => setValue(on ? value.filter((x) => x !== t) : [...value, t])}
              />
              {t}
            </label>
          );
        })}
      </div>
    </InlineForm>
  );
}

function ListEdit({
  label,
  items,
  field,
  save,
  done,
}: {
  label: string;
  items: string[];
  field: string;
  save: Save;
  done: () => void;
}) {
  const [value, setValue] = useState(items.join(', '));
  return (
    <InlineForm
      submit={() =>
        save({
          [field]: value
            .split(',')
            .map((x) => x.trim())
            .filter(Boolean)
            .slice(0, 20),
        })
      }
      done={done}
    >
      <label>
        {label} <small>(separate with commas)</small>
        <input value={value} onChange={(e) => setValue(e.target.value)} autoFocus />
      </label>
    </InlineForm>
  );
}

function Chips({ items, empty }: { items: string[]; empty: string }) {
  if (!items.length) return <p className="v1-lede">{empty}</p>;
  return (
    <ul className="tag-list big">
      {items.map((t) => (
        <li key={t}>{t}</li>
      ))}
    </ul>
  );
}

function Stars({ rating }: { rating: number }) {
  return (
    <span className="stars" role="img" aria-label={`${rating} out of 5 stars`}>
      {Array.from({ length: 5 }, (_, i) => (
        <Star key={i} size={16} aria-hidden="true" className={i < rating ? 'on' : ''} />
      ))}
    </span>
  );
}

function Experience({ history, reload }: { history: WorkHistory[]; reload: () => Promise<void> }) {
  const [editing, setEditing] = useState<string | 'new' | null>(null);
  return (
    <section className="lprofile-section light-card">
      <header>
        <h2>Experience</h2>
        <button className="button button-outline button-sm" onClick={() => setEditing('new')}>
          <Plus size={16} aria-hidden="true" /> Add a job
        </button>
      </header>
      {editing === 'new' && (
        <HistoryForm entry={null} done={() => setEditing(null)} saved={reload} />
      )}
      {!history.length && editing !== 'new' && (
        <EmptyState title="No past jobs yet">
          Contracts you finish on Shift are added for you.
        </EmptyState>
      )}
      <ol className="timeline">
        {history.map((h) => (
          <li key={h.id}>
            <CompanyBadge name={h.company} size={48} />
            <div className="timeline-body">
              {editing === h.id ? (
                <HistoryForm entry={h} done={() => setEditing(null)} saved={reload} />
              ) : (
                <>
                  <div className="timeline-top">
                    <div>
                      <strong>{h.role}</strong>
                      <p>{h.company}</p>
                      <p className="wallet-meta">
                        {day(h.start_date, true)} – {h.end_date ? day(h.end_date, true) : 'present'}
                        {h.city ? ` · ${h.city}` : ''}
                      </p>
                    </div>
                    {!h.engagement_id && (
                      <button
                        className="icon-button tap"
                        aria-label={`Edit ${h.role} at ${h.company}`}
                        onClick={() => setEditing(h.id)}
                      >
                        <Pencil size={18} />
                      </button>
                    )}
                  </div>
                  {h.engagement_id && (
                    <div className="shift-done">
                      <StatusChip status="verified" label="Completed on Shift" icon={BadgeCheck} />
                      {h.rating != null && <Stars rating={h.rating} />}
                    </div>
                  )}
                  {h.description && <p className="timeline-desc">{h.description}</p>}
                  {!!h.photo_paths?.length && (
                    <ul className="gallery" aria-label="Photos of the work">
                      {h.photo_paths.map((src) => (
                        <li key={src}>
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img src={src} alt="" loading="lazy" width={160} height={100} />
                        </li>
                      ))}
                    </ul>
                  )}
                </>
              )}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

function HistoryForm({
  entry,
  done,
  saved,
}: {
  entry: WorkHistory | null;
  done: () => void;
  saved: () => Promise<void>;
}) {
  const [form, setForm] = useState({
    role: entry?.role || '',
    company: entry?.company || '',
    city: entry?.city || '',
    start_date: entry?.start_date || '',
    end_date: entry?.end_date || '',
    description: entry?.description || '',
  });
  const set = (patch: Partial<typeof form>) => setForm((f) => ({ ...f, ...patch }));
  return (
    <InlineForm
      done={done}
      submit={async () => {
        await market(entry ? `/work-history/${entry.id}` : '/work-history', {
          method: entry ? 'PUT' : 'POST',
          body: { ...form, end_date: form.end_date || null },
        });
        await saved();
      }}
    >
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
      <div className="field-row three">
        <label>
          City
          <input
            value={form.city}
            onChange={(e) => set({ city: e.target.value })}
            maxLength={100}
          />
        </label>
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
          Finished
          <input
            type="date"
            value={form.end_date}
            onChange={(e) => set({ end_date: e.target.value })}
          />
        </label>
      </div>
      <label>
        What you did <small>(1–3 lines)</small>
        <textarea
          value={form.description}
          onChange={(e) => set({ description: e.target.value })}
          maxLength={400}
          rows={3}
        />
      </label>
      {entry && (
        <button
          type="button"
          className="text-button danger-text"
          onClick={async () => {
            if (!window.confirm('Delete this job from your history?')) return;
            await market(`/work-history/${entry.id}`, { method: 'DELETE' });
            await saved();
            done();
          }}
        >
          Delete this job
        </button>
      )}
    </InlineForm>
  );
}
