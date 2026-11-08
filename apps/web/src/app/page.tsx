import { AuthGate } from '@/components/auth-gate';
export const dynamic = 'force-dynamic';
export default function Home() {
  return (
    <AuthGate
      demo={process.env.SHIFT_DEMO_MODE === 'true' && process.env.SHIFT_ENVIRONMENT === 'local'}
    />
  );
}
