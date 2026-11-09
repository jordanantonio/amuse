'use client';
import { useMemo } from 'react';
import { createAvatar } from '@dicebear/core';
import { notionists } from '@dicebear/collection';
import {
  Building2,
  Factory,
  Fuel,
  HardHat,
  House,
  Users,
  Warehouse,
  Wheat,
  type LucideIcon,
} from 'lucide-react';
import { photoFor } from '@/data/people';

/* Palette-derived avatar backgrounds (Golden Twilight). */
const AVATAR_BG = ['ffd60a', 'ffc300', 'cfe0f2', 'a8c5e6', 'f5e6b3'];
const cache = new Map<string, string>();

function generated(seed: string): string {
  let uri = cache.get(seed);
  if (!uri) {
    uri = createAvatar(notionists, { seed, backgroundColor: AVATAR_BG, radius: 50 }).toDataUri();
    cache.set(seed, uri);
  }
  return uri;
}

/** A person's photo when one exists in public/profiles/, else a stable generated face. */
export function PersonAvatar({
  id,
  name,
  size = 40,
  className = '',
  ring = false,
}: {
  id?: string | null;
  name: string;
  size?: number;
  className?: string;
  ring?: boolean;
}) {
  const src = useMemo(() => photoFor(id, name) || generated(name), [id, name]);
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt=""
      width={size}
      height={size}
      className={`person-avatar ${ring ? 'ring' : ''} ${className}`}
      style={{ width: size, height: size }}
      loading="lazy"
      decoding="async"
    />
  );
}

const INDUSTRY_ICON: Record<string, LucideIcon> = {
  'Residential construction': House,
  'Commercial construction': Building2,
  'Industrial construction': HardHat,
  Manufacturing: Factory,
  'Food processing': Wheat,
  'Oil and gas': Fuel,
  'Warehousing and logistics': Warehouse,
  Staffing: Users,
};
const BADGE_COLORS = [
  { bg: '#ffc300', fg: '#000814' },
  { bg: '#003566', fg: '#ffd60a' },
  { bg: '#ffd60a', fg: '#001d3d' },
  { bg: '#1d4f86', fg: '#ffffff' },
];

const hash = (s: string) => [...s].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 7);

/** ASSET-4: one company badge everywhere a company appears. */
export function CompanyBadge({
  name,
  industry,
  size = 40,
  className = '',
}: {
  name: string;
  industry?: string | null;
  size?: number;
  className?: string;
}) {
  const Icon = (industry && INDUSTRY_ICON[industry]) || Building2;
  const color = BADGE_COLORS[hash(name) % BADGE_COLORS.length];
  const letters = name
    .split(/\s+/)
    .filter((w) => /^[A-Za-z]/.test(w))
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join('');
  return (
    <span
      className={`company-badge ${className}`}
      style={{ width: size, height: size, background: color.bg, color: color.fg }}
      role="img"
      aria-label={`${name} logo`}
    >
      <Icon size={Math.round(size * 0.36)} aria-hidden="true" />
      <span style={{ fontSize: Math.max(10, Math.round(size * 0.26)) }}>{letters}</span>
    </span>
  );
}
