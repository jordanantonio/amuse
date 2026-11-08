'use client';
import { useEffect, useState } from 'react';
import { market } from '@/lib/market';
import type { CredentialType, Meta, PostingCard } from '@/lib/market-types';
import { todayIso } from '@/lib/format';
import { Modal } from './ui';
import { PATTERNS } from './contract';

type Req = { credential_type_id: string; required: boolean; must_be_verified: boolean };
const plusDays = (iso: string, n: number) => {
  const d = new Date(iso + 'T12:00:00');
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
};

/** POST-1: one-screen posting form with sensible defaults and a trade template. */
export function PostingForm({
  posting,
  onClose,
  onSaved,
}: {
  posting?: PostingCard | null;
  onClose: () => void;
  onSaved: (p: PostingCard) => Promise<void> | void;
}) {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [types, setTypes] = useState<CredentialType[]>([]);
  const [templates, setTemplates] = useState<Record<string, string>>({});
  const start = plusDays(todayIso(), 14);
  const [form, setForm] = useState({
    title: posting?.title || '',
    trade: posting?.trade || '',
    posting_type: posting?.posting_type || 'individual',
    city: posting?.city || '',
    site_address: posting?.site_address || '',
    start_date: posting?.start_date || start,
    end_date: posting?.end_date || plusDays(start, 90),
    schedule_pattern: posting?.schedule_pattern || 'mon_fri',
    is_exclusive: posting?.is_exclusive ?? true,
    pay: posting ? String(posting.pay_rate_cents / 100) : '',
    pay_unit: posting?.pay_unit || 'hour',
    headcount: String(posting?.headcount || 1),
    description: posting?.description || '',
  });
  const [reqs, setReqs] = useState<Req[]>(
    posting?.match.items.map((i) => ({
      credential_type_id: i.credential_type_id,
      required: i.required,
      must_be_verified: i.must_be_verified,
    })) || [],
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    market<Meta>('/meta').then(setMeta, () => undefined);
    market<CredentialType[]>('/credential-types').then(setTypes, () => undefined);
    market<Record<string, string>>('/posting-templates').then(setTemplates, () => undefined);
  }, []);
  const set = (patch: Partial<typeof form>) => setForm((f) => ({ ...f, ...patch }));
  const applies = form.posting_type === 'agency' ? 'org' : 'worker';
  const options = types.filter((t) => t.applies_to === applies);
  const toggle = (id: string, required: boolean) =>
    setReqs((rs) => {
      const existing = rs.find((r) => r.credential_type_id === id);
      if (existing && existing.required === required)
        return rs.filter((r) => r.credential_type_id !== id);
      if (existing) return rs.map((r) => (r.credential_type_id === id ? { ...r, required } : r));
      return [...rs, { credential_type_id: id, required, must_be_verified: false }];
    });

  const submit = async (status: 'open' | 'draft') => {
    setBusy(true);
    setError('');
    try {
      const saved = await market<PostingCard>(posting ? `/postings/${posting.id}` : '/postings', {
        method: posting ? 'PUT' : 'POST',
        body: {
          ...form,
          site_address: form.site_address || null,
          pay_rate_cents: Math.round(Number(form.pay) * 100),
          headcount: Number(form.headcount),
          requirements: reqs,
          status: posting && posting.status === 'open' ? 'open' : status,
        },
      });
      await onSaved(saved);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  };
  return (
    <Modal
      title={posting ? 'Edit posting' : 'New posting'}
      description="Workers see contracts that match their tickets. The site address stays hidden until you send an offer."
      onClose={onClose}
      busy={busy}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void submit('open');
        }}
      >
        <div className="editor-fields">
          <fieldset className="segmented-field">
            <legend>Who are you hiring?</legend>
            {[
              ['individual', 'A person'],
              ['agency', 'A crew or company'],
            ].map(([v, label]) => (
              <label key={v} className={`chip ${form.posting_type === v ? 'on' : ''}`}>
                <input
                  type="radio"
                  name="posting_type"
                  checked={form.posting_type === v}
                  onChange={() => {
                    set({ posting_type: v as 'individual' | 'agency' });
                    setReqs([]);
                  }}
                />
                {label}
              </label>
            ))}
          </fieldset>
          <div className="field-row">
            <label>
              Trade
              <select
                value={form.trade}
                required
                onChange={(e) => {
                  const trade = e.target.value;
                  const isTemplate =
                    !form.description || Object.values(templates).includes(form.description);
                  set({ trade, ...(isTemplate ? { description: templates[trade] || '' } : {}) });
                }}
              >
                <option value="">Choose a trade</option>
                {meta?.trades.map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </select>
            </label>
            <label>
              Title
              <input
                value={form.title}
                onChange={(e) => set({ title: e.target.value })}
                required
                minLength={3}
                maxLength={160}
                placeholder="Framer, 12-home phase"
              />
            </label>
          </div>
          <div className="field-row">
            <label>
              City
              <select value={form.city} onChange={(e) => set({ city: e.target.value })} required>
                <option value="">Choose a city</option>
                {meta?.cities.map((c) => (
                  <option key={c.name}>{c.name}</option>
                ))}
              </select>
            </label>
            <label>
              Site address <small>(shared with an offer)</small>
              <input
                value={form.site_address}
                onChange={(e) => set({ site_address: e.target.value })}
                maxLength={300}
              />
            </label>
          </div>
          <div className="field-row">
            <label>
              Starts
              <input
                type="date"
                value={form.start_date}
                onChange={(e) => set({ start_date: e.target.value })}
                required
              />
            </label>
            <label>
              Ends
              <input
                type="date"
                value={form.end_date}
                min={form.start_date}
                onChange={(e) => set({ end_date: e.target.value })}
                required
              />
            </label>
          </div>
          <div className="field-row">
            <label>
              Schedule
              <select
                value={form.schedule_pattern}
                onChange={(e) => set({ schedule_pattern: e.target.value })}
              >
                {Object.entries(PATTERNS).map(([v, label]) => (
                  <option key={v} value={v}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Commitment
              <select
                value={form.is_exclusive ? 'yes' : 'no'}
                onChange={(e) => set({ is_exclusive: e.target.value === 'yes' })}
              >
                <option value="yes">Full-time: blocks the whole date range</option>
                <option value="no">Part-time: blocks only scheduled days</option>
              </select>
            </label>
          </div>
          <div className="field-row three">
            <label>
              Pay (CAD)
              <input
                type="number"
                min={1}
                step="0.01"
                value={form.pay}
                onChange={(e) => set({ pay: e.target.value })}
                required
              />
            </label>
            <label>
              Per
              <select
                value={form.pay_unit}
                onChange={(e) => set({ pay_unit: e.target.value as 'hour' })}
              >
                <option value="hour">Hour</option>
                <option value="day">Day</option>
                <option value="fixed">Whole contract</option>
              </select>
            </label>
            <label>
              {form.posting_type === 'agency' ? 'Crew size' : 'Openings'}
              <input
                type="number"
                min={1}
                max={200}
                value={form.headcount}
                onChange={(e) => set({ headcount: e.target.value })}
                required
              />
            </label>
          </div>
          <fieldset className="req-field">
            <legend>{form.posting_type === 'agency' ? 'Company credentials' : 'Tickets'}</legend>
            <small>
              Required tickets decide who can apply. Nice-to-haves only improve ranking.
            </small>
            <ul className="req-list">
              {options.map((t) => {
                const r = reqs.find((x) => x.credential_type_id === t.id);
                return (
                  <li key={t.id} className={r ? (r.required ? 'req on' : 'req nice') : 'req'}>
                    <span>{t.name}</span>
                    <div className="req-buttons">
                      <button
                        type="button"
                        aria-pressed={r?.required === true}
                        onClick={() => toggle(t.id, true)}
                      >
                        Required
                      </button>
                      <button
                        type="button"
                        aria-pressed={r?.required === false}
                        onClick={() => toggle(t.id, false)}
                      >
                        Nice to have
                      </button>
                      {r?.required && (
                        <label className="mini-check">
                          <input
                            type="checkbox"
                            checked={r.must_be_verified}
                            onChange={(e) =>
                              setReqs((rs) =>
                                rs.map((x) =>
                                  x.credential_type_id === t.id
                                    ? { ...x, must_be_verified: e.target.checked }
                                    : x,
                                ),
                              )
                            }
                          />
                          Must be verified
                        </label>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          </fieldset>
          <label>
            Description
            <textarea
              value={form.description}
              onChange={(e) => set({ description: e.target.value })}
              maxLength={3000}
            />
          </label>
        </div>
        {error && (
          <div className="form-error" role="alert">
            {error}
          </div>
        )}
        <div className="editor-actions">
          {!posting && (
            <button
              type="button"
              className="text-button"
              disabled={busy}
              onClick={() => void submit('draft')}
            >
              Save as draft
            </button>
          )}
          <button type="button" className="button button-outline" disabled={busy} onClick={onClose}>
            Cancel
          </button>
          <button className="button button-primary" disabled={busy}>
            {busy ? 'Saving…' : posting ? 'Save changes' : 'Publish posting'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
