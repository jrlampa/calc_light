import { Ghost, Plus, X } from 'lucide-react';

// ── TIPOS ──────────────────────────────────────────────────────────────────
export type GhostNodeChoice = 'new' | 'ghost';

interface Props {
    onChoose: (choice: GhostNodeChoice) => void;
    onClose: () => void;
}

// ── COMPONENTE ─────────────────────────────────────────────────────────────
/**
 * Modal Rápido 2.5D — drop-on-pane.
 *
 * Aparece quando o usuário arrasta a ponta de uma aresta e solta no fundo do
 * canvas (sem destino). Pergunta se deseja criar um Novo Poste (real) ou um
 * Nó Fantasma (representando a rede existente da concessionária).
 */
export default function GhostNodeModal({ onChoose, onClose }: Props) {
    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/20 backdrop-blur-sm"
            onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
        >
            <div className="w-full max-w-sm bg-white/85 backdrop-blur-xl border border-white/70 rounded-2xl shadow-2xl overflow-hidden">
                {/* ── Cabeçalho ─────────────────────────────────────────── */}
                <div className="px-6 py-4 border-b border-slate-200/60 bg-white/40 flex items-center justify-between">
                    <h2 className="text-sm font-bold text-slate-800">Conexão sem destino</h2>
                    <button
                        onClick={onClose}
                        className="p-1 rounded hover:bg-slate-100/60 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400/50"
                        aria-label="Fechar modal"
                    >
                        <X size={15} className="text-slate-500" />
                    </button>
                </div>

                {/* ── Corpo ─────────────────────────────────────────────── */}
                <div className="px-6 py-5 space-y-3">
                    <p className="text-xs text-slate-500 leading-relaxed">
                        Esta conexão não possui destino. O que deseja criar?
                    </p>

                    {/* Opção 1: Novo Poste (real) */}
                    <button
                        onClick={() => onChoose('new')}
                        className="w-full flex items-center gap-3 p-4 rounded-xl border border-blue-200/60 bg-blue-50/60 hover:bg-blue-100/60 transition-colors group focus:outline-none focus:ring-2 focus:ring-blue-400/50"
                    >
                        <div className="flex-shrink-0 w-9 h-9 rounded-full bg-blue-500/20 flex items-center justify-center group-hover:bg-blue-500/30 transition-colors">
                            <Plus size={16} className="text-blue-600" />
                        </div>
                        <div className="text-left">
                            <p className="text-sm font-semibold text-blue-800">Novo Poste</p>
                            <p className="text-xs text-blue-600/70">Cria um poste real, calculado e exportado</p>
                        </div>
                    </button>

                    {/* Opção 2: Nó Fantasma */}
                    <button
                        onClick={() => onChoose('ghost')}
                        className="w-full flex items-center gap-3 p-4 rounded-xl border border-slate-300/60 bg-slate-50/60 hover:bg-slate-100/60 transition-colors group focus:outline-none focus:ring-2 focus:ring-slate-400/50"
                    >
                        <div className="flex-shrink-0 w-9 h-9 rounded-full bg-slate-400/20 flex items-center justify-center group-hover:bg-slate-400/30 transition-colors">
                            <Ghost size={16} className="text-slate-500" />
                        </div>
                        <div className="text-left">
                            <p className="text-sm font-semibold text-slate-700">Nó Fantasma <span className="text-slate-400 font-normal">(Rede Existente)</span></p>
                            <p className="text-xs text-slate-400">Exerce tração, mas não é calculado nem exportado</p>
                        </div>
                    </button>
                </div>

                {/* ── Rodapé ────────────────────────────────────────────── */}
                <div className="px-6 py-3 border-t border-slate-100/60 bg-white/20">
                    <button
                        onClick={onClose}
                        className="w-full text-xs text-slate-400 hover:text-slate-600 transition-colors py-1 focus:outline-none"
                    >
                        Cancelar — não criar nada
                    </button>
                </div>
            </div>
        </div>
    );
}
