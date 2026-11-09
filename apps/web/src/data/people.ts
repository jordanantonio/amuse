/**
 * Who appears in the demo and which photo they use (ASSET-1, ASSET-2).
 * `photo` is a file in public/profiles/ when one exists; otherwise the avatar is
 * generated locally from the name (ASSET-3). Photos are discovered at dev/build time
 * by scripts/profile-photos.mjs.
 */
import photos from './profile-photos.json';

export type Person = { id: string; name: string; role: string; photo: string | null };

const found = photos as Record<string, string>;
const photo = (...keys: string[]) => keys.map((k) => found[k]).find(Boolean) || null;

export const PEOPLE: Record<string, Person> = {
  'u-ilya': { id: 'u-ilya', name: 'Ilya Sukhanov', role: 'Worker', photo: photo('ilya', 'u-ilya') },
  'u-rahul': {
    id: 'u-rahul',
    name: 'Rahul Ghosh',
    role: 'Hiring manager, Prairie Harvest Foods',
    photo: photo('rahul', 'u-rahul'),
  },
  'u-jordan': {
    id: 'u-jordan',
    name: 'Jordan Antonio',
    role: 'Owner, Timberline Framing Crew',
    photo: photo('jordan', 'u-jordan'),
  },
};

/** Fictional testimonial authors on the landing page (LAND-3). */
export const TESTIMONIALS = [
  {
    id: 'testimonial-1',
    name: 'Marisol Vega',
    role: 'Forklift operator, Leduc',
    quote:
      'I used to juggle three group chats to find shifts. Now I open Shift with my coffee and the jobs that fit my certs are right there.',
    photo: photo('testimonial-1'),
  },
  {
    id: 'testimonial-2',
    name: 'Owen Pritchard',
    role: 'Plant manager, food processing',
    quote:
      'Checking forklift cards used to eat my morning. Now I can see who’s certified before I open a single application.',
    photo: photo('testimonial-2'),
  },
  {
    id: 'testimonial-3',
    name: 'Tanya Okafor',
    role: 'Owner, framing crew',
    quote:
      'We bid on crew jobs with our COR and insurance already attached. Fewer phone calls, more booked weeks.',
    photo: photo('testimonial-3'),
  },
];

/** Photo for any person id or name, if one was dropped into public/profiles/. */
export function photoFor(id?: string | null, name?: string | null): string | null {
  if (id && PEOPLE[id]?.photo) return PEOPLE[id].photo;
  const keys: string[] = [];
  if (id) keys.push(id.toLowerCase(), id.replace(/^u-/, '').toLowerCase());
  if (name) keys.push(name.split(' ')[0].toLowerCase(), name.toLowerCase().replace(/\s+/g, '-'));
  return photo(...keys);
}
