import { BaseEdge, EdgeLabelRenderer, getBezierPath, type EdgeProps } from '@xyflow/react';

// ── TIPOS ──────────────────────────────────────────────────────────────────
export interface ConductorEdgeData extends Record<string, unknown> {
    // Média Tensão
    mt_conductor?: string;
    mt_sag_m?: number;
    // Baixa Tensão
    bt_conductor?: string;
    bt_sag_m?: number;
    // Metadados
    span_length_m?: number;
    angle_deg?: number;
}

// ── COMPONENTE ─────────────────────────────────────────────────────────────
export default function CustomEdge({
    id,
    sourceX, sourceY, targetX, targetY,
    sourcePosition, targetPosition,
    style = {},
    markerEnd,
    data,
}: EdgeProps) {
    const edgeData = data as ConductorEdgeData | undefined;

    const [edgePath, labelX, labelY] = getBezierPath({
        sourceX, sourceY, sourcePosition,
        targetX, targetY, targetPosition,
    });

    const hasMT = !!(edgeData?.mt_conductor);
    const hasBT = !!(edgeData?.bt_conductor);

    return (
        <>
            {/* Linha do vão */}
            <BaseEdge
                id={id}
                path={edgePath}
                markerEnd={markerEnd}
                style={{
                    ...style,
                    strokeWidth: 2.5,
                    stroke: hasMT ? '#3b82f6' : '#10b981',
                    strokeDasharray: hasBT && !hasMT ? '6 3' : undefined,
                }}
            />

            {/* Labels injetados via EdgeLabelRenderer (HTML sobre SVG) */}
            <EdgeLabelRenderer>
                <div
                    className="nodrag nopan pointer-events-none"
                    style={{
                        position: 'absolute',
                        transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: '4px',
                    }}
                >
                    {/* ─── TOPO: Condutor MT + Flecha MT ─────────────────── */}
                    {hasMT && (
                        <div className="flex flex-col items-center -translate-y-8">
                            {/* Flecha MT — acima do rótulo do condutor */}
                            {edgeData?.mt_sag_m !== undefined && (
                                <span className="text-[9px] text-blue-400/80 font-medium leading-none mb-0.5">
                                    f={edgeData.mt_sag_m}m
                                </span>
                            )}
                            {/* Rótulo do Condutor MT */}
                            <span className="text-[10px] font-bold text-blue-500 bg-white/90 border border-blue-200 px-2 py-0.5 rounded shadow-sm whitespace-nowrap">
                                MT · {edgeData?.mt_conductor}
                            </span>
                        </div>
                    )}

                    {/* Comprimento central (info extra) */}
                    {edgeData?.span_length_m && (
                        <span className="text-[9px] text-slate-400 bg-white/70 px-1 rounded">
                            {edgeData.span_length_m}m
                        </span>
                    )}

                    {/* ─── FUNDO: Condutor BT + Flecha BT ─────────────────── */}
                    {hasBT && (
                        <div className="flex flex-col items-center translate-y-8">
                            {/* Rótulo do Condutor BT */}
                            <span className="text-[10px] font-bold text-emerald-600 bg-white/90 border border-emerald-200 px-2 py-0.5 rounded shadow-sm whitespace-nowrap">
                                BT · {edgeData?.bt_conductor}
                            </span>
                            {/* Flecha BT — abaixo do rótulo */}
                            {edgeData?.bt_sag_m !== undefined && (
                                <span className="text-[9px] text-emerald-400/80 font-medium leading-none mt-0.5">
                                    f={edgeData.bt_sag_m}m
                                </span>
                            )}
                        </div>
                    )}
                </div>
            </EdgeLabelRenderer>
        </>
    );
}
