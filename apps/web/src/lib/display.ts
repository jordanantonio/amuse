const zone = 'America/Edmonton';
export const clock = (v: string) =>
  new Intl.DateTimeFormat('en-CA', { hour: 'numeric', minute: '2-digit', timeZone: zone }).format(
    new Date(v),
  );
export const shortDate = (v: string) =>
  new Intl.DateTimeFormat('en-CA', { month: 'short', day: 'numeric', timeZone: zone }).format(
    new Date(v),
  );
export const day = (v: string) =>
  new Intl.DateTimeFormat('en-CA', { day: 'numeric', timeZone: zone }).format(new Date(v));
export const money = (v: number) =>
  new Intl.NumberFormat('en-CA', {
    style: 'currency',
    currency: 'CAD',
    maximumFractionDigits: 0,
  }).format(v / 100);
export const initials = (name: string) =>
  name
    .split(' ')
    .map((n) => n[0])
    .slice(0, 2)
    .join('');

export const localDate = (v: string) =>
  new Intl.DateTimeFormat('en-CA', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    timeZone: zone,
  }).format(new Date(v));
