import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, AlertCircle, CheckCircle2, X, Zap, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { api } from '../api';

// ── TIPOS ──────────────────────────────────────────────────────────────────

interface SpanSuggestionOut {
    span_id: number;
    new_mt_sag_m: number | null;
    new_bt_sag_m: number | null;
}

export interface SolverSuggestionOut {
    node_id: number;
    node_label: string;
    current_effort_dan: number;
    target_effort_dan: number | null;
    is_extreme: boolean;
    requires_span_break: boolean;
    message: string;
    span_suggestions: SpanSuggestionOut[];
}

interface SolverReportOut {
    project_id: number;
    suggestions: SolverSuggestionOut[];
    overloaded_count: number;
    solvable_count: number;
    requires_span_break_count: number;
}

interface Props {
    projectId: number;
    onClose: () => void;
}

// ── COMPONENTE ─────────────────────────────────────────────────────────────

/**
 * Modal de Otimização — Fase 17 (Solver Global).
 *
 * Lista as sugestões do motor heurístico com três estados visuais:
 *   • Normal solvable   → linha branca + checkbox
 *   • Extreme solvable  → linha amarela ⚠️ + checkbox
 *   • Span break needed → linha vermelha 🚨 + checkbox bloqueado
 */
export default function SolverModal({ projectId, onClose }: Props) {
    const queryClient = useQueryClient();
    const [selected, setSelected] = useState<Set<number>>(new Set());

    // ── Fetch do relatório do solver ────────────────────────────────────────
    const { data: report, isLoading, isError } = useQuery<SolverReportOut>({
        queryKey: ['solver', projectId],
        queryFn: () => api.get(`/projects/${projectId}/solve`).then(r => r.data),
        refetchOnWindowFocus: false,
        retry: false,
    });

    // ── Mutation: aplicar sugestões selecionadas ────────────────────────────
    const applyMut = useMutation({
        mutationFn: (items: { span_suggestions: SpanSuggestionOut[] }[]) =>
            api.post(`/projects/${projectId}/solve/apply`, { items }),
        onSuccess: (res) => {
            const updated: number = res.data.updated_spans ?? 0;
            toast.success(`${updated} vão(s) otimizado(s) com sucesso!`);
            queryClient.invalidateQueries({ queryKey: ['topology', projectId] });
            queryClient.invalidateQueries({ queryKey: ['solver', projectId] });
            onClose();
        },
        onError: () => {
            toast.error('Erro ao aplicar otimizações. Tente novamente.');
        },
    });

    const toggleSelect = (nodeId: number) => {
        setSelected(prev => {
            const next = new Set(prev);
            if (next.has(nodeId)) next.delete(nodeId);
            else next.add(nodeId);
            return next;
        });
    };

    const handleApply = () => {
        if (!report) return;
        const items = report.suggestions
            .filter(s => selected.has(s.node_id) && !s.requires_span_break)
            .map(s => ({ span_suggestions: s.span_suggestions }));
        if (items.length === 0) {
            toast.warning('Selecione ao menos uma sugestão aplicável.');
            return;
        }
        applyMut.mutate(items);
    };

    const solvable = report?.suggestions.filter(s => !s.requires_span_break) ?? [];
    const allSolvableSelected = solvable.length > 0 && solvable.every(s => selected.has(s.node_id));

    const toggleAll = () => {
        if (allSolvableSelected) {
            setSelected(new Set());
        } else {
            setSelected(new Set(solvable.map(s => s.node_id)));
        }
    };

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/30 backdrop-blur-sm"
            onClick={e => { if (e.target === e.currentTarget) onClose(); }}
        >
            <div className="w-full max-w-2xl bg-white/90 backdrop-blur-xl border border-white/70 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
                {/* ── Cabeçalho ──────────────────────────────────────────── */}
                <div className="px-6 py-4 border-b border-slate-200/60 bg-gradient-to-r from-indigo-50/60 to-white/60 flex items-center justify-between flex-shrink-0">
                    <div className="flex items-center gap-2">
                        <Zap size={16} className="text-indigo-500" />
                        <h2 className="text-sm font-bold text-slate-800">Otimizar Rede</h2>
                        {report && (
                            <span className="text-xs text-slate-500 ml-1">
                                ({report.overloaded_count} poste(s) sobrecarregado(s))
                            </span>
                        )}
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1 rounded hover:bg-slate-100/60 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-400/50"
                        aria-label="Fechar modal"
                    >
                        <X size={15} className="text-slate-500" />
                    </button>
                </div>

                {/* ── Corpo ──────────────────────────────────────────────── */}
                <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
                    {isLoading && (
                        <div className="flex items-center justify-center gap-2 py-10 text-slate-500">
                            <Loader2 size={18} className="animate-spin text-indigo-400" />
                            <span className="text-sm">Executando análise de otimização…</span>
                        </div>
                    )}

                    {isError && (
                        <div className="text-center py-8 text-red-400 text-sm">
                            Erro ao executar o solver. Verifique se o backend está disponível.
                        </div>
                    )}

                    {report && report.suggestions.length === 0 && (
                        <div className="flex flex-col items-center gap-2 py-10 text-slate-400">
                            <CheckCircle2 size={28} className="text-emerald-400" />
                            <p className="text-sm font-medium text-emerald-600">Rede OK!</p>
                            <p className="text-xs">Nenhum poste excede o limite de 2 000 daN. Sem sugestões necessárias.</p>
                        </div>
                    )}

                    {report && report.suggestions.length > 0 && (
                        <>
                            {/* Selecionar todos os aplicáveis */}
                            {solvable.length > 0 && (
                                <div className="flex items-center gap-2 pb-1 border-b border-slate-100">
                                    <input
                                        type="checkbox"
                                        id="select-all"
                                        checked={allSolvableSelected}
                                        onChange={toggleAll}
                                        className="w-3.5 h-3.5 accent-indigo-500"
                                    />
                                    <label htmlFor="select-all" className="text-xs text-slate-500 cursor-pointer select-none">
                                        Selecionar todos os aplicáveis ({solvable.length})
                                    </label>
                                </div>
                            )}

                            {/* Lista de sugestões */}
                            {report.suggestions.map(s => (
                                <SuggestionRow
                                    key={s.node_id}
                                    suggestion={s}
                                    isSelected={selected.has(s.node_id)}
                                    onToggle={() => toggleSelect(s.node_id)}
                                />
                            ))}
                        </>
                    )}
                </div>

                {/* ── Rodapé ─────────────────────────────────────────────── */}
                <div className="px-6 py-4 border-t border-slate-100/60 bg-white/40 flex items-center justify-between flex-shrink-0 gap-3">
                    <p className="text-xs text-slate-400">
                        {selected.size > 0
                            ? `${selected.size} sugestão(ões) selecionada(s)`
                            : 'Selecione sugestões para aplicar'}
                    </p>
                    <div className="flex gap-2">
                        <button
                            onClick={onClose}
                            className="px-4 py-1.5 text-xs text-slate-500 hover:text-slate-700 transition-colors focus:outline-none"
                        >
                            Cancelar
                        </button>
                        <button
                            onClick={handleApply}
                            disabled={selected.size === 0 || applyMut.isPending}
                            className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-medium rounded-lg bg-indigo-500 text-white hover:bg-indigo-600 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-400/50 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {applyMut.isPending && <Loader2 size={11} className="animate-spin" />}
                            Aplicar Sugestões
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

// ── SUB-COMPONENTE: linha de sugestão ─────────────────────────────────────

function SuggestionRow({
    suggestion: s,
    isSelected,
    onToggle,
}: {
    suggestion: SolverSuggestionOut;
    isSelected: boolean;
    onToggle: () => void;
}) {
    if (s.requires_span_break) {
        return (
            <div className="flex items-start gap-3 p-3 rounded-xl border border-red-300/60 bg-red-50/60">
                {/* Checkbox bloqueado */}
                <input
                    type="checkbox"
                    disabled
                    className="mt-0.5 w-3.5 h-3.5 opacity-30 cursor-not-allowed"
                />
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 mb-1">
                        <AlertCircle size={13} className="text-red-500 flex-shrink-0" />
                        <span className="text-xs font-bold text-red-700">🚨 {s.node_label}</span>
                        <span className="ml-auto text-xs font-mono text-red-600">
                            {s.current_effort_dan.toFixed(1)} daN
                        </span>
                    </div>
                    <p className="text-xs text-red-600 leading-relaxed">
                        <strong>Limite de 2 000 daN excedido.</strong> Adicione um poste intermediário (Quebra de Vão).
                    </p>
                </div>
            </div>
        );
    }

    if (s.is_extreme) {
        return (
            <div
                className={`flex items-start gap-3 p-3 rounded-xl border transition-colors cursor-pointer ${
                    isSelected
                        ? 'border-amber-400/80 bg-amber-50/80'
                        : 'border-amber-300/50 bg-amber-50/40 hover:bg-amber-50/70'
                }`}
                onClick={onToggle}
            >
                <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={onToggle}
                    onClick={e => e.stopPropagation()}
                    className="mt-0.5 w-3.5 h-3.5 accent-amber-500"
                />
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 mb-1">
                        <AlertTriangle size={13} className="text-amber-500 flex-shrink-0" />
                        <span className="text-xs font-semibold text-amber-800">⚠️ {s.node_label}</span>
                        <span className="ml-auto text-xs font-mono text-amber-700">
                            {s.current_effort_dan.toFixed(1)} → {s.target_effort_dan?.toFixed(1)} daN
                        </span>
                    </div>
                    <p className="text-xs text-amber-700 leading-relaxed">{s.message}</p>
                    {s.span_suggestions.filter(ss => ss.new_mt_sag_m != null).map(ss => (
                        <span key={ss.span_id} className="inline-block mt-1 text-[10px] bg-amber-200/60 text-amber-800 px-1.5 py-0.5 rounded-full">
                            Vão #{ss.span_id}: flecha MT → {ss.new_mt_sag_m} m
                        </span>
                    ))}
                </div>
            </div>
        );
    }

    // Normal solvable
    return (
        <div
            className={`flex items-start gap-3 p-3 rounded-xl border transition-colors cursor-pointer ${
                isSelected
                    ? 'border-indigo-300/80 bg-indigo-50/60'
                    : 'border-slate-200/60 bg-white/50 hover:bg-slate-50/70'
            }`}
            onClick={onToggle}
        >
            <input
                type="checkbox"
                checked={isSelected}
                onChange={onToggle}
                onClick={e => e.stopPropagation()}
                className="mt-0.5 w-3.5 h-3.5 accent-indigo-500"
            />
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5 mb-1">
                    <CheckCircle2 size={13} className="text-indigo-400 flex-shrink-0" />
                    <span className="text-xs font-semibold text-slate-700">{s.node_label}</span>
                    <span className="ml-auto text-xs font-mono text-slate-500">
                        {s.current_effort_dan.toFixed(1)} → {s.target_effort_dan?.toFixed(1)} daN
                    </span>
                </div>
                <p className="text-xs text-slate-500 leading-relaxed">{s.message}</p>
                {s.span_suggestions.filter(ss => ss.new_mt_sag_m != null).map(ss => (
                    <span key={ss.span_id} className="inline-block mt-1 text-[10px] bg-indigo-100/60 text-indigo-700 px-1.5 py-0.5 rounded-full">
                        Vão #{ss.span_id}: flecha MT → {ss.new_mt_sag_m} m
                    </span>
                ))}
            </div>
        </div>
    );
}
