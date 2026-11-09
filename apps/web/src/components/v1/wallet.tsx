'use client';
import { useEffect, useMemo, useState } from 'react';
import { FileText, Paperclip, Pencil, Plus, Trash2, Upload } from 'lucide-react';
import { market } from '@/lib/market';
import type { Credential, CredentialType } from '@/lib/market-types';
import { day, fileToBase64 } from '@/lib/format';
import { EmptyState, ExpiryChip, Modal, StatusChip } from './ui';

const CATEGORY_ORDER = ['Trade', 'Safety', 'Equipment', 'Driving', 'Business', 'Other'];
const ACCEPT = 'application/pdf,image/jpeg,image/png,image/webp';
const MAX_BYTES = 5 * 1024 * 1024;

/** CRED-1: grouped wallet cards with status chips. Shared by workers and companies. */
export function CredentialWallet({
  credentials,
  scope,
  onChange,
  highlightType,
}: {
  credentials: Credential[];
  scope: 'me' | 'org';
  onChange: () => Promise<void> | void;
  highlightType?: string | null;
}) {
  const [types, setTypes] = useState<CredentialType[]>([]);
  const [editing, setEditing] = useState<Credential | 'new' | null>(null);
  const [preset, setPreset] = useState<string | null>(null);
  useEffect(() => {
    market<CredentialType[]>('/credential-types').then(setTypes, () => setTypes([]));
  }, []);
  const groups = useMemo(() => {
    const by = new Map<string, Credential[]>();
    for (const c of credentials) by.set(c.category, [...(by.get(c.category) || []), c]);
    return CATEGORY_ORDER.filter((c) => by.has(c)).map((c) => [c, by.get(c)!] as const);
  }, [credentials]);
  const noun = scope === 'me' ? 'certification' : 'credential';
  return (
    <section className="v1-section" aria-labelledby={`wallet-${scope}`}>
      <div className="v1-section-head">
        <h2 id={`wallet-${scope}`}>{scope === 'me' ? 'Certifications' : 'Company credentials'}</h2>
        <button
          className="button button-outline"
          onClick={() => {
            setPreset(null);
            setEditing('new');
          }}
        >
          <Plus size={18} aria-hidden="true" />
          {scope === 'me' ? 'Upload certification' : `Add ${noun}`}
        </button>
      </div>
      {!credentials.length && (
        <EmptyState
          title={`No ${noun}s yet`}
          action={
            <button className="button button-primary" onClick={() => setEditing('new')}>
              Add your first {noun}
            </button>
          }
        >
          {scope === 'me'
            ? 'Contracts list the certifications they need. Add yours so Shift can show the work you qualify for.'
            : 'Verified company credentials (COR, WCB clearance, insurance) build trust with workers.'}
        </EmptyState>
      )}
      {highlightType && !credentials.some((c) => c.credential_type_id === highlightType) && (
        <button
          className="unlock-hint"
          onClick={() => {
            setPreset(highlightType);
            setEditing('new');
          }}
        >
          <Plus size={18} aria-hidden="true" />
          Add {types.find((t) => t.id === highlightType)?.name || 'this certification'}
        </button>
      )}
      {groups.map(([category, items]) => (
        <div key={category} className="wallet-group">
          <h3>{category}</h3>
          <ul className="wallet-grid">
            {items.map((c) => (
              <li key={c.id} className={`wallet-card ${c.status}`}>
                <DocThumb credential={c} />
                <div className="wallet-card-top">
                  <strong>{c.name}</strong>
                  <StatusChip status={c.status} />
                </div>
                <p className="wallet-meta">
                  {c.issuer || 'Issuer not set'}
                  {c.number ? ` · No. ${c.number}` : ''}
                </p>
                <p className="wallet-meta">
                  {c.expires_on
                    ? `${c.status === 'expired' ? 'Expired' : 'Expires'} ${day(c.expires_on, true)}`
                    : 'No expiry'}
                </p>
                {c.expiring_soon && c.days_to_expiry != null && (
                  <ExpiryChip days={c.days_to_expiry} />
                )}
                {c.status === 'rejected' && c.rejection_reason && (
                  <p className="wallet-reason">Reason: {c.rejection_reason}</p>
                )}
                <div className="wallet-actions">
                  {c.has_document ? (
                    <DocumentLink credential={c} />
                  ) : (
                    <span className="wallet-meta">
                      <Paperclip size={15} aria-hidden="true" /> No proof uploaded
                    </span>
                  )}
                  <button
                    className="icon-button tap"
                    aria-label={`Edit ${c.name}`}
                    onClick={() => setEditing(c)}
                  >
                    <Pencil size={18} />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      ))}
      {editing && (
        <CredentialDialog
          credential={editing === 'new' ? null : editing}
          preset={preset}
          types={types.filter((t) => t.applies_to === (scope === 'me' ? 'worker' : 'org'))}
          scope={scope}
          onClose={() => setEditing(null)}
          onSaved={async () => {
            setEditing(null);
            await onChange();
          }}
        />
      )}
    </section>
  );
}

function DocumentLink({ credential }: { credential: Credential }) {
  const [error, setError] = useState('');
  return (
    <button
      className="text-button doc-link"
      onClick={async () => {
        setError('');
        try {
          const { url } = await market<{ url: string }>(
            `/credentials/${credential.id}/document-link`,
          );
          window.open(url, '_blank', 'noopener');
        } catch (e) {
          setError((e as Error).message);
        }
      }}
    >
      <FileText size={16} aria-hidden="true" />
      {credential.document_name || 'View proof'}
      {error && <span role="alert"> {error}</span>}
    </button>
  );
}

function CredentialDialog({
  credential,
  preset,
  types,
  scope,
  onClose,
  onSaved,
}: {
  credential: Credential | null;
  preset: string | null;
  types: CredentialType[];
  scope: 'me' | 'org';
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const [typeId, setTypeId] = useState(credential?.credential_type_id || preset || '');
  const [customName, setCustomName] = useState(
    credential?.credential_type_id ? '' : credential?.name || '',
  );
  const chosen = types.find((t) => t.id === typeId);
  const [issuer, setIssuer] = useState(credential?.issuer || chosen?.default_issuer || '');
  const [number, setNumber] = useState(credential?.number || '');
  const [issued, setIssued] = useState(credential?.issued_on || '');
  const [expires, setExpires] = useState(credential?.expires_on || '');
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const categories = [...new Set(types.map((t) => t.category))];

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (file && file.size > MAX_BYTES) return setError('Files must be 5 MB or smaller');
    setBusy(true);
    setError('');
    try {
      const body = {
        credential_type_id: typeId && typeId !== 'other' ? typeId : null,
        custom_name: typeId === 'other' || !typeId ? customName : null,
        issuer,
        number: number || null,
        issued_on: issued || null,
        expires_on: expires || null,
        scope,
      };
      const saved = await market<Credential>(
        credential ? `/credentials/${credential.id}` : '/credentials',
        {
          method: credential ? 'PUT' : 'POST',
          body,
        },
      );
      if (file)
        await market(`/credentials/${saved.id}/document`, {
          method: 'POST',
          body: {
            filename: file.name,
            content_type: file.type,
            data_base64: await fileToBase64(file),
          },
        });
      await onSaved();
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  };
  const remove = async () => {
    if (!credential || !window.confirm(`Delete ${credential.name} from your wallet?`)) return;
    setBusy(true);
    try {
      await market(`/credentials/${credential.id}`, { method: 'DELETE' });
      await onSaved();
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  };
  return (
    <Modal
      title={
        credential
          ? `Edit ${credential.name}`
          : scope === 'me'
            ? 'Add a certification'
            : 'Add a credential'
      }
      description="Upload a photo or PDF as proof. Only you, Shift reviewers and businesses you apply to can open it."
      onClose={onClose}
      busy={busy}
    >
      <form onSubmit={save}>
        <div className="editor-fields">
          <label>
            Type
            <select
              value={typeId}
              required
              onChange={(e) => {
                setTypeId(e.target.value);
                const t = types.find((x) => x.id === e.target.value);
                if (t && !issuer) setIssuer(t.default_issuer);
              }}
            >
              <option value="">Choose a type</option>
              {categories.map((cat) => (
                <optgroup key={cat} label={cat}>
                  {types
                    .filter((t) => t.category === cat)
                    .map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name}
                      </option>
                    ))}
                </optgroup>
              ))}
              <option value="other">Other (type a name)</option>
            </select>
          </label>
          {typeId === 'other' && (
            <label>
              Name
              <input
                value={customName}
                onChange={(e) => setCustomName(e.target.value)}
                required
                maxLength={160}
              />
            </label>
          )}
          <label>
            Issuer
            <input value={issuer} onChange={(e) => setIssuer(e.target.value)} maxLength={160} />
          </label>
          <label>
            Certificate number <small>(optional)</small>
            <input value={number} onChange={(e) => setNumber(e.target.value)} maxLength={80} />
          </label>
          <div className="field-row">
            <label>
              Issued on
              <input type="date" value={issued} onChange={(e) => setIssued(e.target.value)} />
            </label>
            <label>
              Expires on {chosen && !chosen.has_expiry && <small>(usually doesn’t expire)</small>}
              <input type="date" value={expires} onChange={(e) => setExpires(e.target.value)} />
            </label>
          </div>
          <DropZone file={file} setFile={setFile} hasDocument={!!credential?.has_document} />
        </div>
        {error && (
          <div className="form-error" role="alert">
            {error}
          </div>
        )}
        <div className="editor-actions">
          {credential && (
            <button
              type="button"
              className="text-button danger-text"
              disabled={busy}
              onClick={() => void remove()}
            >
              <Trash2 size={16} aria-hidden="true" /> Delete
            </button>
          )}
          <button type="button" className="button button-outline" disabled={busy} onClick={onClose}>
            Cancel
          </button>
          <button className="button button-primary" disabled={busy}>
            {busy ? 'Saving…' : 'Save'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

/** PROFILE-4: thumbnail of the uploaded proof (image via a short-lived link, PDFs as an icon). */
function DocThumb({ credential }: { credential: Credential }) {
  const [src, setSrc] = useState<string | null>(null);
  const isImage = credential.document_type?.startsWith('image/');
  useEffect(() => {
    if (!credential.has_document || !isImage) return;
    market<{ url: string }>(`/credentials/${credential.id}/document-link`).then(
      (r) => setSrc(r.url),
      () => setSrc(null),
    );
  }, [credential.id, credential.has_document, isImage]);
  return (
    <div className={`doc-thumb ${credential.has_document ? '' : 'empty'}`} aria-hidden="true">
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={src} alt="" />
      ) : credential.has_document ? (
        <FileText size={28} />
      ) : (
        <Paperclip size={22} />
      )}
    </div>
  );
}

/** Drag-and-drop or browse for a photo or PDF, with a preview before saving. */
function DropZone({
  file,
  setFile,
  hasDocument,
}: {
  file: File | null;
  setFile: (f: File | null) => void;
  hasDocument: boolean;
}) {
  const [over, setOver] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  useEffect(() => {
    if (!file || !file.type.startsWith('image/')) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  return (
    <div
      className={`drop-zone ${over ? 'over' : ''}`}
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        const f = e.dataTransfer.files?.[0];
        if (f) setFile(f);
      }}
    >
      {file ? (
        <div className="drop-preview">
          {preview ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={preview} alt="Preview of the selected certification" />
          ) : (
            <FileText size={36} aria-hidden="true" />
          )}
          <span>
            <strong>{file.name}</strong>
            {(file.size / 1024).toFixed(0)} KB
          </span>
          <button type="button" className="text-button" onClick={() => setFile(null)}>
            Remove
          </button>
        </div>
      ) : (
        <>
          <Upload size={28} aria-hidden="true" />
          <p>
            <strong>Drag a photo or PDF here</strong>
            {hasDocument ? ' to replace the current proof' : ''}
          </p>
        </>
      )}
      <label className="drop-browse">
        <span className="button button-outline button-sm">Browse files</span>
        <input
          type="file"
          accept={ACCEPT}
          className="sr-only"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
      </label>
      <small>Up to 5 MB. Uploading proof sends this certification for review.</small>
    </div>
  );
}
