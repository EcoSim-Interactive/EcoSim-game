import React from 'react';
import { Download, ChevronRight, CheckCircle } from 'lucide-react';
import GithubIcon from './GithubIcon';

const DISCOVER_UPDATES = [
  { version: 'v1.0.0', title: 'Version finale stable', date: 'Juin 2026', details: 'Lancement public avec simulation optimisée des plantes et animaux.' },
  { version: 'v0.9.0', title: 'Amélioration de l\'intelligence animale', date: 'Mai 2026', details: 'Les hyènes chassent désormais en groupe et les gazelles fuient de manière coopérative.' },
  { version: 'v0.8.0', title: 'Rendu graphique 3D enrichi', date: 'Avril 2026', details: 'Nouveaux arbres en basse résolution (low-poly), effets météo et cycle jour/nuit.' }
];

export default function Changelog() {
  return (
    <section id="changelog" className="space-y-12">
      
      {/* Downloads / Github CTA integrated inside Changelog area */}
      <div id="download-box" className="p-8 md:p-12 rounded-[2.5rem] bg-gradient-to-br from-emerald-50 dark:from-emerald-950/20 to-slate-50 dark:to-slate-900/40 border border-slate-200 dark:border-slate-800 relative overflow-hidden shadow-sm">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
          <div className="lg:col-span-8 space-y-6 text-left">
            <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400 font-mono tracking-widest">INSTALLATION RAPIDE</span>
            <h2 className="text-3xl font-extrabold text-slate-900 dark:text-white">Prêt à observer votre écosystème ?</h2>
            <p className="text-slate-600 dark:text-slate-300 leading-relaxed font-light text-base">
              Téléchargez l'application complète directement depuis notre espace de publication GitHub. Le fichier contient tout le nécessaire : le moteur écologique, le visualiseur 3D et le lanceur unifié. Double-cliquez simplement sur l'exécutable pour démarrer l'aventure.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 items-center pt-2">
              <a 
                href="https://github.com/EcoSim-Interactive/EcoSim-game/releases/latest/download/EcoSim-Windows.zip"
                target="_blank"
                rel="noreferrer"
                id="direct-download-github"
                className="w-full sm:w-auto flex items-center justify-center gap-3 bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-500 hover:to-green-500 text-white font-bold py-4 px-8 rounded-2xl transition-all duration-300 shadow-md active:scale-95 text-base"
              >
                <Download className="w-5 h-5" />
                <span>Télécharger (Dernière version Windows)</span>
              </a>
              <a
                href="https://github.com/EcoSim-Interactive/EcoSim-game/releases/tag/v1.0.0"
                target="_blank"
                rel="noreferrer"
                className="text-xs font-semibold text-slate-500 dark:text-slate-400 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors"
              >
                Voir d'autres versions (ex: v1.0.0)
              </a>
            </div>
          </div>

          {/* Simple features lists */}
          <div className="lg:col-span-4 p-6 rounded-2xl bg-white dark:bg-slate-950 border border-slate-200/80 dark:border-slate-900/60 text-left space-y-4">
            <h4 className="text-xs font-bold text-slate-800 dark:text-slate-400 uppercase tracking-widest">Inclus dans le téléchargement :</h4>
            <ul className="space-y-3 text-xs text-slate-600 dark:text-slate-400">
              <li className="flex items-center gap-2.5">
                <CheckCircle className="w-4.5 h-4.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <span>Le Lanceur automatique unifié</span>
              </li>
              <li className="flex items-center gap-2.5">
                <CheckCircle className="w-4.5 h-4.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <span>L'affichage 3D interactif</span>
              </li>
              <li className="flex items-center gap-2.5">
                <CheckCircle className="w-4.5 h-4.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <span>Les règles de calcul d'écosystème</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div className="space-y-10 pt-8">
        <div className="text-center space-y-3">
          <h2 className="text-3xl font-bold text-slate-900 dark:text-white">Suivi des Améliorations</h2>
          <p className="text-slate-500 dark:text-slate-400 max-w-xl mx-auto">
            Découvrez l'historique des versions récentes développées pour enrichir la simulation.
          </p>
        </div>

        <div className="p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-6">
          <div className="space-y-6 text-left">
            {DISCOVER_UPDATES.map((update, index) => (
              <div 
                key={index}
                className="flex flex-col sm:flex-row items-start justify-between p-5 rounded-2xl bg-slate-50/50 dark:bg-[#0c101d] border border-slate-100 dark:border-slate-900 transition-colors gap-4"
              >
                <div className="space-y-2">
                  <div className="flex items-center gap-3">
                    <span className="px-2.5 py-0.5 rounded-lg bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-400 text-xs font-bold">
                      {update.version}
                    </span>
                    <h4 className="font-bold text-slate-900 dark:text-white text-base m-0">{update.title}</h4>
                  </div>
                  <p className="text-sm text-slate-500 dark:text-slate-400 font-light leading-relaxed">
                    {update.details}
                  </p>
                </div>
                <span className="text-xs text-slate-450 dark:text-slate-500 font-mono shrink-0 sm:pt-1">
                  {update.date}
                </span>
              </div>
            ))}
          </div>

          <div className="pt-4 text-center border-t border-slate-100 dark:border-slate-850">
            <a 
              href="https://github.com/EcoSim-Interactive/EcoSim-game" 
              target="_blank"
              rel="noreferrer"
              id="btn-git-repo"
              className="inline-flex items-center gap-2 text-xs text-slate-500 hover:text-emerald-600 dark:text-slate-400 dark:hover:text-emerald-400 transition-colors hover:underline"
            >
              <GithubIcon className="w-4 h-4" />
              <span>Voir le code source sur GitHub</span>
              <ChevronRight className="w-3 h-3" />
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
