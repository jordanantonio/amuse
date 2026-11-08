import { redirect } from 'next/navigation';

/** CREW-6: the slot-first crew planner replaces the old text-wall view. */
export default function PlannerRedirect() {
  redirect('/crew');
}
