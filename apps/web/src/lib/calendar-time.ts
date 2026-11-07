export const defaultZone = 'America/Edmonton';
export function dateKey(value: string | Date, zone = defaultZone) {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: zone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(value));
}
export function addDays(date: string, n: number) {
  const d = new Date(date + 'T12:00:00Z');
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}
export function zonedInstant(date: string, time = '00:00', zone = defaultZone) {
  const [y, m, d] = date.split('-').map(Number),
    [h, min] = time.split(':').map(Number);
  const desired = Date.UTC(y, m - 1, d, h, min);
  let instant = desired;
  for (let i = 0; i < 4; i++) {
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone: zone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hourCycle: 'h23',
    }).formatToParts(new Date(instant));
    const values = Object.fromEntries(parts.map((p) => [p.type, p.value]));
    const actual = Date.UTC(
      +values.year,
      +values.month - 1,
      +values.day,
      +values.hour,
      +values.minute,
    );
    const delta = desired - actual;
    if (!delta) break;
    instant += delta;
  }
  return new Date(instant).toISOString();
}
export function localInput(value: string, zone = defaultZone) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: zone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(new Date(value));
  const p = Object.fromEntries(parts.map((x) => [x.type, x.value]));
  return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}`;
}
export function inputInstant(value: string, zone = defaultZone) {
  const [date, time] = value.split('T');
  return zonedInstant(date, time, zone);
}
export function intersect(start: string, end: string, date: string, zone = defaultZone) {
  const a = Math.max(Date.parse(start), Date.parse(zonedInstant(date, '00:00', zone))),
    b = Math.min(Date.parse(end), Date.parse(zonedInstant(addDays(date, 1), '00:00', zone)));
  return b > a
    ? { starts_at: new Date(a).toISOString(), ends_at: new Date(b).toISOString() }
    : null;
}
export function freeWindows(
  windows: { starts_at: string; ends_at: string }[],
  busy: { starts_at: string; ends_at: string }[],
) {
  let free = windows.map((w) => [Date.parse(w.starts_at), Date.parse(w.ends_at)]);
  for (const b of busy) {
    const a = Date.parse(b.starts_at),
      z = Date.parse(b.ends_at);
    free = free.flatMap(([s, e]) =>
      z <= s || a >= e
        ? [[s, e]]
        : [
            [s, Math.min(e, a)],
            [Math.max(s, z), e],
          ].filter(([x, y]) => y > x),
    );
  }
  return free.map(([s, e]) => ({
    starts_at: new Date(s).toISOString(),
    ends_at: new Date(e).toISOString(),
  }));
}
