import { Keyboard, X } from 'lucide-react';

interface ShortcutsModalProps {
    onClose: () => void;
}

interface ShortcutEntry {
    keys: string[];
    description: string;
}

interface ShortcutGroup {
    title: string;
    shortcuts: ShortcutEntry[];
}

const SHORTCUT_GROUPS: ShortcutGroup[] = [
    {
        title: 'Navegação Global',
        shortcuts: [
            { keys: ['Alt', '1'], description: 'Ir para Aba 1 — Entrada de Dados' },
            { keys: ['Alt', '2'], description: 'Ir para Aba 2 — Diagrama de Forças' },
            { keys: ['Alt', '3'], description: 'Ir para Aba 3 — Unifilar Topológico' },
            { keys: ['Ctrl', 'S'], description: 'Salvar formulário atual' },
            { keys: ['Shift', '?'], description: 'Abrir/fechar este mapa de atalhos' },
            { keys: ['Esc'], description: 'Fechar janelas e modais' },
        ],
    },
    {
        title: 'Formulário de Dados (Aba 1)',
        shortcuts: [
            { keys: ['Tab'], description: 'Avançar para o próximo campo' },
            { keys: ['Shift', 'Tab'], description: 'Voltar para o campo anterior' },
            { keys: ['Enter'], description: 'Submeter o formulário ativo' },
            { keys: ['Foco'], description: 'O valor do campo é selecionado automaticamente' },
        ],
    },
    {
        title: 'Topologia (Aba 3)',
        shortcuts: [
            { keys: ['↑ ↓ ← →'], description: 'Mover poste selecionado (Nudge ±10px)' },
            { keys: ['Delete'], description: 'Apagar poste/vão selecionado' },
            { keys: ['Backspace'], description: 'Apagar poste/vão selecionado' },
        ],
    },
];

function KeyBadge({ label }: { label: string }) {
    return (
        <kbd className="
            inline-flex items-center justify-center
            min-w-[28px] h-6 px-1.5
            rounded-md border border-slate-200
            bg-white/80 shadow-[0_2px_0_rgba(0,0,0,0.08)]
            text-[11px] font-semibold text-slate-600
            font-mono
        ">
            {label}
        </kbd>
    );
}

export default function ShortcutsModal({ onClose }: ShortcutsModalProps) {
    return (
        /* Backdrop */
        <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/30 backdrop-blur-sm"
            role="dialog"
            aria-modal="true"
            aria-label="Mapa de atalhos de teclado"
            onClick={(e) => {
                if (e.target === e.currentTarget) onClose();
            }}
        >
            {/* Panel 2.5D Glassmorphism */}
            <div className="
                relative w-full max-w-lg
                bg-white/80 backdrop-blur-xl
                border border-white/70
                rounded-2xl shadow-2xl shadow-slate-400/30
                overflow-hidden
            ">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200/60 bg-white/40">
                    <div className="flex items-center gap-2">
                        <Keyboard size={20} className="text-blue-500" />
                        <h2 className="text-base font-bold text-slate-800">Atalhos de Teclado</h2>
                    </div>
                    <button
                        onClick={onClose}
                        aria-label="Fechar modal de atalhos"
                        className="
                            p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100/60
                            transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400/50
                        "
                    >
                        <X size={18} />
                    </button>
                </div>

                {/* Body */}
                <div className="px-6 py-5 space-y-5 max-h-[70vh] overflow-y-auto custom-scrollbar">
                    {SHORTCUT_GROUPS.map((group) => (
                        <div key={group.title}>
                            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
                                {group.title}
                            </h3>
                            <div className="space-y-2">
                                {group.shortcuts.map((s) => (
                                    <div
                                        key={s.description}
                                        className="flex items-center justify-between gap-4 py-1.5"
                                    >
                                        <span className="text-sm text-slate-600">{s.description}</span>
                                        <div className="flex items-center gap-1 shrink-0">
                                            {s.keys.map((k, i) => (
                                                <span key={i} className="flex items-center gap-1">
                                                    <KeyBadge label={k} />
                                                    {i < s.keys.length - 1 && (
                                                        <span className="text-[10px] text-slate-400">+</span>
                                                    )}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>

                {/* Footer hint */}
                <div className="px-6 py-3 border-t border-slate-200/60 bg-white/30">
                    <p className="text-xs text-slate-400 text-center">
                        Pressione <KeyBadge label="Shift" /> + <KeyBadge label="?" /> ou <KeyBadge label="Esc" /> para fechar
                    </p>
                </div>
            </div>
        </div>
    );
}
