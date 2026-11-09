// Lists photos in public/profiles into src/data/profile-photos.json (ASSET-1).
import { readdirSync, writeFileSync, existsSync } from 'node:fs';
import { join, parse } from 'node:path';

const root = join(import.meta.dirname, '..');
const dir = join(root, 'public', 'profiles');
const photos = {};
if (existsSync(dir)) {
  for (const file of readdirSync(dir).sort()) {
    const { name, ext } = parse(file);
    if (/^\.(jpe?g|png|webp)$/i.test(ext)) photos[name.toLowerCase()] = `/profiles/${file}`;
  }
}
writeFileSync(
  join(root, 'src', 'data', 'profile-photos.json'),
  JSON.stringify(photos, null, 2) + '\n',
);
console.log(`profile photos: ${Object.keys(photos).length} found`);
