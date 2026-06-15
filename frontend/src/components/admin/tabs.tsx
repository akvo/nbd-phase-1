'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const tabItems = [
  { name: 'Data', href: '/admin/data' },
  { name: 'User management', href: '/admin/users' },
  { name: 'Site management', href: '/admin/sites' },
];

export default function Tabs() {
  const pathname = usePathname();

  return (
    <div className="flex border border-slate-200 rounded-lg p-0.5 bg-slate-100/50 w-fit">
      {tabItems.map((tab) => {
        const isActive = pathname === tab.href;
        return (
          <Link
            key={tab.name}
            href={tab.href}
            data-active={isActive ? 'true' : undefined}
            className={`px-4 py-1.5 rounded-md text-xs font-semibold transition-colors ${
              isActive
                ? 'bg-slate-200 text-slate-800 shadow-sm'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            {tab.name}
          </Link>
        );
      })}
    </div>
  );
}
