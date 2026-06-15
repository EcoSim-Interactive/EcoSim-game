import React from 'react';
import { Users } from 'lucide-react';

export default function Team() {
  return (
    <section id="team" className="space-y-12">
      <div className="text-center space-y-3">
        <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">Créateurs</span>
        <h2 className="text-3xl font-bold text-slate-900 dark:text-white">L'Équipe de Développement</h2>
        <p className="text-slate-500 dark:text-slate-400 max-w-xl mx-auto">
          Les concepteurs d'EcoSim Interactive.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Member 1 */}
        <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-left flex flex-col justify-between h-full shadow-sm">
          <div className="space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 flex items-center justify-center">
              <Users className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white m-0">Thomas Boulard</h3>
              <span className="text-xs text-slate-500 font-mono">Concepteur du Moteur de Simulation</span>
            </div>
            <p className="text-xs text-slate-550 dark:text-slate-400 leading-relaxed font-light">
              Thomas s'est concentré sur la logique scientifique de la simulation, codant les règles comportementales des animaux et vérifiant le bon fonctionnement biologique des algorithmes.
            </p>
          </div>
        </div>

        {/* Member 2 */}
        <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-left flex flex-col justify-between h-full shadow-sm">
          <div className="space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-cyan-500/10 flex items-center justify-center">
              <Users className="w-6 h-6 text-cyan-600 dark:text-cyan-400" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white m-0">Abdelqodousse Boustani</h3>
              <span className="text-xs text-slate-500 font-mono">Ingénieur Données & Intégration</span>
            </div>
            <p className="text-xs text-slate-550 dark:text-slate-400 leading-relaxed font-light">
              Abdelqodousse s'est occupé de connecter les calculs écologiques à la fenêtre 3D et a conçu le site de présentation pour rendre le projet accessible au public.
            </p>
          </div>
        </div>

        {/* Member 3 */}
        <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-left flex flex-col justify-between h-full shadow-sm">
          <div className="space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 flex items-center justify-center">
              <Users className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white m-0">Nassim Bouziane</h3>
              <span className="text-xs text-slate-500 font-mono">Architecte Système & Graphismes</span>
            </div>
            <p className="text-xs text-slate-550 dark:text-slate-400 leading-relaxed font-light">
              Nassim a structuré les outils de compilation automatique du projet et a mis en scène les graphismes 3D en concevant l'interface visuelle du logiciel.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
