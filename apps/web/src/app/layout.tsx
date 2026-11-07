import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = {
  title: 'SHIFT — Workforce, in sync.',
  description:
    'Workforce scheduling, project talent, and constraint-based planning. SHIFT local demonstration.',
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
