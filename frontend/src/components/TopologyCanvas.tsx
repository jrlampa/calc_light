/**
 * TopologyCanvas — inner React Flow canvas component wrapped in ReactFlowProvider.
 * Handles: topology fetch, undo/redo sync, drag-stop persist, nudge, onConnect
 * (conductor inheritance), drop-on-pane Ghost Node modal.
 *
 * Extracted from TopologyDiagram.tsx (Phase 20 — SRP / Regra dos 500 linhas).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
    ReactFlow,
    Controls,
    Background,
    MiniMap,
    type Node,
    type Edge,
    type NodeChange,
    type Connection,
    type OnConnectStartParams,
    applyNodeChanges,
    useReactFlow,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useHotkeys } from 'react-hotkeys-hook';
import { toast } from 'sonner';
import { api } from '../api';
import { useUIStore, useTopologyHistoryStore, type PersistedNode, type PersistedEdge } from '../store';
import CustomNode, { type PoleNodeData } from './CustomNode';
import CustomEdge, { type ConductorEdgeData } from './CustomEdge';
import GhostNodeModal, { type GhostNodeChoice } from './GhostNodeModal';

// ── TIPOS DA RESPOSTA DA API ─────────────────────────────────────────────

export interface ApiNode {
    id: string;
    position: { x: number; y: number };
    data: PoleNodeData;
}

export interface ApiEdge {
    id: string;
    source: string;
    target: string;
    mt_label?: string;
    mt_sag_m?: number;
    bt_label?: string;
    bt_sag_m?: number;
    span_length_m?: number;
}

// Tamanho do passo de nudge (setas do teclado)
const NUDGE_PX = 10;

// ── Helpers de serialização ───────────────────────────────────────────────

function toPersistedNode(n: Node<PoleNodeData>): PersistedNode {
    return { id: n.id, position: n.position, data: n.data as Record<string, unknown> };
}

function toPersistedEdge(e: ApiEdge): PersistedEdge {
    return { id: e.id, source: e.source, target: e.target, mt_label: e.mt_label, bt_label: e.bt_label };
}

// ── COMPONENTE ────────────────────────────────────────────────────────────

export default function TopologyCanvas({ projectId }: { projectId: number }) {
    const { selectedNodeId, setSelectedNodeId } = useUIStore();
    const nodeTypes = useMemo(() => ({ pole: CustomNode }), []);
    const edgeTypes = useMemo(() => ({ conductors: CustomEdge }), []);
    const queryClient = useQueryClient();
    const { screenToFlowPosition } = useReactFlow();

    // ── History store (Phase 18 — undo/redo) ─────────────────────────────
    const { setTopologySnapshot, nodes: historyNodes, projectId: historyProjectId } =
        useTopologyHistoryStore();
    const lastPushedRef = useRef<string>('');

    // ── Estado para modal de Ghost Node (drop-on-pane) ───────────────────
    const [showGhostModal, setShowGhostModal] = useState(false);
    const connectSourceRef = useRef<string | null>(null);
    const connectDropPosRef = useRef<{ x: number; y: number }>({ x: 200, y: 200 });

    // ── Fetch da topologia calculada pelo Smart Backend ──────────────────
    const { data: topology, isLoading, isError } = useQuery({
        queryKey: ['topology', projectId],
        queryFn: () => api.get(`/topology/project/${projectId}`).then(r => r.data),
        enabled: !!projectId,
        refetchOnWindowFocus: false,
    });

    // ── Mutation silenciosa: persiste posição XY após drag ou nudge ──────
    const patchPosition = useMutation({
        mutationFn: ({ nodeId, pos_x, pos_y }: { nodeId: number; pos_x: number; pos_y: number }) =>
            api.patch(`/projects/${projectId}/nodes/${nodeId}/position`, { pos_x, pos_y }),
    });

    const [localNodes, setLocalNodes] = useState<Node<PoleNodeData>[]>([]);

    const pushToHistory = useCallback(
        (nodes: Node<PoleNodeData>[], edges: ApiEdge[]) => {
            const persisted = nodes.map(toPersistedNode);
            const serialized = JSON.stringify(persisted);
            if (serialized === lastPushedRef.current) return;
            lastPushedRef.current = serialized;
            setTopologySnapshot(projectId, persisted, edges.map(toPersistedEdge));
        },
        [projectId, setTopologySnapshot]
    );

    const apiMappedNodes = useMemo<Node<PoleNodeData>[]>(() => {
        const apiNodes: ApiNode[] = topology?.nodes ?? [];
        return apiNodes.map((n) => ({
            id: n.id,
            type: 'pole' as const,
            position: n.position,
            data: n.data,
        }));
    }, [topology]);

    useEffect(() => {
        if (apiMappedNodes.length > 0) {
            setLocalNodes(apiMappedNodes);
            pushToHistory(apiMappedNodes, topology?.edges ?? []);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [topology]);

    // Sincroniza localNodes quando undo/redo muda o historyNodes (Phase 18)
    useEffect(() => {
        if (historyProjectId !== projectId || historyNodes.length === 0) return;
        const serialized = JSON.stringify(historyNodes);
        if (serialized === lastPushedRef.current) return;
        lastPushedRef.current = serialized;
        setLocalNodes(
            historyNodes.map(pn => ({
                id: pn.id,
                type: 'pole' as const,
                position: pn.position,
                data: pn.data as PoleNodeData,
            }))
        );
    }, [historyNodes, historyProjectId, projectId]);

    const onNodeDragStop = useCallback(
        (_event: React.MouseEvent, node: Node<PoleNodeData>) => {
            setLocalNodes(prev => {
                const next = prev.map(n => n.id === node.id ? { ...n, position: node.position } : n);
                pushToHistory(next, topology?.edges ?? []);
                return next;
            });
            const nodeId = parseInt(node.id, 10);
            if (!isNaN(nodeId)) {
                patchPosition.mutate({ nodeId, pos_x: node.position.x, pos_y: node.position.y });
            }
        },
        [patchPosition, pushToHistory, topology?.edges]
    );

    const nudgeSelectedNode = useCallback(
        (dx: number, dy: number) => {
            if (!selectedNodeId) return;
            const selectedIdStr = String(selectedNodeId);
            let newPos = { x: 0, y: 0 };
            setLocalNodes(prev => {
                const next = prev.map(n => {
                    if (n.id === selectedIdStr) {
                        newPos = { x: n.position.x + dx, y: n.position.y + dy };
                        return { ...n, position: newPos };
                    }
                    return n;
                });
                pushToHistory(next, topology?.edges ?? []);
                return next;
            });
            patchPosition.mutate({ nodeId: selectedNodeId, pos_x: newPos.x, pos_y: newPos.y });
        },
        [selectedNodeId, patchPosition, pushToHistory, topology?.edges]
    );

    const onConnect = useCallback(
        async (params: Connection) => {
            if (!params.source || !params.target) return;
            const sourceId = parseInt(params.source, 10);
            const targetId = parseInt(params.target, 10);
            if (isNaN(sourceId) || isNaN(targetId)) return;

            let mtConductorId: number | null = null;
            let mtSagM = 0.0;
            let btConductorId: number | null = null;
            let btSagM = 0.0;
            let inherited = false;

            try {
                const res = await api.get(`/projects/${projectId}/nodes/${sourceId}/outgoing-conductors`);
                const conds = res.data;
                if (conds.mt_conductor_id || conds.bt_conductor_id) {
                    mtConductorId = conds.mt_conductor_id;
                    mtSagM = conds.mt_sag_m ?? 0.0;
                    btConductorId = conds.bt_conductor_id;
                    btSagM = conds.bt_sag_m ?? 0.0;
                    inherited = true;
                }
            } catch { /* sem herança — continua sem cabos */ }

            try {
                await api.post(`/projects/${projectId}/edges`, {
                    source_node_id: sourceId,
                    target_node_id: targetId,
                    mt_conductor_id: mtConductorId,
                    mt_sag_m: mtSagM,
                    bt_conductor_id: btConductorId,
                    bt_sag_m: btSagM,
                    span_length_m: 50.0,
                    angle_deg: 0.0,
                });
                if (inherited) {
                    toast.success('Vão criado com condutores herdados automaticamente!');
                } else {
                    toast('Vão criado. Configure os condutores na aba de Dados.', { icon: '🔌' });
                }
                queryClient.invalidateQueries({ queryKey: ['topology', projectId] });
            } catch {
                toast.error('Erro ao criar vão. Verifique se os postes são do mesmo projeto.');
            }
        },
        [projectId, queryClient]
    );

    const onConnectStart = useCallback(
        (_: React.MouseEvent | React.TouchEvent, params: OnConnectStartParams) => {
            connectSourceRef.current = params.nodeId ?? null;
        },
        []
    );

    const onConnectEnd = useCallback(
        (event: MouseEvent | TouchEvent) => {
            if (!connectSourceRef.current) return;
            const target = event.target as Element;
            if (target.closest('.react-flow__node') || target.closest('.react-flow__handle')) return;
            const clientX = 'changedTouches' in event
                ? (event as TouchEvent).changedTouches[0].clientX
                : (event as MouseEvent).clientX;
            const clientY = 'changedTouches' in event
                ? (event as TouchEvent).changedTouches[0].clientY
                : (event as MouseEvent).clientY;
            connectDropPosRef.current = screenToFlowPosition({ x: clientX, y: clientY });
            setShowGhostModal(true);
        },
        [screenToFlowPosition]
    );

    const handleGhostChoice = useCallback(
        async (choice: GhostNodeChoice) => {
            setShowGhostModal(false);
            const sourceId = connectSourceRef.current;
            if (!sourceId) return;
            const isGhost = choice === 'ghost';
            const label = isGhost ? 'Rede Existente' : 'Novo Poste';
            const { x, y } = connectDropPosRef.current;
            try {
                const nodeRes = await api.post(`/projects/${projectId}/nodes`, {
                    project_id: projectId, pole_id: 0, label, pos_x: x, pos_y: y, is_ghost: isGhost,
                });
                await api.post(`/projects/${projectId}/edges`, {
                    source_node_id: parseInt(sourceId, 10),
                    target_node_id: nodeRes.data.id,
                    span_length_m: 50.0,
                    angle_deg: 0.0,
                });
                queryClient.invalidateQueries({ queryKey: ['topology', projectId] });
                toast.success(isGhost
                    ? 'Nó Fantasma (Rede Existente) criado e conectado.'
                    : 'Novo Poste criado e conectado. Configure os cabos na aba de Dados.'
                );
            } catch {
                toast.error('Erro ao criar nó. Tente novamente.');
            } finally {
                connectSourceRef.current = null;
            }
        },
        [projectId, queryClient]
    );

    // ── Atalhos de teclado ────────────────────────────────────────────────
    const nudgeOpts = { preventDefault: true, enabled: !!selectedNodeId } as const;
    useHotkeys('up',    () => nudgeSelectedNode(0, -NUDGE_PX), nudgeOpts);
    useHotkeys('down',  () => nudgeSelectedNode(0,  NUDGE_PX), nudgeOpts);
    useHotkeys('left',  () => nudgeSelectedNode(-NUDGE_PX, 0), nudgeOpts);
    useHotkeys('right', () => nudgeSelectedNode( NUDGE_PX, 0), nudgeOpts);
    useHotkeys(
        ['delete', 'backspace'],
        () => {
            if (!selectedNodeId) return;
            const node = localNodes.find(n => n.id === String(selectedNodeId));
            const label = (node?.data as PoleNodeData)?.label ?? `Nó ${selectedNodeId}`;
            setLocalNodes(prev => prev.filter(n => n.id !== String(selectedNodeId)));
            setSelectedNodeId(null);
            toast.warning(`"${label}" removido da visualização.`, {
                description: 'Para remover permanentemente, use a aba de Dados.',
                duration: 5000,
            });
        },
        { enabled: !!selectedNodeId }
    );

    // ── Arestas mapeadas ─────────────────────────────────────────────────
    const reactFlowEdges: Edge<ConductorEdgeData>[] = useMemo(
        () => (topology?.edges ?? []).map((e: ApiEdge) => ({
            id: e.id,
            source: e.source,
            target: e.target,
            type: 'conductors' as const,
            animated: true,
            data: {
                mt_conductor: e.mt_label,
                mt_sag_m: e.mt_sag_m,
                bt_conductor: e.bt_label,
                bt_sag_m: e.bt_sag_m,
                span_length_m: e.span_length_m,
            },
        })),
        [topology]
    );

    // ── Estados de carregamento / erro ───────────────────────────────────
    if (isLoading) {
        return (
            <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-500">
                <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                <span className="text-sm animate-pulse">Calculando topologia no Smart Backend...</span>
            </div>
        );
    }
    if (isError) {
        return (
            <div className="flex items-center justify-center h-full text-red-400 text-sm">
                Erro ao carregar a topologia. Verifique se o backend está rodando.
            </div>
        );
    }
    if (apiMappedNodes.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center h-full gap-2 text-slate-400">
                <svg className="w-12 h-12 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                        d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6-10l6-3m6 16l-5.447-2.724A1 1 0 0115 16.382V5.618a1 1 0 011.447-.894L21 7m0 13V7" />
                </svg>
                <p className="text-sm">Nenhum poste cadastrado ainda.</p>
                <p className="text-xs text-slate-300">Vá para a Aba 1 e adicione postes para visualizar a rede aqui.</p>
            </div>
        );
    }

    return (
        <>
            <ReactFlow
                nodes={localNodes}
                edges={reactFlowEdges}
                nodeTypes={nodeTypes}
                edgeTypes={edgeTypes}
                onNodeDragStop={onNodeDragStop}
                onConnect={onConnect}
                onConnectStart={onConnectStart}
                onConnectEnd={onConnectEnd}
                onNodeClick={(_event, node) => {
                    const nodeId = parseInt(node.id, 10);
                    if (!isNaN(nodeId)) {
                        setSelectedNodeId(nodeId);
                        toast(`Poste selecionado: ${(node.data as PoleNodeData).label}`, {
                            icon: '📍',
                            duration: 2000,
                        });
                    }
                }}
                onNodesChange={(changes: NodeChange<Node<PoleNodeData>>[]) => {
                    setLocalNodes(prev => applyNodeChanges(changes, prev));
                }}
                fitView
                fitViewOptions={{ padding: 0.2 }}
                className="rounded-xl"
            >
                <Background gap={20} size={1} color="#e2e8f0" />
                <Controls className="!bg-white/80 !border-slate-200 !shadow-md !rounded-lg" showInteractive={false} />
                <MiniMap
                    nodeColor={(n) => {
                        const effort = (n.data as PoleNodeData)?.effort_dan ?? 0;
                        if (effort > 500) return '#ef4444';
                        if (effort > 300) return '#f59e0b';
                        return '#10b981';
                    }}
                    className="!bg-white/80 !border-slate-200 !rounded-lg !shadow-md"
                    maskColor="rgba(148,163,184,0.1)"
                />
            </ReactFlow>

            {showGhostModal && (
                <GhostNodeModal
                    onChoose={handleGhostChoice}
                    onClose={() => { setShowGhostModal(false); connectSourceRef.current = null; }}
                />
            )}
        </>
    );
}
