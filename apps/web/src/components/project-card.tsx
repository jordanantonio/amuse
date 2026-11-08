import { ChevronRight } from 'lucide-react';
import type { Project } from '@/lib/types';
import { shortDate } from '@/lib/display';

export function ProjectRow({ project, open }: { project: Project; open: () => void }) {
  const total = project.tasks.length;
  const staffed = project.tasks.filter((t) => t.confirmed_count >= t.crew_size).length;
  return (
    <button className="project-row" onClick={open}>
      <span className="project-swatch" style={{ background: project.color }} />
      <span className="project-row-main">
        <strong>{project.name}</strong>
        <small>{project.client}</small>
      </span>
      <span className="project-row-coverage">
        <span className="progress-track" aria-hidden="true">
          <span style={{ width: `${total ? (staffed / total) * 100 : 0}%` }} />
        </span>
        <small>
          {staffed} of {total} tasks staffed
        </small>
      </span>
      <span className="project-row-due">Due {shortDate(project.deadline)}</span>
      <ChevronRight size={16} className="project-row-open" />
    </button>
  );
}
