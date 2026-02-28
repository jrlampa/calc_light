import { Handle, Position } from '@xyflow/react';
import { useUIStore } from '../store';

// ── TIPOS ──────────────────────────────────────────────────────────────────
export interface PoleNodeData extends Record<string, unknown> {
    label: string;
    effort_dan: number;
    pole_type?: string;
    utilization_percent?: number;
    is_overloaded?: boolean;
    nominal_capacity?: number;
}

// ── HELPERS ────────────────────────────────────────────────────────────────
function effortBadgeClass(effort: number, isOverloaded: boolean): string {
    if (isOverloaded) return 'bg-red-500/90 text-white font-bold';
    if (effort > 300) return 'bg-amber-400/90 text-slate-900';
    return 'bg-emerald-500/90 text-white';
}

// ── COMPONENTE ─────────────────────────────────────────────────────────────
export default function CustomNode({ id, data }: { id: string; data: PoleNodeData }) {
    const { highlightOverloaded, overloadedNodeIds } = useUIStore();
    const effort = data.effort_dan ?? 0;
    const utilization = data.utilization_percent ?? 0;
    const isOverloaded = data.is_overloaded ?? false;
    const nominalCapacity = data.nominal_capacity ?? 0;

    // Dim safe nodes when highlighting overloaded
    const numericId = parseInt(id, 10);
    const isDimmed = highlightOverloaded && overloadedNodeIds.length > 0 && !overloadedNodeIds.includes(numericId);

    const tooltipText = nominalCapacity > 0
        ? `Capacidade: ${nominalCapacity.toFixed(0)} daN | Esforço: ${effort.toFixed(1)} daN | Utilização: ${utilization.toFixed(1)}%`
        : `Esforço: ${effort.toFixed(1)} daN`;

    return (
        <div
            className={`flex flex-col items-center gap-1 select-none transition-opacity duration-300 ${isDimmed ? 'opacity-25' : 'opacity-100'}`}
            title={tooltipText}
        >
            {/* Label (nome do poste) — ACIMA do desenho */}
            <span className="text-[10px] font-semibold text-slate-600 bg-white/80 px-2 py-0.5 rounded-full border border-slate-200 shadow-sm whitespace-nowrap">
                {data.label}
            </span>

            {/* Corpo do nó 2.5D — círculo Glassmorphism */}
            <div
                className={`
                    relative flex items-center justify-center
                    w-14 h-14 rounded-full
                    bg-gradient-to-br from-white/80 to-blue-50/60
                    border-2 transition-all duration-200
                    ${isOverloaded
                        ? 'border-red-500 shadow-[0_4px_16px_rgba(239,68,68,0.5),inset_0_2px_4px_rgba(255,255,255,0.8)] animate-pulse'
                        : 'border-blue-300/60 shadow-[0_4px_16px_rgba(59,130,246,0.25),inset_0_2px_4px_rgba(255,255,255,0.8)] hover:shadow-[0_6px_24px_rgba(59,130,246,0.4)]'
                    }
                `}
            >
                {/* Handles ReactFlow */}
                <Handle type="target" position={Position.Left} className="!bg-blue-400 !border-blue-300 !w-2.5 !h-2.5" />
                <Handle type="source" position={Position.Right} className="!bg-blue-400 !border-blue-300 !w-2.5 !h-2.5" />
                <Handle type="target" position={Position.Top} className="!bg-blue-400 !border-blue-300 !w-2.5 !h-2.5" id="top-in" />
                <Handle type="source" position={Position.Bottom} className="!bg-blue-400 !border-blue-300 !w-2.5 !h-2.5" id="bot-out" />

                {/* Ícone de poste simplificado (SVG inline) */}
                <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
                    <rect x="12" y="2" width="4" height="20" rx="2" fill={isOverloaded ? '#ef4444' : '#3b82f6'} opacity="0.8" />
                    <rect x="5" y="6" width="18" height="2" rx="1" fill={isOverloaded ? '#fca5a5' : '#60a5fa'} />
                    <rect x="8" y="10" width="12" height="2" rx="1" fill={isOverloaded ? '#fecaca' : '#93c5fd'} />
                </svg>
            </div>

            {/* Esforço mecânico resultante */}
            <div className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full shadow-md ${effortBadgeClass(effort, isOverloaded)}`}>
                {effort.toFixed(1)} daN
            </div>

            {/* Percentual de utilização — visível apenas quando disponível */}
            {utilization > 0 && (
                <div className={`text-[10px] px-1.5 py-0 rounded-full ${isOverloaded ? 'text-red-600 font-bold' : 'text-slate-500 font-medium'}`}>
                    {utilization.toFixed(1)}%
                </div>
            )}
        </div>
    );
}
