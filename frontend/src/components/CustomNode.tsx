import { Handle, Position } from '@xyflow/react';

// ── TIPOS ──────────────────────────────────────────────────────────────────
export interface PoleNodeData extends Record<string, unknown> {
    label: string;
    effort_dan: number;
    pole_type?: string;
}

// ── HELPERS ────────────────────────────────────────────────────────────────
/**
 * Determina a cor do badge de esforço:
 *  verde  → seguro (< 80% da resistência)
 *  amarelo→ atenção (80-99%)
 *  vermelho → crítico (≥ 100%)
 * Sem limite de resistência disponível no nó, usamos threshold visual simples.
 */
function effortBadgeClass(effort: number): string {
    if (effort > 500) return 'bg-red-500/90 text-white';
    if (effort > 300) return 'bg-amber-400/90 text-slate-900';
    return 'bg-emerald-500/90 text-white';
}

// ── COMPONENTE ─────────────────────────────────────────────────────────────
export default function CustomNode({ data }: { data: PoleNodeData }) {
    const effort = data.effort_dan ?? 0;

    return (
        <div className="flex flex-col items-center gap-1 select-none">

            {/* Label (nome do poste) — ACIMA do desenho */}
            <span className="text-[10px] font-semibold text-slate-600 bg-white/80 px-2 py-0.5 rounded-full border border-slate-200 shadow-sm whitespace-nowrap">
                {data.label}
            </span>

            {/* Corpo do nó 2.5D — círculo Glassmorphism */}
            <div
                className="
          relative flex items-center justify-center
          w-14 h-14 rounded-full
          bg-gradient-to-br from-white/80 to-blue-50/60
          border-2 border-blue-300/60
          shadow-[0_4px_16px_rgba(59,130,246,0.25),inset_0_2px_4px_rgba(255,255,255,0.8)]
          transition-all duration-200 hover:shadow-[0_6px_24px_rgba(59,130,246,0.4)]
        "
            >
                {/* Handles ReactFlow */}
                <Handle type="target" position={Position.Left} className="!bg-blue-400 !border-blue-300 !w-2.5 !h-2.5" />
                <Handle type="source" position={Position.Right} className="!bg-blue-400 !border-blue-300 !w-2.5 !h-2.5" />
                <Handle type="target" position={Position.Top} className="!bg-blue-400 !border-blue-300 !w-2.5 !h-2.5" id="top-in" />
                <Handle type="source" position={Position.Bottom} className="!bg-blue-400 !border-blue-300 !w-2.5 !h-2.5" id="bot-out" />

                {/* Ícone de poste simplificado (SVG inline) */}
                <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
                    <rect x="12" y="2" width="4" height="20" rx="2" fill="#3b82f6" opacity="0.8" />
                    <rect x="5" y="6" width="18" height="2" rx="1" fill="#60a5fa" />
                    <rect x="8" y="10" width="12" height="2" rx="1" fill="#93c5fd" />
                </svg>
            </div>

            {/* ⬇ ESFORÇO MECÂNICO RESULTANTE — OBRIGATORIAMENTE ABAIXO DO NÓ ⬇ */}
            <div className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full shadow-md ${effortBadgeClass(effort)}`}>
                {effort.toFixed(1)} daN
            </div>

        </div>
    );
}
