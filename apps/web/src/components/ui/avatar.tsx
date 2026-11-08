import type { Worker } from '@/lib/types';
import { initials } from '@/lib/display';
export function Avatar({
  worker,
  small = false,
}: {
  worker: Pick<Worker, 'name' | 'color'>;
  small?: boolean;
}) {
  return (
    <span
      className={`avatar ${small ? 'avatar-small' : ''}`}
      style={{ background: worker.color + '28', color: worker.color }}
    >
      {initials(worker.name)}
    </span>
  );
}
