import { AdaptiveWorkspace } from '@/components/adaptive-workspace';
import { AuthGate } from '@/components/auth-gate';
export default function Home() {
  return (
    <AuthGate>
      <AdaptiveWorkspace />
    </AuthGate>
  );
}
