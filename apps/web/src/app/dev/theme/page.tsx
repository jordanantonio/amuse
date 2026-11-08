import type { Metadata } from 'next';
import {
  BadgeCheck,
  Clock3,
  House,
  BriefcaseBusiness,
  CalendarDays,
  UserRound,
} from 'lucide-react';

export const metadata: Metadata = { title: 'Theme preview — Shift' };

/**
 * SHELL-1 preview: two blueprint blues derived from Oxford Navy (#003566) in OKLCH.
 * The app shell uses the deeper option via --app-bg; the profile uses the vivid one
 * (PROFILE-7). Ratios measured with the WCAG relative-luminance formula.
 */
const OPTIONS = [
  {
    key: 'deep',
    name: 'Deeper blueprint',
    hex: '#003c76',
    note: 'Oxford Navy, L +0.03, chroma ×1.15. Used for the app background.',
    ratios: [
      ['White text on blue', '11.0 : 1'],
      ['Gold #ffd60a on blue', '7.8 : 1'],
    ],
  },
  {
    key: 'vivid',
    name: 'Vibrant blueprint',
    hex: '#0052b1',
    note: 'Oxford Navy, L +0.12, chroma ×1.75. Used on the worker profile.',
    ratios: [
      ['White text on blue', '7.4 : 1'],
      ['Gold #ffd60a on blue', '5.2 : 1'],
    ],
  },
];
const CARD_RATIOS = [
  ['Ink #001d3d on card #f5f8fc', '15.9 : 1'],
  ['Secondary #3d5a7a on card', '6.7 : 1'],
  ['Muted #52708f on card', '4.8 : 1'],
  ['Amber text #8a5a00 on card', '5.6 : 1'],
];

export default function ThemePreview() {
  return (
    <main className="theme-preview">
      <h1>Blueprint blue: two options</h1>
      <p>
        Both are derived from the palette’s Oxford Navy. Cards stay light on top so content is easy
        to read. Every pair below meets WCAG AA.
      </p>
      <div className="theme-options">
        {OPTIONS.map((o) => (
          <section key={o.key} className="theme-option" aria-label={o.name}>
            <div className="theme-mock" style={{ background: o.hex }}>
              <nav className="theme-mock-nav" aria-hidden="true">
                <strong>
                  shift<span>.</span>
                </strong>
                <span className="on">
                  <House size={16} /> Home
                </span>
                <span>
                  <BriefcaseBusiness size={16} /> Work
                </span>
                <span>
                  <CalendarDays size={16} /> Schedule
                </span>
                <span>
                  <UserRound size={16} /> Profile
                </span>
              </nav>
              <div className="theme-mock-body">
                <p className="theme-mock-title">Good morning, Ilya</p>
                <div className="theme-mock-bright">1 new contract fits you since yesterday</div>
                <div className="theme-mock-card">
                  <strong>General Labourer — Sanitation Crew</strong>
                  <span>Prairie Harvest Foods · Leduc, 9 km away</span>
                  <span className="chip ok">
                    <BadgeCheck size={14} /> Verified
                  </span>
                  <span className="chip warn">
                    <Clock3 size={14} /> Pending review
                  </span>
                  <button type="button">Apply</button>
                </div>
              </div>
            </div>
            <h2>
              {o.name} <code>{o.hex}</code>
            </h2>
            <p>{o.note}</p>
            <ul>
              {o.ratios.map(([k, v]) => (
                <li key={k}>
                  {k}: <strong>{v}</strong>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
      <h2>Light cards</h2>
      <ul>
        {CARD_RATIOS.map(([k, v]) => (
          <li key={k}>
            {k}: <strong>{v}</strong>
          </li>
        ))}
      </ul>
    </main>
  );
}
