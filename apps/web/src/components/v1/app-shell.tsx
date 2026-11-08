'use client';
import Link from 'next/link';
import { LogOut } from 'lucide-react';
import { useSession } from './session';

export function AppShell({ children }: { children: React.ReactNode }) {
  const { me, signOut } = useSession();
  return (
    <div className="v1-shell">
      <header className="v1-header">
        <Link href="/home" className="v1-wordmark">
          shift<span>.</span>
        </Link>
        <div className="v1-header-right">
          <span>{me.organization?.name || me.user.full_name}</span>
          <button className="icon-button" aria-label="Sign out" onClick={() => void signOut()}>
            <LogOut size={18} />
          </button>
        </div>
      </header>
      <main className="v1-main">{children}</main>
    </div>
  );
}
