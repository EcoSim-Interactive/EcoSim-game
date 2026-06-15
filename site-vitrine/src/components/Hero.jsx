import React from 'react';
import { Download, Heart } from 'lucide-react';
import ecosimScreenshot from '../assets/ecosim_screenshot.png';

export default function Hero() {
  return (
    <section id="hero" className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center pt-8">
      <div className="lg:col-span-7 space-y-6 text-left">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 dark:text-emerald-400 text-xs font-semibold">
          <Heart className="w-3.5 h-3.5 fill-current" />
          <span>Observer et comprendre la nature</span>
        </div>

        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-slate-900 dark:text-white tracking-tight leading-[1.15]">
          Explorez la vie dans notre<br />
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-emerald-600 to-green-500 dark:from-emerald-400 dark:to-green-300">
            Simulateur Écologique
          </span>
        </h1>

        <p className="text-lg text-slate-600 dark:text-slate-300 leading-relaxed font-light">
          Découvrez les secrets de l'équilibre naturel. <strong>EcoSim Interactive</strong> modélise les comportements d'animaux virtuels au sein d'une forêt en 3D. Observez comment les populations de lapins et de loups évoluent, s'alimentent et interagissent avec leur environnement en temps réel.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 pt-4">
          <a 
            href="https://github.com/ThomasBoulard/EcoSim-Interactive/releases"
            target="_blank"
            rel="noreferrer"
            id="hero-download-btn"
            className="flex items-center justify-center gap-3 bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-500 hover:to-green-500 text-white font-bold py-4 px-8 rounded-2xl transition-all duration-300 shadow-lg shadow-emerald-600/10 active:scale-95 text-base"
          >
            <Download className="w-5 h-5" />
            <span>Télécharger le simulateur (GitHub)</span>
          </a>
        </div>

        <div className="flex items-center gap-4 text-xs font-medium text-slate-500 dark:text-slate-400">
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            <span>Gratuit & Open Source</span>
          </div>
          <span>•</span>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            <span>Facile à utiliser</span>
          </div>
        </div>
      </div>

      {/* Quick Hero image representation */}
      <div className="lg:col-span-5 flex justify-center">
        <div className="relative group w-full max-w-[420px] aspect-[4/3] rounded-3xl overflow-hidden shadow-2xl border border-slate-200/80 dark:border-slate-800/80">
          <img 
            src={ecosimScreenshot} 
            alt="Aperçu d'EcoSim Interactive" 
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-slate-950/80 via-transparent to-transparent flex items-end p-6">
            <div className="text-left">
              <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-widest block">Rendu 3D temps réel</span>
              <span className="text-white font-bold text-base">La clairière et ses espèces vivantes</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
