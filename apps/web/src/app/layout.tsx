import type { Metadata } from 'next';
import { Barlow, Barlow_Semi_Condensed } from 'next/font/google';
import './globals.css';

const body = Barlow({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-body',
});
const display = Barlow_Semi_Condensed({
  subsets: ['latin'],
  weight: ['500', '600'],
  variable: '--font-display',
});

export const metadata: Metadata = {
  title: 'SHIFT — Workforce, in sync.',
  description:
    'Workforce scheduling, project talent, and constraint-based planning. SHIFT local demonstration.',
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${body.variable} ${display.variable}`}>
      <body>{children}</body>
    </html>
  );
}
