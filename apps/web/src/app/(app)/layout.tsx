'use client';
import { RequireSession } from '@/components/v1/session';
import { AppShell } from '@/components/v1/app-shell';

export default function SignedInLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireSession fallback={<div className="shell-loading" aria-busy="true" />}>
      <AppShell>{children}</AppShell>
    </RequireSession>
  );
}
