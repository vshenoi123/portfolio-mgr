import { IBM_Plex_Mono, IBM_Plex_Sans } from 'next/font/google';
import Sidebar from '@/components/shared/Sidebar';
import './globals.css';

const plexSans = IBM_Plex_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-plex-sans',
});

const plexMono = IBM_Plex_Mono({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-plex-mono',
});

export const metadata = {
  title: 'Portfolio Manager',
  description: 'Terminal-green dark theme portfolio management dashboard',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${plexSans.variable} ${plexMono.variable}`}>
      <body className="font-sans antialiased">
        <div className="flex h-screen overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-auto p-6 bg-terminal-bg">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
