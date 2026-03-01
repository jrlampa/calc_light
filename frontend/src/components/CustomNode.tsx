import { Handle, Position } from '@xyflow/react';
import { useUIStore, useElectricalStore } from '../store';

// ── TIPOS ──────────────────────────────────────────────────────────────────
export interface PoleNodeData extends Record<string, unknown> {
    label: string;
    effort_dan: number;
    pole_type?: string;
    utilization_percent?: number;
    is_overloaded?: boolean;
    nominal_capacity?: number;
    is_ghost?: boolean;
    is_transformer?: boolean;
}

// ── HELPERS ────────────────────────────────────────────────────────────────
function effortBadgeClass(effort: number, isOverloaded: boolean): string {
    if (isOverloaded) return 'bg-red-500/90 text-white font-bold';
    if (effort > 300) return 'bg-amber-400/90 text-slate-900';
    return 'bg-emerald-500/90 text-white';
}

function tempColor(temp: number): string {
    if (temp > 90) return 'text-red-400';
    if (temp > 70) return 'text-amber-400';
    return 'text-emerald-400';
}

// ── COMPONENTE ─────────────────────────────────────────────────────────────
export default function CustomNode({ id, data }: { id: string; data: PoleNodeData }) {
    const { highlightOverloaded, overloadedNodeIds } = useUIStore();
    const { resultsByNode, trafoDados } = useElectricalStore();

    const effort = data.effort_dan ?? 0;
    const utilization = data.utilization_percent ?? 0;
    const isOverloaded = data.is_overloaded ?? false;
    const nominalCapacity = data.nominal_capacity ?? 0;
    const isGhost = data.is_ghost ?? false;
    const isTransformer = data.is_transformer ?? false;

    // Resultados elétricos injetados pela store (Fase 22)
    const elec = resultsByNode[id];
    const tensaoBaixa = elec ? elec.v_final < 117 : false;
    const termicoRuim = elec ? elec.thermal_status !== 'Ok !' : false;
    const eletricoAlerta = tensaoBaixa || termicoRuim;

    // Dim safe nodes when highlighting overloaded
    const numericId = parseInt(id, 10);
    const isDimmed = highlightOverloaded && overloadedNodeIds.length > 0 && !overloadedNodeIds.includes(numericId);

    const tooltipText = isGhost
        ? `Nó Fantasma (Rede Existente) — exerce tração nos postes reais, não é calculado`
        : nominalCapacity > 0
            ? `Capacidade: ${nominalCapacity.toFixed(0)} daN | Esforço: ${effort.toFixed(1)} daN | Utilização: ${utilization.toFixed(1)}%`
            : `Esforço: ${effort.toFixed(1)} daN`;

    // ── Ghost node ─────────────────────────────────────────────────────────
    if (isGhost) {
        return (
            <div
                className={`flex flex-col items-center gap-1 select-none transition-opacity duration-300 ${isDimmed ? 'opacity-20' : 'opacity-50'}`}
                title={tooltipText}
            >
                <span className="text-[10px] font-semibold text-slate-400 bg-white/60 px-2 py-0.5 rounded-full border border-dashed border-slate-300 shadow-sm whitespace-nowrap">
                    {data.label}
                </span>
                <div className="relative flex items-center justify-center w-14 h-14 rounded-full bg-slate-100/60 border-2 border-dashed border-slate-400/60 shadow-md">
                    <Handle type="target" position={Position.Left} className="!bg-slate-400 !border-slate-300 !w-2.5 !h-2.5" />
                    <Handle type="source" position={Position.Right} className="!bg-slate-400 !border-slate-300 !w-2.5 !h-2.5" />
                    <Handle type="target" position={Position.Top} className="!bg-slate-400 !border-slate-300 !w-2.5 !h-2.5" id="top-in" />
                    <Handle type="source" position={Position.Bottom} className="!bg-slate-400 !border-slate-300 !w-2.5 !h-2.5" id="bot-out" />
                    <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
                        <rect x="12" y="2" width="4" height="20" rx="2" fill="#94a3b8" opacity="0.6" />
                        <rect x="5" y="6" width="18" height="2" rx="1" fill="#94a3b8" opacity="0.4" />
                        <rect x="8" y="10" width="12" height="2" rx="1" fill="#94a3b8" opacity="0.3" />
                    </svg>
                </div>
                <div className="text-[9px] font-medium px-2 py-0.5 rounded-full bg-slate-200/70 text-slate-500 border border-dashed border-slate-300">
                    Rede Existente
                </div>
            </div>
        );
    }

    // ── Transformador ───────────────────────────────────────────────────────
    if (isTransformer && trafoDados) {
        const loadPct = trafoDados.trafo_loading_percent;
        const isOverload = trafoDados.trafo_status === 'Sobrecarga';
        return (
            <div className={`flex flex-col items-center gap-1 select-none transition-opacity duration-300 ${isDimmed ? 'opacity-25' : 'opacity-100'}`}>
                <span className="text-[10px] font-semibold text-violet-300 bg-violet-900/60 px-2 py-0.5 rounded-full border border-violet-500/40 shadow-sm whitespace-nowrap">
                    {data.label}
                </span>
                <div className={`relative flex items-center justify-center w-16 h-16 rounded-full border-2 transition-all duration-200
                    bg-gradient-to-br from-violet-900/80 to-slate-900/60
                    ${isOverload
                        ? 'border-red-500 shadow-[0_4px_20px_rgba(239,68,68,0.6)] animate-pulse'
                        : 'border-violet-500/60 shadow-[0_4px_16px_rgba(139,92,246,0.35)]'
                    }`}
                >
                    <Handle type="source" position={Position.Right} className="!bg-violet-400 !border-violet-300 !w-2.5 !h-2.5" />
                    <Handle type="source" position={Position.Left} className="!bg-violet-400 !border-violet-300 !w-2.5 !h-2.5" />
                    <Handle type="source" position={Position.Bottom} className="!bg-violet-400 !border-violet-300 !w-2.5 !h-2.5" id="bot-out" />
                    {/* Ícone trafo */}
                    <svg width="30" height="30" viewBox="0 0 30 30" fill="none">
                        <circle cx="10" cy="15" r="6" stroke={isOverload ? '#f87171' : '#a78bfa'} strokeWidth="2" fill="none" />
                        <circle cx="20" cy="15" r="6" stroke={isOverload ? '#f87171' : '#a78bfa'} strokeWidth="2" fill="none" />
                    </svg>
                </div>
                {/* Badge de carregamento */}
                <div className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full shadow-md
                    ${isOverload ? 'bg-red-500/90 text-white' : 'bg-violet-600/80 text-white'}`}>
                    {loadPct.toFixed(1)}%
                </div>
                <div className="text-[9px] text-slate-400">{trafoDados.trafo_status}</div>
            </div>
        );
    }

    // ── Poste normal ────────────────────────────────────────────────────────
    return (
        <div
            className={`flex flex-col items-center gap-1 select-none transition-opacity duration-300 ${isDimmed ? 'opacity-25' : 'opacity-100'}`}
            title={tooltipText}
        >
            {/* Label (nome do poste) */}
            <span className="text-[10px] font-semibold text-slate-600 bg-white/80 px-2 py-0.5 rounded-full border border-slate-200 shadow-sm whitespace-nowrap">
                {data.label}
            </span>

            {/* Corpo do nó 2.5D */}
            <div
                className={`
                    relative flex items-center justify-center
                    w-14 h-14 rounded-full
                    bg-gradient-to-br from-white/80 to-blue-50/60
                    border-2 transition-all duration-200
                    ${(isOverloaded || eletricoAlerta)
                        ? 'border-red-500 shadow-[0_4px_16px_rgba(239,68,68,0.5),inset_0_2px_4px_rgba(255,255,255,0.8)] animate-pulse'
                        : 'border-blue-300/60 shadow-[0_4px_16px_rgba(59,130,246,0.25),inset_0_2px_4px_rgba(255,255,255,0.8)] hover:shadow-[0_6px_24px_rgba(59,130,246,0.4)]'
                    }
                `}
            >
                <Handle type="target" position={Position.Left} className="!bg-blue-400 !border-blue-300 !w-2.5 !h-2.5" />
                <Handle type="source" position={Position.Right} className="!bg-blue-400 !border-blue-300 !w-2.5 !h-2.5" />
                <Handle type="target" position={Position.Top} className="!bg-blue-400 !border-blue-300 !w-2.5 !h-2.5" id="top-in" />
                <Handle type="source" position={Position.Bottom} className="!bg-blue-400 !border-blue-300 !w-2.5 !h-2.5" id="bot-out" />

                <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
                    <rect x="12" y="2" width="4" height="20" rx="2" fill={isOverloaded || eletricoAlerta ? '#ef4444' : '#3b82f6'} opacity="0.8" />
                    <rect x="5" y="6" width="18" height="2" rx="1" fill={isOverloaded || eletricoAlerta ? '#fca5a5' : '#60a5fa'} />
                    <rect x="8" y="10" width="12" height="2" rx="1" fill={isOverloaded || eletricoAlerta ? '#fecaca' : '#93c5fd'} />
                </svg>
            </div>

            {/* Badge Esforço Mecânico */}
            <div className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full shadow-md ${effortBadgeClass(effort, isOverloaded)}`}>
                {effort.toFixed(1)} daN
            </div>

            {/* Badges Elétricos — exibidos apenas após calcular (Fase 22) */}
            {elec && (
                <div className="flex flex-col items-center gap-0.5 mt-0.5">
                    {/* ΔV% e Tensão */}
                    <div className="flex gap-1">
                        <span className={`text-[9px] font-mono px-1.5 py-0 rounded-full border
                            ${elec.dv_acum_perc > 8
                                ? 'bg-red-900/40 text-red-300 border-red-500/40'
                                : 'bg-slate-800/60 text-slate-300 border-white/10'}`}>
                            ΔV {elec.dv_acum_perc.toFixed(1)}%
                        </span>
                        <span className={`text-[9px] font-mono px-1.5 py-0 rounded-full border
                            ${tensaoBaixa
                                ? 'bg-red-900/40 text-red-300 border-red-500/40 font-bold'
                                : 'bg-slate-800/60 text-slate-300 border-white/10'}`}>
                            {elec.v_final.toFixed(0)}V
                        </span>
                    </div>
                    {/* Icc e Temperatura */}
                    <div className="flex gap-1">
                        <span className="text-[9px] font-mono px-1.5 py-0 rounded-full bg-slate-800/60 text-blue-300 border border-white/10">
                            {(elec.icc_amperes / 1000).toFixed(1)}kA
                        </span>
                        <span className={`text-[9px] font-mono px-1.5 py-0 rounded-full border bg-slate-800/60 border-white/10 ${tempColor(elec.cable_temp_celsius)}`}>
                            {elec.cable_temp_celsius.toFixed(0)}°C
                        </span>
                    </div>
                </div>
            )}

            {/* Percentual de utilização mecânica — visível apenas quando disponível */}
            {utilization > 0 && (
                <div className={`text-[10px] px-1.5 py-0 rounded-full ${isOverloaded ? 'text-red-600 font-bold' : 'text-slate-500 font-medium'}`}>
                    {utilization.toFixed(1)}%
                </div>
            )}
        </div>
    );
}
