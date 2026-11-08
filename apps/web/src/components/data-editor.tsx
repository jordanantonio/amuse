'use client';
import { useEffect, useRef, useState } from 'react';
import { X } from 'lucide-react';
import { Button } from './ui/button';
export type Field = {
  name: string;
  label: string;
  type?: string;
  value?: string | number;
  required?: boolean;
  min?: number;
  max?: number;
  step?: number;
  options?: { value: string; label: string }[];
  help?: string;
};
export type EditorSpec = {
  title: string;
  description?: string;
  fields: Field[];
  save: (data: Record<string, string>) => Promise<void>;
};
export function DataEditor({ spec, close }: { spec: EditorSpec; close: () => void }) {
  const ref = useRef<HTMLDialogElement>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState('');
  useEffect(() => {
    ref.current?.showModal();
    return () => ref.current?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      className="editor-dialog"
      onCancel={(e) => {
        e.preventDefault();
        if (!busy) close();
      }}
    >
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError('');
          try {
            const form = new FormData(e.currentTarget);
            const values = Object.fromEntries(form) as Record<string, string>;
            for (const field of spec.fields) {
              if (field.type === 'multiselect')
                values[field.name] = form.getAll(field.name).join(', ');
            }
            await spec.save(values);
            close();
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <div className="editor-heading">
          <div>
            <h2>{spec.title}</h2>
            {spec.description && <p>{spec.description}</p>}
          </div>
          <button
            type="button"
            className="icon-button"
            aria-label="Close editor"
            disabled={busy}
            onClick={close}
          >
            <X size={20} />
          </button>
        </div>
        <div className="editor-fields">
          {spec.fields.map((f) => (
            <label key={f.name}>
              {f.label}
              {f.options ? (
                <select
                  name={f.name}
                  multiple={f.type === 'multiselect'}
                  defaultValue={
                    f.type === 'multiselect'
                      ? String(f.value || '')
                          .split(',')
                          .map((s) => s.trim())
                      : f.value
                  }
                  required={f.required}
                >
                  {f.options.map((o) => (
                    <option value={o.value} key={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              ) : f.type === 'textarea' ? (
                <textarea name={f.name} defaultValue={f.value} required={f.required} />
              ) : (
                <input
                  autoFocus={f === spec.fields[0]}
                  name={f.name}
                  type={f.type || 'text'}
                  defaultValue={f.value}
                  required={f.required}
                  min={f.min}
                  max={f.max}
                  step={f.step}
                />
              )}{' '}
              {f.help && <small>{f.help}</small>}
            </label>
          ))}
        </div>
        {error && (
          <div className="form-error" role="alert">
            {error}
          </div>
        )}
        <div className="editor-actions">
          <Button variant="outline" disabled={busy} onClick={close}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy}>
            {busy ? 'Saving…' : 'Save changes'}
          </Button>
        </div>
      </form>
    </dialog>
  );
}
