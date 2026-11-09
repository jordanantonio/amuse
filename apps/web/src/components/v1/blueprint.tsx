'use client';
import { useEffect, useId, useRef } from 'react';

/**
 * Living blueprint grid (LAND-4 / WOW-1): pure SVG + CSS, no image files.
 * Minor grid, heavier major lines every 5 cells, faint crosshairs and dimension marks,
 * a slow parallax drift and a highlight sweep every ~8 s. Motion is disabled under
 * prefers-reduced-motion (see .blueprint rules in v1.css).
 */
export function Blueprint({
  parallax = false,
  className = '',
}: {
  parallax?: boolean;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const id = useId().replace(/:/g, '');
  useEffect(() => {
    const el = ref.current;
    if (!parallax || !el || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    let frame = 0;
    let mx = 0;
    let my = 0;
    const apply = () => {
      frame = 0;
      const sy = window.scrollY * 0.04;
      el.style.setProperty('--drift-x', `${(mx * 10).toFixed(2)}px`);
      el.style.setProperty('--drift-y', `${(my * 10 - sy).toFixed(2)}px`);
    };
    const queue = () => {
      if (!frame) frame = requestAnimationFrame(apply);
    };
    const move = (e: PointerEvent) => {
      mx = e.clientX / window.innerWidth - 0.5;
      my = e.clientY / window.innerHeight - 0.5;
      queue();
    };
    window.addEventListener('pointermove', move, { passive: true });
    window.addEventListener('scroll', queue, { passive: true });
    return () => {
      window.removeEventListener('pointermove', move);
      window.removeEventListener('scroll', queue);
      cancelAnimationFrame(frame);
    };
  }, [parallax]);
  return (
    <div ref={ref} className={`blueprint ${className}`} aria-hidden="true">
      <svg className="blueprint-grid" width="100%" height="100%">
        <defs>
          <pattern id={`minor-${id}`} width="24" height="24" patternUnits="userSpaceOnUse">
            <path d="M24 0H0V24" fill="none" stroke="var(--bp-minor)" strokeWidth="1" />
          </pattern>
          <pattern id={`major-${id}`} width="120" height="120" patternUnits="userSpaceOnUse">
            <rect width="120" height="120" fill={`url(#minor-${id})`} />
            <path d="M120 0H0V120" fill="none" stroke="var(--bp-major)" strokeWidth="1.5" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill={`url(#major-${id})`} />
      </svg>
      <svg className="blueprint-marks" viewBox="0 0 1200 800" preserveAspectRatio="xMidYMid slice">
        <g stroke="var(--bp-mark)" strokeWidth="1.2" fill="none">
          {[
            [240, 240],
            [960, 120],
            [840, 600],
            [120, 600],
          ].map(([x, y]) => (
            <g key={`${x}-${y}`}>
              <circle cx={x} cy={y} r="9" />
              <path d={`M${x - 16} ${y}H${x + 16}M${x} ${y - 16}V${y + 16}`} />
            </g>
          ))}
          <path d="M240 690H720M240 682V698M720 682V698" />
          <path d="M1080 240V600M1072 240H1088M1072 600H1088" />
          <path d="M360 120H600M360 112V128M600 112V128" strokeDasharray="4 6" />
        </g>
        <g fill="var(--bp-mark)" fontSize="13" fontFamily="var(--font-head)" letterSpacing="1">
          <text x="466" y="680">
            4 800
          </text>
          <text x="1092" y="424" transform="rotate(90 1092 424)">
            3 600
          </text>
          <text x="452" y="110">
            GRID B
          </text>
        </g>
      </svg>
      <div className="blueprint-sweep" />
    </div>
  );
}
