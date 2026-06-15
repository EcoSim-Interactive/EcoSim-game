import React, { useState } from 'react';
import ecosimScreenshot from '../assets/ecosim_screenshot.png';
import ecosimDashboard from '../assets/ecosim_dashboard.png';

export default function Screenshots() {
  const [activeScreenTab, setActiveScreenTab] = useState('main');

  return (
    <section id="screens" className="space-y-10">
      <div className="text-center space-y-3">
        <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">Interface Visuelle</span>
        <h2 className="text-3xl font-bold text-slate-900 dark:text-white">Captures d'Écran du Logiciel</h2>
        <p className="text-slate-500 dark:text-slate-400 max-w-xl mx-auto">
          Découvrez l'interface interactive du simulateur 3D et ses outils de statistiques.
        </p>
      </div>

      {/* Toggle buttons for screens */}
      <div className="flex justify-center gap-3">
        <button
          onClick={() => setActiveScreenTab('main')}
          className={`px-5 py-2.5 rounded-xl border text-sm font-semibold transition-all cursor-pointer ${
            activeScreenTab === 'main'
              ? 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-500 text-emerald-700 dark:text-emerald-400'
              : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
          }`}
        >
          Vue Principale (Simulation)
        </button>
        <button
          onClick={() => setActiveScreenTab('dashboard')}
          className={`px-5 py-2.5 rounded-xl border text-sm font-semibold transition-all cursor-pointer ${
            activeScreenTab === 'dashboard'
              ? 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-500 text-emerald-700 dark:text-emerald-400'
              : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
          }`}
        >
          Tableau de Bord Analytique
        </button>
      </div>

      {/* Screenshot display with elegant frame */}
      <div className="max-w-4xl mx-auto rounded-[2rem] bg-slate-100 dark:bg-slate-900/50 p-2.5 md:p-4 border border-slate-200/80 dark:border-slate-800 shadow-xl transition-all">
        <div className="rounded-[1.5rem] overflow-hidden border border-slate-200 dark:border-slate-800 relative bg-slate-950 aspect-[16/10]">
          {activeScreenTab === 'main' ? (
            <img 
              src={ecosimScreenshot} 
              alt="Vue 3D de la simulation d'EcoSim" 
              className="w-full h-full object-cover"
            />
          ) : (
            <img 
              src={ecosimDashboard} 
              alt="Tableau de bord statistique d'EcoSim" 
              className="w-full h-full object-cover"
            />
          )}
        </div>
        
        <div className="p-6 text-left space-y-2">
          <h3 className="font-bold text-lg text-slate-900 dark:text-white">
            {activeScreenTab === 'main' ? 'L\'Écosystème Interactif en 3D' : 'Le Tableau de Suivi Scientifique'}
          </h3>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {activeScreenTab === 'main' 
              ? 'Observez en direct les déplacements des animaux, la pousse de l\'herbe et l\'accès aux points d\'eau. Vous pouvez déplacer la caméra librement et suivre les trajectoires individuelles de chaque sujet d\'étude.'
              : 'Analysez l\'évolution de la biomasse et les cycles proies-prédateurs à l\'aide de courbes et de statistiques précises. Un bon moyen de comprendre comment les variations de ressources impactent la vie.'
            }
          </p>
        </div>
      </div>
    </section>
  );
}
