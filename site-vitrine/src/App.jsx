import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import Hero from './components/Hero';
import Screenshots from './components/Screenshots';
import Architecture from './components/Architecture';
import Changelog from './components/Changelog';
import Team from './components/Team';
import Footer from './components/Footer';

export default function App() {
  const [isDarkMode, setIsDarkMode] = useState(false);

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);

  return (
    <div className="min-h-screen transition-colors duration-300 bg-[#fcfbfa] text-slate-800 dark:bg-[#070b13] dark:text-slate-200 relative overflow-hidden">
      {/* Nature ambient light gradients */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full ambient-forest pointer-events-none z-0"></div>
      <div className="absolute bottom-[-15%] right-[-10%] w-[60%] h-[60%] rounded-full ambient-warm pointer-events-none z-0"></div>

      <Navbar isDarkMode={isDarkMode} onToggleTheme={() => setIsDarkMode(!isDarkMode)} />

      <main className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 space-y-32">
        <Hero />
        <Screenshots />
        <Architecture />
        <Changelog />
        <Team />
      </main>

      <Footer />
    </div>
  );
}
