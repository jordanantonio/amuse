'use client';
import { useEffect, useRef } from 'react';
import {
  BadgeCheck,
  Clock3,
  CircleDashed,
  CircleX,
  Ban,
  TriangleAlert,
  CircleCheck,
  CircleMinus,
  X,
  type LucideIcon,
} from 'lucide-react';

/** Status vocabulary (Section 13): colour + icon + word, never colour alone. */
export type Tone = 'ok' | 'warn' | 'bad' | 'muted';
const STATUS: Record<string, { tone: Tone; icon: LucideIcon; label: string }> = {
  verified: { tone: 'ok', icon: BadgeCheck, label: 'Verified' },
  pending: { tone: 'warn', icon: Clock3, label: 'Pending review' },
  self_reported: { tone: 'muted', icon: CircleDashed, label: 'Self-reported' },
  expired: { tone: 'bad', icon: CircleX, label: 'Expired' },
  rejected: { tone: 'bad', icon: Ban, label: 'Rejected' },
  eligible: { tone: 'ok', icon: CircleCheck, label: 'Eligible' },
  missing: { tone: 'bad', icon: CircleX, label: 'Missing' },
  conflict: { tone: 'bad', icon: TriangleAlert, label: 'Conflict' },
  closed: { tone: 'muted', icon: CircleMinus, label: 'Closed' },
};

export function StatusChip({
  status,
  label,
  tone,
  icon,
}: {
  status?: string;
  label?: string;
  tone?: Tone;
  icon?: LucideIcon;
}) {
  const known = status ? STATUS[status] : undefined;
  const Icon = icon || known?.icon || CircleDashed;
  return (
    <span className={`status-chip ${tone || known?.tone || 'muted'}`}>
      <Icon size={15} aria-hidden="true" />
      {label || known?.label || status}
    </span>
  );
}

export function ExpiryChip({ days }: { days: number }) {
  return (
    <StatusChip
      tone="warn"
      icon={TriangleAlert}
      label={days === 0 ? 'Expires today' : `Expires in ${days} ${days === 1 ? 'day' : 'days'}`}
    />
  );
}

export function Modal({
  title,
  description,
  onClose,
  children,
  busy = false,
}: {
  title: string;
  description?: string;
  onClose: () => void;
  children: React.ReactNode;
  busy?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    dialog?.showModal();
    return () => dialog?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      className="editor-dialog v1-dialog"
      aria-label={title}
      onCancel={(e) => {
        e.preventDefault();
        if (!busy) onClose();
      }}
    >
      <div className="editor-heading">
        <div>
          <h2>{title}</h2>
          {description && <p>{description}</p>}
        </div>
        <button
          type="button"
          className="icon-button tap"
          aria-label="Close"
          disabled={busy}
          onClick={onClose}
        >
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  );
}

export function EmptyState({
  title,
  children,
  action,
}: {
  title: string;
  children?: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="v1-empty">
      <p className="v1-empty-title">{title}</p>
      {children && <p>{children}</p>}
      {action}
    </div>
  );
}

export function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="skeleton-stack" aria-busy="true" aria-label="Loading">
      {Array.from({ length: lines }, (_, i) => (
        <div key={i} className="skeleton-block" />
      ))}
    </div>
  );
}

export function ErrorNote({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <div className="v1-inline-error" role="alert">
      {message}
      {retry && (
        <button className="text-button" onClick={retry}>
          Try again
        </button>
      )}
    </div>
  );
}
