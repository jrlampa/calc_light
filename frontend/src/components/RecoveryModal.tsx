import { CloudOff, RefreshCcw, Trash2 } from 'lucide-react';

interface Props {
    savedAt: string;          // ISO timestamp of the local backup
    onRecover: () => void;    // user wants local version
    onDiscard: () => void;    // user wants server version
}

/**
 * Modal de Recuperação de Desastres — Fase 18.
 *
 * Exibido quando o backup local (localStorage) é MAIS RECENTE que a
 * versão do banco de dados, indicando que o usuário tinha progresso
 * não sincronizado (ex: conexão caiu antes de salvar na nuvem).
 */
export default function RecoveryModal({ savedAt, onRecover, onDiscard }: Props) {
    const formattedTime = (() => {
        try {
            const d = new Date(savedAt);
            if (isNaN(d.getTime())) return savedAt;
            return d.toLocaleString('pt-BR', {
                dateStyle: 'short',
                timeStyle: 'medium',
            });
        } catch {
            return savedAt;
        }
    })();

    return (
        <div
            className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-md"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="recovery-title"
            aria-describedby="recovery-desc"
        >
            <div className="w-full max-w-md bg-white/90 backdrop-blur-xl border border-white/70 rounded-2xl shadow-2xl shadow-slate-400/30 overflow-hidden">
                {/* ── Cabeçalho ─────────────────────────────────────────── */}
                <div className="px-6 py-4 border-b border-amber-200/60 bg-amber-50/70 flex items-center gap-3">
                    <div className="p-2 bg-amber-400/20 rounded-xl">
                        <CloudOff size={20} className="text-amber-600" />
                    </div>
                    <h2 id="recovery-title" className="text-sm font-bold text-amber-800">
                        Progresso não sincronizado detectado
                    </h2>
                </div>

                {/* ── Corpo ─────────────────────────────────────────────── */}
                <div className="px-6 py-5 space-y-4">
                    <p id="recovery-desc" className="text-sm text-slate-700 leading-relaxed">
                        Detectamos um progresso não salvo no seu navegador — mais recente
                        que a versão na nuvem. Isso pode ter ocorrido porque a conexão caiu
                        antes de sincronizar.
                    </p>

                    <div className="bg-slate-50/80 border border-slate-200/60 rounded-xl px-4 py-3 text-xs text-slate-500 space-y-1">
                        <p><span className="font-semibold text-slate-700">Backup local salvo em:</span> {formattedTime}</p>
                    </div>

                    <p className="text-xs text-slate-400">
                        Deseja recuperar a versão local (preserva seu trabalho não salvo) ou
                        descartar e usar a versão da nuvem?
                    </p>
                </div>

                {/* ── Ações ─────────────────────────────────────────────── */}
                <div className="px-6 pb-5 flex flex-col gap-2">
                    <button
                        onClick={onRecover}
                        className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-amber-500 hover:bg-amber-600 rounded-xl shadow-md shadow-amber-400/30 transition-colors focus:outline-none focus:ring-2 focus:ring-amber-400/50"
                        aria-label="Recuperar versão local"
                    >
                        <RefreshCcw size={15} />
                        Recuperar versão local
                    </button>
                    <button
                        onClick={onDiscard}
                        className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm text-slate-500 hover:text-slate-700 hover:bg-slate-100/60 rounded-xl transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400/50"
                        aria-label="Descartar progresso local e usar versão da nuvem"
                    >
                        <Trash2 size={15} />
                        Descartar e usar versão da nuvem
                    </button>
                </div>
            </div>
        </div>
    );
}
