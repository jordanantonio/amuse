import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { PublicHome } from '@/components/public-home';
import './public-home.css';

const inter = Inter({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-public',
});
export const metadata: Metadata = {
  title: 'SHIFT — Find skilled trades work across Alberta',
  description:
    'Browse Alberta contracts with pay and dates up front. Find work in electrical, welding, carpentry, manufacturing and more.',
};

export default function Landing() {
  return (
    <div className={inter.variable}>
      <PublicHome />
    </div>
  );
}
