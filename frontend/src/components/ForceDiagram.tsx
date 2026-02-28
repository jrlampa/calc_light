import { useMemo, useState } from 'react';
import { useUIStore } from '../store';
import { useNodeForces, type ForceVector } from '../hooks/useNodeForces';
import { useProjectNodes } from '../hooks/useProjects';

// ── CONSTANTES ────────────────────────────────────────────────────────────
const SVG_SIZE = 480;
const ORIGIN = SVG_SIZE / 2;
const PADDING = 60;
const PLOT_AREA = (SVG_SIZE / 2) - PADDING;

// Paleta de cores por nível
const LEVEL_COLORS: Record<string, string> = {
    MT1: '#3b82f6',   // Azul
    MT2: '#6366f1',   // Índigo
    BT: '#10b981',   // Verde
    RAMAIS: '#f59e0b',   // Âmbar
    WIND: '#94a3b8',   // Cinza
    RESULT: '#ef4444',   // Vermelho — resultante
};

function levelLabel(level: string): string {
    const map: Record<string, string> = {
        MT1: 'Tração MT1', MT2: 'Tração MT2',
        BT: 'Tração BT', RAMAIS: 'Ramais',
        WIND: 'Vento', RESULT: 'Resultante Total',
    };
    return map[level] ?? level;
}

// ── ESCALA: mapeia daN para pixels ───────────────────────────────────────
function buildScale(vectors: ForceVector[]): number {
    const maxMag = Math.max(...vectors.map(v => v.magnitude_dan), 1);
    return PLOT_AREA / maxMag;
}

// ── ARROW HEAD (ponta da seta em SVG) ───────────────────────────────────
function arrowHead(x1: number, y1: number, x2: number, y2: number, color: string, isResult: boolean) {
    const angle = Math.atan2(y2 - y1, x2 - x1);
    const size = isResult ? 14 : 10;
    const p1x = x2 - size * Math.cos(angle - 0.4);
    const p1y = y2 - size * Math.sin(angle - 0.4);
    const p2x = x2 - size * Math.cos(angle + 0.4);
    const p2y = y2 - size * Math.sin(angle + 0.4);
    return (
        <polygon
            points={`${x2},${y2} ${p1x},${p1y} ${p2x},${p2y}`}
            fill={color}
            stroke="none"
        />
    );
}

// ── COMPONENTE DO VETOR ───────────────────────────────────────────────────
function VectorArrow({
    vec, scale, isResult, onHover, onLeave,
}: {
    vec: ForceVector;
    scale: number;
    isResult: boolean;
    onHover: (v: ForceVector) => void;
    onLeave: () => void;
}) {
    const color = LEVEL_COLORS[vec.level] ?? '#64748b';
    const dx = vec.component_x * scale;
    const dy = -vec.component_y * scale; // SVG: y cresce para baixo → invertemos
    const x2 = ORIGIN + dx;
    const y2 = ORIGIN + dy;
    const strokeW = isResult ? 3.5 : 2;
    const filter = isResult ? `drop-shadow(0 0 6px ${color})` : undefined;

    return (
        <g
            style={{ cursor: 'pointer', filter }}
            onMouseEnter={() => onHover(vec)}
            onMouseLeave={onLeave}
        >
            <line
                x1={ORIGIN} y1={ORIGIN}
                x2={x2} y2={y2}
                stroke={color}
                strokeWidth={strokeW}
                strokeLinecap="round"
                strokeDasharray={isResult ? undefined : '6 3'}
                opacity={isResult ? 1 : 0.8}
            />
            {arrowHead(ORIGIN, ORIGIN, x2, y2, color, isResult)}
        </g>
    );
}

// ── COMPONENTE PRINCIPAL ──────────────────────────────────────────────────
export default function ForcesDiagram() {
    const { selectedProjectId, selectedNodeId, setSelectedNodeId } = useUIStore();
    const { data: nodes = [] } = useProjectNodes(selectedProjectId);
    const { data: vectors, isLoading, isError } = useNodeForces(selectedNodeId);
    const [hovered, setHovered] = useState<ForceVector | null>(null);

    const scale = useMemo(
        () => vectors ? buildScale(vectors) : 1,
        [vectors]
    );

    // Separa os vetores parciais do resultante
    const partials = useMemo(() => vectors?.filter(v => v.level !== 'RESULT') ?? [], [vectors]);
    const resultant = useMemo(() => vectors?.find(v => v.level === 'RESULT'), [vectors]);

    // ── Grid labels (eixos) ───────────────────────────────────────────────
    const gridLines = [0.25, 0.5, 0.75, 1.0].map(frac => PLOT_AREA * frac);

    return (
        <div className="flex flex-col lg:flex-row gap-6">

            {/* ── Seletor de Nó (Poste) ───────────────────────────────────── */}
            <div className="w-full lg:w-64 bg-white/60 backdrop-blur-md border border-white/60 shadow-lg rounded-2xl p-5 flex flex-col gap-4">
                <h3 className="text-sm font-semibold text-slate-700 border-b border-slate-200 pb-2">
                    Selecione o Poste para Análise
                </h3>

                {nodes.length === 0 ? (
                    <p className="text-xs text-slate-400">Nenhum poste cadastrado no projeto.</p>
                ) : (
                    <ul className="space-y-2">
                        {nodes.map(node => (
                            <li key={node.id}>
                                <button
                                    onClick={() => setSelectedNodeId(node.id)}
                                    className={`w-full text-left px-4 py-2.5 rounded-xl text-sm font-medium transition-all border
                    ${selectedNodeId === node.id
                                            ? 'bg-blue-600 text-white border-blue-500 shadow-md shadow-blue-300/40'
                                            : 'bg-white/50 text-slate-700 border-slate-200 hover:bg-white hover:border-blue-300'
                                        }`}
                                >
                                    {node.label}
                                </button>
                            </li>
                        ))}
                    </ul>
                )}

                {/* Legenda dos Vetores */}
                {vectors && vectors.length > 0 && (
                    <div className="mt-auto pt-4 border-t border-slate-200 space-y-1.5">
                        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Legenda</p>
                        {Object.entries(LEVEL_COLORS).map(([level, color]) => {
                            const hasVector = vectors.some(v => v.level === level);
                            if (!hasVector) return null;
                            return (
                                <div key={level} className="flex items-center gap-2 text-xs text-slate-600">
                                    <div className="w-6 h-0.5 rounded-full" style={{ backgroundColor: color, height: level === 'RESULT' ? '3px' : '1.5px' }} />
                                    <span>{levelLabel(level)}</span>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* ── Diagrama SVG ─────────────────────────────────────────────── */}
            <div className="flex-1 bg-white/60 backdrop-blur-md border border-white/60 shadow-lg rounded-2xl p-5">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold text-slate-800">
                        Diagrama de Forças Mecânicas
                        {selectedNodeId && nodes.find(n => n.id === selectedNodeId) && (
                            <span className="ml-2 text-sm font-normal text-slate-500">
                                — {nodes.find(n => n.id === selectedNodeId)?.label}
                            </span>
                        )}
                    </h2>
                    {resultant && (
                        <div className="bg-red-50 border border-red-200 text-red-700 text-sm font-bold px-4 py-1.5 rounded-xl shadow-sm">
                            Resultante: {resultant.magnitude_dan.toFixed(1)} daN
                        </div>
                    )}
                </div>

                {/* Estados vazios / loading */}
                {!selectedNodeId && (
                    <div className="flex items-center justify-center h-80 text-slate-400 text-sm">
                        ← Selecione um poste para visualizar o diagrama de forças.
                    </div>
                )}

                {selectedNodeId && isLoading && (
                    <div className="flex items-center justify-center h-80 gap-3 text-slate-500 text-sm animate-pulse">
                        <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                        Calculando vetores no Smart Backend...
                    </div>
                )}

                {selectedNodeId && isError && (
                    <div className="flex items-center justify-center h-80 text-red-400 text-sm">
                        Erro ao buscar vetores. Verifique se o backend está ativo.
                    </div>
                )}

                {selectedNodeId && !isLoading && vectors && vectors.length === 0 && (
                    <div className="flex items-center justify-center h-80 text-slate-400 text-sm">
                        Nenhum vão conectado a este poste ainda. Conecte vãos na Aba 1.
                    </div>
                )}

                {/* ── SVG Cartesiano ───────────────────────────────────────── */}
                {selectedNodeId && !isLoading && vectors && vectors.length > 0 && (
                    <>
                        <svg
                            width={SVG_SIZE} height={SVG_SIZE}
                            viewBox={`0 0 ${SVG_SIZE} ${SVG_SIZE}`}
                            className="mx-auto block"
                            style={{ maxWidth: '100%', height: 'auto' }}
                        >
                            {/* Grid de fundo */}
                            {gridLines.map(r => (
                                <g key={r}>
                                    <circle cx={ORIGIN} cy={ORIGIN} r={r} fill="none" stroke="#e2e8f0" strokeWidth={1} strokeDasharray="4 4" />
                                    <text x={ORIGIN + r} y={ORIGIN - 4} fontSize={9} fill="#94a3b8" textAnchor="middle">
                                        {(r / scale).toFixed(0)}
                                    </text>
                                </g>
                            ))}

                            {/* Eixos X e Y */}
                            <line x1={PADDING} y1={ORIGIN} x2={SVG_SIZE - PADDING} y2={ORIGIN} stroke="#cbd5e1" strokeWidth={1.5} />
                            <line x1={ORIGIN} y1={PADDING} x2={ORIGIN} y2={SVG_SIZE - PADDING} stroke="#cbd5e1" strokeWidth={1.5} />

                            {/* Labels dos eixos */}
                            <text x={SVG_SIZE - PADDING + 8} y={ORIGIN + 4} fontSize={10} fill="#94a3b8">X</text>
                            <text x={ORIGIN + 4} y={PADDING - 8} fontSize={10} fill="#94a3b8">Y</text>

                            {/* Vetores parciais (tracejados) */}
                            {partials.map((vec, i) => (
                                <VectorArrow
                                    key={i}
                                    vec={vec}
                                    scale={scale}
                                    isResult={false}
                                    onHover={setHovered}
                                    onLeave={() => setHovered(null)}
                                />
                            ))}

                            {/* Vetor resultante (destaque visual 2.5D) */}
                            {resultant && (
                                <VectorArrow
                                    vec={resultant}
                                    scale={scale}
                                    isResult
                                    onHover={setHovered}
                                    onLeave={() => setHovered(null)}
                                />
                            )}

                            {/* Ponto de origem */}
                            <circle cx={ORIGIN} cy={ORIGIN} r={5} fill="#1e3a5f" />
                        </svg>

                        {/* Tooltip de hover */}
                        {hovered && (
                            <div className="mt-3 mx-auto w-fit bg-slate-800 text-white rounded-xl px-5 py-3 text-sm shadow-xl">
                                <div className="font-bold text-base mb-1">{levelLabel(hovered.level)}</div>
                                <div className="text-slate-300 space-y-0.5">
                                    <div>Magnitude: <span className="text-white font-semibold">{hovered.magnitude_dan.toFixed(2)} daN</span></div>
                                    <div>Ângulo: <span className="text-white font-semibold">{hovered.angle_deg.toFixed(1)}°</span></div>
                                    <div>Comp. X: <span className="text-slate-200">{hovered.component_x.toFixed(2)} daN</span></div>
                                    <div>Comp. Y: <span className="text-slate-200">{hovered.component_y.toFixed(2)} daN</span></div>
                                </div>
                            </div>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}
