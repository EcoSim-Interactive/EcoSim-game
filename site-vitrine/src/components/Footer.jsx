import React from 'react';
import GithubIcon from './GithubIcon';

export default function Footer() {
  return (
    <footer className="border-t border-slate-200 dark:border-slate-900 bg-slate-50 dark:bg-slate-950/60 py-12 px-6 md:px-12 transition-colors">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-emerald-500 to-green-600 flex items-center justify-center">
            <span className="font-extrabold text-white text-xs">ES</span>
          </div>
          <span className="font-bold text-slate-900 dark:text-white">EcoSim Interactive</span>
        </div>

        <p className="text-xs text-slate-400 dark:text-slate-550 font-mono">
          Projet ETNA GPE 2026. Fiche Projet J-7. Tous droits réservés.
        </p>

        <div className="flex gap-4">
          <a 
            href="https://github.com/EcoSim-Interactive/EcoSim-game" 
            target="_blank" 
            rel="noreferrer"
            className="text-slate-400 hover:text-slate-650 dark:text-slate-500 dark:hover:text-white transition-colors"
          >
            <GithubIcon className="w-5 h-5" />
          </a>
        </div>
      </div>
    </footer>
  );
}
