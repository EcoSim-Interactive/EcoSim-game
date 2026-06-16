import React from 'react';
import { Server, RefreshCw, Monitor } from 'lucide-react';

export default function Architecture() {
  return (
    <section id="architecture" className="space-y-12">
      <div className="text-center space-y-3">
        <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">Fonctionnement</span>
        <h2 className="text-3xl font-bold text-slate-900 dark:text-white">Comment fonctionne le simulateur ?</h2>
        <p className="text-slate-500 dark:text-slate-400 max-w-xl mx-auto">
          L'application se compose de trois éléments simples qui collaborent pour donner vie à la savane virtuelle.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Component 1 */}
        <div className="p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex flex-col justify-between shadow-sm">
          <div className="space-y-4 text-left">
            <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 flex items-center justify-center">
              <Server className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Le Cerveau Écologique (Python)</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
              C'est lui qui calcule de manière scientifique toutes les actions des animaux. Il calcule si une gazelle a faim, si elle trouve de l'herbe, s'il y a un point d'eau à proximité, ou si elle se fait chasser par un lion ou une hyène. Il utilise des formules mathématiques pour garantir le réalisme de la simulation.
            </p>
          </div>
          <span className="text-[10px] font-bold text-slate-400 dark:text-slate-600 mt-6 tracking-widest uppercase text-left">MOTEUR LOGIQUE</span>
        </div>

        {/* Component 2 */}
        <div className="p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex flex-col justify-between shadow-sm">
          <div className="space-y-4 text-left">
            <div className="w-12 h-12 rounded-2xl bg-amber-500/10 flex items-center justify-center">
              <RefreshCw className="w-6 h-6 text-amber-600 dark:text-amber-400" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Le Fil Connecteur (WebSockets)</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
              Il relie les calculs à l'image. Chaque seconde, il transporte les informations de position des animaux depuis le cerveau écologique jusqu'à l'écran d'affichage, de façon instantanée et invisible pour l'utilisateur.
            </p>
          </div>
          <span className="text-[10px] font-bold text-slate-400 dark:text-slate-600 mt-6 tracking-widest uppercase text-left">TRANSMISSION DES DONNÉES</span>
        </div>

        {/* Component 3 */}
        <div className="p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex flex-col justify-between shadow-sm">
          <div className="space-y-4 text-left">
            <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 flex items-center justify-center">
              <Monitor className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">La Fenêtre Visuelle (Godot 3D)</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
              C'est la partie ludique du logiciel. Il affiche la savane en 3D avec des graphismes épurés, anime les animaux selon les informations reçues et fournit une interface avec des boutons pour contrôler l'écoulement du temps.
            </p>
          </div>
          <span className="text-[10px] font-bold text-slate-400 dark:text-slate-600 mt-6 tracking-widest uppercase text-left">INTERFACE GRAPHIQUE</span>
        </div>
      </div>
    </section>
  );
}
