import { ArrowUpRight, Building2, Clock3 } from 'lucide-react';
import type { Assignment, Project, Worker } from '@/lib/types';
import { shortDate } from '@/lib/display';
import { Avatar } from '@/components/ui/avatar';
export function ProjectCard({
  project,
  workers,
  assignments,
  open,
}: {
  project: Project;
  workers: Worker[];
  assignments: Assignment[];
  open: () => void;
}) {
  const staffed = project.tasks.filter((t) => t.confirmed_count >= t.crew_size).length;
  const team = workers.filter((w) =>
    assignments.some((a) => a.project_id === project.id && a.worker_id === w.id),
  );
  return (
    <button className="panel project-card" onClick={open}>
      <div className="project-card-top">
        <span
          className="project-emblem"
          style={{ background: project.color + '22', color: project.color }}
        >
          <Building2 size={21} />
        </span>
        <span className="badge neutral">{project.tasks.length} tasks</span>
        <ArrowUpRight size={16} className="project-open" />
      </div>
      <h3>{project.name}</h3>
      <p>{project.client}</p>
      <div className="project-progress-label">
        <span>Confirmed task coverage</span>
        <strong>
          {staffed}/{project.tasks.length}
        </strong>
      </div>
      <div className="progress-track">
        <span
          style={{
            width: `${project.tasks.length ? (staffed / project.tasks.length) * 100 : 0}%`,
            background: project.color,
          }}
        />
      </div>
      <div className="project-card-bottom">
        <div className="avatar-stack">
          {team.slice(0, 3).map((w) => (
            <Avatar key={w.id} worker={w} small />
          ))}
          {!team.length && <span className="subtle">Team unassigned</span>}
        </div>
        <span>
          <Clock3 size={12} />
          {shortDate(project.deadline)}
        </span>
      </div>
    </button>
  );
}
