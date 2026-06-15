import React from 'react';
import { Download, Sun, Moon } from 'lucide-react';

export default function Navbar({ isDarkMode, onToggleTheme }) {
  return (
    <header className="sticky top-0 z-50 bg-[#fcfbfa]/85 dark:bg-[#070b13]/85 backdrop-blur-md border-b border-slate-200/60 dark:border-slate-800/40 py-4 px-6 md:px-12 flex justify-between items-center transition-colors">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-emerald-500 to-green-600 flex items-center justify-center shadow-lg shadow-emerald-500/10">
          <span className="font-extrabold text-white text-lg tracking-wide">ES</span>
        </div>
        <div>
          <h2 className="font-bold text-slate-900 dark:text-white tracking-tight text-lg leading-tight m-0">EcoSim</h2>
          <p className="text-emerald-600 dark:text-emerald-400 text-xs font-semibold tracking-wide m-0">Interactive</p>
        </div>
      </div>

      <nav className="hidden md:flex items-center gap-8 text-[15px] font-medium">
        <a href="#screens" className="text-slate-600 hover:text-emerald-600 dark:text-slate-300 dark:hover:text-emerald-400 transition-colors">Aperçu</a>
        <a href="#architecture" className="text-slate-600 hover:text-emerald-600 dark:text-slate-300 dark:hover:text-emerald-400 transition-colors">Comment ça marche</a>
        <a href="#changelog" className="text-slate-600 hover:text-emerald-600 dark:text-slate-300 dark:hover:text-emerald-400 transition-colors">Nouveautés</a>
        <a href="#team" className="text-slate-600 hover:text-emerald-600 dark:text-slate-300 dark:hover:text-emerald-400 transition-colors">L'Équipe</a>
      </nav>

      <div className="flex items-center gap-4">
        {/* Light/Dark mode switcher */}
        <button 
          id="theme-toggle"
          onClick={onToggleTheme}
          className="p-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-900 dark:hover:bg-slate-800 border border-slate-200/60 dark:border-slate-800 text-slate-600 dark:text-slate-400 transition-all active:scale-95"
          aria-label="Changer de thème"
        >
          {isDarkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-700" />}
        </button>

        <a 
          href="https://github.com/ThomasBoulard/EcoSim-Interactive/releases"
          target="_blank"
          rel="noreferrer"
          id="nav-download-github"
          className="hidden sm:flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-500 dark:hover:bg-emerald-400 text-white dark:text-slate-950 font-semibold text-sm py-2 px-4.5 rounded-xl transition-all shadow-md shadow-emerald-600/10 active:scale-95"
        >
          <Download className="w-4 h-4" />
          <span>Télécharger</span>
        </a>
      </div>
    </header>
  );
}
