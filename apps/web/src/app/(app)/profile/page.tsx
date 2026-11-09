'use client';
import { useCallback, useEffect, useState } from 'react';
import { MapPin, Pencil, Plus, BadgeCheck, Globe } from 'lucide-react';
import { market } from '@/lib/market';
import type { Meta, OrgProfile, Profile, WorkHistory } from '@/lib/market-types';
import { day, dollars, initials } from '@/lib/format';
import { useSession } from '@/components/v1/session';
import { WorkerProfile } from '@/components/v1/worker-profile';
import { CredentialWallet } from '@/components/v1/wallet';
import { EmptyState, ErrorNote, Modal, Skeleton, StatusChip } from '@/components/v1/ui';
import { CompanyBadge, PersonAvatar } from '@/components/v1/avatar';

export default function ProfilePage() {
  const { me } = useSession();
  return me.mode === 'worker' ? <WorkerProfile /> : <CompanyProfilePage />;
}

function useMeta() {
  const [meta, setMeta] = useState<Meta | null>(null);
  useEffect(() => {
    market<Meta>('/meta').then(setMeta, () => undefined);
  }, []);
  return meta;
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
