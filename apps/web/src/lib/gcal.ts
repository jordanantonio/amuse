/** Google Calendar links that work without OAuth (SCHED-1, SCHED-2). */
const DAY = 86400000;
const nextDay = (iso: string) =>
  new Date(Date.parse(iso.slice(0, 10) + 'T00:00:00Z') + DAY).toISOString().slice(0, 10);
const compact = (iso: string) => iso.slice(0, 10).replaceAll('-', '');

/** Opens Google Calendar on the week that contains `iso`. */
export function googleWeekUrl(iso: string) {
  const [y, m, d] = iso.slice(0, 10).split('-');
  return `https://calendar.google.com/calendar/r/week/${y}/${m}/${d}`;
}

/** Google's event template: an all-day event from `start` to `end` (both inclusive). */
export function googleEventUrl(event: {
  title: string;
  start: string;
  end: string;
  details?: string;
  location?: string;
}) {
  const q = new URLSearchParams({
    action: 'TEMPLATE',
    text: event.title,
    dates: `${compact(event.start)}/${compact(nextDay(event.end))}`,
    details: event.details || '',
    location: event.location || '',
  });
  return `https://calendar.google.com/calendar/render?${q.toString()}`;
}
