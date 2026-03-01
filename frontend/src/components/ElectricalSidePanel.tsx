/**
 * ElectricalSidePanel — Fase 22
 * Painel lateral em pt-BR com dados do Motor CQT Elétrico.
 * Abas: Resumo | Avançado
 * Separação de responsabilidades: exibe dados injetados pela store, sem lógica de cálculo.
 */

import { useState } from 'react';
import { useElectricalStore } from '../store';

interface Props {
    nodeId: string;
    isTransformer?: boolean;
    onClose: () => void;
}

function StatusBadge({ ok, label }: { ok: boolean; label: string }) {
    return (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold
            ${ok
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                : 'bg-red-500/20 text-red-300 border border-red-500/40 animate-pulse'
            }`}
        >
            <span className={`w-1.5 h-1.5 rounded-full ${ok ? 'bg-emerald-400' : 'bg-red-400'}`} />
            {label}
        </span>
    );
}

function InfoRow({ label, value, unit = '', highlight = false }: {
    label: string; value: string | number; unit?: string; highlight?: boolean;
}) {
    return (
        <div className="flex justify-between items-center py-1.5 border-b border-white/5">
            <span className="text-xs text-slate-400">{label}</span>
            <span className={`text-xs font-mono font-semibold ${highlight ? 'text-amber-300' : 'text-slate-200'}`}>
                {value}{unit}
            </span>
        </div>
    );
}

export default function ElectricalSidePanel({ nodeId, isTransformer = false, onClose }: Props) {
    const [tab, setTab] = useState<'resumo' | 'avancado'>('resumo');
    const { resultsByNode, trafoDados } = useElectricalStore();

    const result = resultsByNode[nodeId];

    if (isTransformer && trafoDados) {
        const loading = trafoDados.trafo_loading_percent;
        const isOverload = trafoDados.trafo_status === 'Sobrecarga';
        return (
            <aside className="absolute right-4 top-4 z-50 w-72 bg-slate-900/95 backdrop-blur-md border border-white/10 rounded-2xl shadow-2xl text-white overflow-hidden">
                {/* Cabeçalho Trafo */}
                <div className="px-4 py-3 bg-gradient-to-r from-violet-900/80 to-slate-900/80 flex justify-between items-center border-b border-white/10">
                    <div>
                        <p className="text-xs text-slate-400 uppercase tracking-widest">Transformador</p>
                        <p className="text-sm font-bold text-white">Nó Raiz</p>
                    </div>
                    <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors text-lg leading-none">✕</button>
                </div>
                <div className="px-4 py-4 space-y-2">
                    <div className="flex justify-between items-center">
                        <span className="text-xs text-slate-400">Carregamento Projetado</span>
                        <span className={`text-2xl font-black font-mono ${isOverload ? 'text-red-400 animate-pulse' : 'text-emerald-400'}`}>
                            {loading.toFixed(1)}%
                        </span>
                    </div>
                    <StatusBadge ok={!isOverload} label={trafoDados.trafo_status} />
                    <div className="mt-3 space-y-0">
                        <InfoRow label="Carga Atual" value={trafoDados.carga_atual_kva.toFixed(1)} unit=" kVA" />
                        <InfoRow label="Carga Projetada (c/ margem)" value={trafoDados.carga_projetada_kva.toFixed(1)} unit=" kVA" />
                    </div>
                </div>
            </aside>
        );
    }

    if (!result) {
        return (
            <aside className="absolute right-4 top-4 z-50 w-72 bg-slate-900/95 backdrop-blur-md border border-white/10 rounded-2xl shadow-2xl p-4 text-slate-400 text-sm">
                <div className="flex justify-between items-center mb-2">
                    <span>Nó {nodeId}</span>
                    <button onClick={onClose} className="text-slate-500 hover:text-white">✕</button>
                </div>
                <p className="text-xs">Execute "Calcular Rede CQT" para ver os dados elétricos aqui.</p>
            </aside>
        );
    }

    const tensaoBaixa = result.v_final < 117;
    const termicoRuim = result.thermal_status !== 'Ok !';
    const alertar = tensaoBaixa || termicoRuim;

    return (
        <aside className="absolute right-4 top-4 z-50 w-72 bg-slate-900/95 backdrop-blur-md border border-white/10 rounded-2xl shadow-2xl text-white overflow-hidden">
            {/* Cabeçalho */}
            <div className={`px-4 py-3 flex justify-between items-center border-b border-white/10
                ${alertar ? 'bg-gradient-to-r from-red-900/70 to-slate-900/80' : 'bg-gradient-to-r from-blue-900/60 to-slate-900/80'}`}>
                <div>
                    <p className="text-xs text-slate-400 uppercase tracking-widest">Poste</p>
                    <p className="text-sm font-bold text-white">{result.id}</p>
                </div>
                <div className="flex items-center gap-2">
                    {alertar && <span className="text-red-400 animate-pulse text-base">⚠</span>}
                    <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors text-lg leading-none">✕</button>
                </div>
            </div>

            {/* Abas */}
            <div className="flex border-b border-white/10">
                {(['resumo', 'avancado'] as const).map(t => (
                    <button
                        key={t}
                        onClick={() => setTab(t)}
                        className={`flex-1 py-2 text-xs font-semibold transition-colors
                            ${tab === t ? 'text-blue-300 border-b-2 border-blue-400' : 'text-slate-500 hover:text-slate-300'}`}
                    >
                        {t === 'resumo' ? 'Resumo' : 'Avançado'}
                    </button>
                ))}
            </div>

            {/* Conteúdo */}
            <div className="px-4 py-3 space-y-0.5">
                {tab === 'resumo' ? (
                    <>
                        <InfoRow label="Tensão Final" value={result.v_final.toFixed(1)} unit=" V"
                            highlight={tensaoBaixa} />
                        <InfoRow label="Queda de Tensão" value={result.dv_acum_perc.toFixed(2)} unit=" %"
                            highlight={result.dv_acum_perc > 8} />
                        <InfoRow label="Icc (trifásico)" value={(result.icc_amperes / 1000).toFixed(2)} unit=" kA" />
                        <InfoRow label="Temperatura do Cabo" value={result.cable_temp_celsius.toFixed(1)} unit=" °C"
                            highlight={termicoRuim} />
                        <InfoRow label="Carga no Trecho" value={result.carga_acum_kva.toFixed(2)} unit=" kVA" />
                        <div className="pt-2 flex gap-2 flex-wrap">
                            <StatusBadge ok={!tensaoBaixa} label={tensaoBaixa ? 'Tensão Baixa' : 'Tensão Ok'} />
                            <StatusBadge ok={!termicoRuim} label={result.thermal_status} />
                        </div>
                    </>
                ) : (
                    <>
                        <InfoRow label="ΔV Trecho" value={result.dv_trecho_perc.toFixed(4)} unit=" %" />
                        <InfoRow label="ΔV Acumulado" value={result.dv_acum_perc.toFixed(4)} unit=" %" />
                        <InfoRow label="Icc (A)" value={result.icc_amperes.toFixed(0)} unit=" A" />
                        <InfoRow label="Carga Trecho" value={result.carga_kva.toFixed(3)} unit=" kVA" />
                        <InfoRow label="Carga Acumulada" value={result.carga_acum_kva.toFixed(3)} unit=" kVA" />
                        <div className="mt-3 p-2 bg-white/5 rounded-lg text-[10px] text-slate-400 font-mono space-y-0.5">
                            <p className="text-slate-500 text-[9px] uppercase tracking-widest mb-1">Fórmulas Aplicadas</p>
                            <p>ΔV% = K × S(kVA) × L(km) × F_fase</p>
                            <p>T = 30 + (I/Iamp) × 60 °C</p>
                            <p>Icc = U / |Z_total|</p>
                        </div>
                    </>
                )}
            </div>
        </aside>
    );
}
