/** Plain-language formatting for Shift V1 ("Jan 6 – Jun 30", never ISO). */
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export const parseDay = (iso: string) => {
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number);
  return { y, m, d };
};

export function day(iso: string, withYear?: boolean) {
  const { y, m, d } = parseDay(iso);
  const showYear = withYear ?? y !== new Date().getFullYear();
  return `${MONTHS[m - 1]} ${d}${showYear ? `, ${y}` : ''}`;
}

export function range(start: string, end: string) {
  const a = parseDay(start);
  const b = parseDay(end);
  const thisYear = new Date().getFullYear();
  if (start.slice(0, 10) === end.slice(0, 10)) return day(start);
  if (a.y === b.y && a.y === thisYear) return `${day(start, false)} – ${day(end, false)}`;
  if (a.y === b.y) return `${day(start, false)} – ${day(end, true)}`;
  return `${day(start, true)} – ${day(end, true)}`;
}

/** Whole days between two ISO dates, inclusive of both ends. */
export function spanDays(start: string, end: string) {
  const a = Date.UTC(...ymd(start));
  const b = Date.UTC(...ymd(end));
  return Math.round((b - a) / 86400000) + 1;
}
const ymd = (iso: string): [number, number, number] => {
  const { y, m, d } = parseDay(iso);
  return [y, m - 1, d];
};

export function duration(start: string, end: string) {
  const days = spanDays(start, end);
  if (days < 14) return `${days} ${days === 1 ? 'day' : 'days'}`;
  if (days < 60) return `${Math.round(days / 7)} weeks`;
  const months = Math.round(days / 30.4);
  return `${months} ${months === 1 ? 'month' : 'months'}`;
}

export const dollars = (cents: number) =>
  new Intl.NumberFormat('en-CA', {
    style: 'currency',
    currency: 'CAD',
    maximumFractionDigits: cents % 100 ? 2 : 0,
  }).format(cents / 100);

export const payUnit: Record<string, string> = {
  hour: 'per hour',
  day: 'per day',
  fixed: 'fixed price',
};

export const todayIso = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(
    now.getDate(),
  ).padStart(2, '0')}`;
};

export const initials = (name: string) =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .map((n) => n[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();

export async function fileToBase64(file: File): Promise<string> {
  const url = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error('The file could not be read'));
    reader.readAsDataURL(file);
  });
  return url.slice(url.indexOf(',') + 1);
}
