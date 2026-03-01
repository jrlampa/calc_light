/**
 * CanvasPersistenceBar.tsx — Fase 23
 *
 * Barra de persistência do canvas React Flow.
 * Botões: 💾 Guardar | 📂 Carregar
 *
 * Serializa nodes + edges + viewport (zoom/pan) e persiste no backend.
 * Ao carregar, restaura o canvas e ajusta o viewport via ReactFlow instance.
 */
import { useState, useCallback } from 'react';
import { useReactFlow, type Node, type Edge, type Viewport } from '@xyflow/react';
import { toast } from 'sonner';
import { saveCanvas, loadCanvas } from '../api';
import { useTopologyHistoryStore } from '../store';
import type { PoleNodeData } from './CustomNode';
import type { ConductorEdgeData } from './CustomEdge';

interface CanvasPersistenceBarProps {
    projectId: number;
    /** Função para forçar a actualização dos nós locais após um load */
    onLoad: (nodes: Node<PoleNodeData>[], edges: Edge<ConductorEdgeData>[]) => void;
}

export default function CanvasPersistenceBar({ projectId, onLoad }: CanvasPersistenceBarProps) {
    const [isSaving, setIsSaving] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const { getNodes, getEdges, getViewport, setViewport } = useReactFlow();
    const { setTopologySnapshot } = useTopologyHistoryStore();

    // ── 💾 Guardar ──────────────────────────────────────────────────────────
    const handleSave = useCallback(async () => {
        if (isSaving || isLoading) return;
        setIsSaving(true);
        try {
            const nodes = getNodes() as Node<PoleNodeData>[];
            const edges = getEdges() as Edge<ConductorEdgeData>[];
            const viewport: Viewport = getViewport();

            await saveCanvas(projectId, {
                nodes: nodes.map(n => ({
                    id: n.id,
                    type: n.type,
                    position: n.position,
                    data: n.data,
                })),
                edges: edges.map(e => ({
                    id: e.id,
                    source: e.source,
                    target: e.target,
                    type: e.type,
                    data: e.data,
                })),
                viewport,
            });

            toast.success('Projeto guardado com sucesso! 💾', { duration: 3000 });
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Erro ao guardar';
            toast.error(`Falha ao guardar: ${msg}`);
            console.error(err);
        } finally {
            setIsSaving(false);
        }
    }, [isSaving, isLoading, projectId, getNodes, getEdges, getViewport]);

    // ── 📂 Carregar ─────────────────────────────────────────────────────────
    const handleLoad = useCallback(async () => {
        if (isSaving || isLoading) return;
        setIsLoading(true);
        try {
            const result = await loadCanvas(projectId);

            if (!result.has_canvas) {
                toast.info('Nenhum canvas salvo encontrado neste projeto.', { duration: 3000 });
                return;
            }

            const nodes = result.nodes as Node<PoleNodeData>[];
            const edges = result.edges as Edge<ConductorEdgeData>[];
            const viewport = result.viewport as Viewport;

            // Inject into local state via the parent's callback
            onLoad(nodes, edges);

            // Restore viewport (zoom + pan) — o "segredo de ouro" do UX
            setViewport(viewport, { duration: 400 });

            // Persist to undo/redo store
            setTopologySnapshot(
                projectId,
                nodes.map(n => ({
                    id: n.id,
                    type: n.type ?? 'pole',
                    position: n.position,
                    data: n.data as PoleNodeData,
                })),
                edges.map(e => ({
                    id: e.id,
                    source: e.source,
                    target: e.target,
                    type: e.type ?? 'conductors',
                    data: e.data as ConductorEdgeData,
                    sourceHandle: null,
                    targetHandle: null,
                }))
            );

            toast.success('Canvas restaurado com sucesso! 📂', { duration: 3000 });
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Erro ao carregar';
            toast.error(`Falha ao carregar: ${msg}`);
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    }, [isSaving, isLoading, projectId, onLoad, setViewport, setTopologySnapshot]);

    // ── Render ───────────────────────────────────────────────────────────────
    const btnBase = [
        'flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold',
        'border transition-all duration-200 select-none',
        'disabled:opacity-50 disabled:cursor-not-allowed',
    ].join(' ');

    const btnSave = isSaving || isLoading
        ? `${btnBase} bg-slate-700/80 text-slate-400 border-slate-600`
        : `${btnBase} bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white border-white/20 hover:shadow-[0_4px_16px_rgba(16,185,129,0.4)] active:scale-95`;

    const btnLoad = isSaving || isLoading
        ? `${btnBase} bg-slate-700/80 text-slate-400 border-slate-600`
        : `${btnBase} bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white border-white/20 hover:shadow-[0_4px_16px_rgba(59,130,246,0.4)] active:scale-95`;

    const Spinner = () => (
        <span className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
    );

    return (
        <div className="flex items-center gap-2">
            {/* 💾 Guardar Projeto */}
            <button
                id="btn-guardar-canvas"
                onClick={handleSave}
                disabled={isSaving || isLoading}
                className={btnSave}
                title="Guardar o estado atual do canvas na base de dados"
            >
                {isSaving ? <Spinner /> : <span>💾</span>}
                {isSaving ? 'Guardando...' : 'Guardar'}
            </button>

            {/* 📂 Carregar Projeto */}
            <button
                id="btn-carregar-canvas"
                onClick={handleLoad}
                disabled={isSaving || isLoading}
                className={btnLoad}
                title="Restaurar o canvas salvo da base de dados"
            >
                {isLoading ? <Spinner /> : <span>📂</span>}
                {isLoading ? 'Carregando...' : 'Carregar'}
            </button>
        </div>
    );
}
