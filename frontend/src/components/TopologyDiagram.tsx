import { useCallback, useEffect, useMemo, useState } from 'react';
import {
    ReactFlow,
    Controls,
    Background,
    MiniMap,
    type Node,
    type Edge,
    type NodeChange,
    applyNodeChanges,
    ReactFlowProvider,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '../api';
import { useUIStore } from '../store';
import CustomNode, { type PoleNodeData } from './CustomNode';
import CustomEdge, { type ConductorEdgeData } from './CustomEdge';

// ── TIPOS DA RESPOSTA DA API ─────────────────────────────────────────────
interface ApiNode {
    id: string;
    position: { x: number; y: number };
    data: PoleNodeData;
}

interface ApiEdge {
    id: string;
    source: string;
    target: string;
    mt_label?: string;
    mt_sag_m?: number;
    bt_label?: string;
    bt_sag_m?: number;
    span_length_m?: number;
}

// ── COMPONENTE INTERNO (dentro do ReactFlowProvider) ─────────────────────
function TopologyCanvas({ projectId }: { projectId: number }) {
    const nodeTypes = useMemo(() => ({ pole: CustomNode }), []);
    const edgeTypes = useMemo(() => ({ conductors: CustomEdge }), []);

    // ── Fetch da topologia calculada pelo Smart Backend ──────────────────
    const { data: topology, isLoading, isError } = useQuery({
        queryKey: ['topology', projectId],
        queryFn: () => api.get(`/topology/project/${projectId}`).then(r => r.data),
        enabled: !!projectId,
        refetchOnWindowFocus: false,
    });

    // ── Mutation silenciosa: persiste posição XY após drag ───────────────
    const patchPosition = useMutation({
        mutationFn: ({ nodeId, pos_x, pos_y }: { nodeId: number; pos_x: number; pos_y: number }) =>
            api.patch(`/projects/${projectId}/nodes/${nodeId}/position`, { pos_x, pos_y }),
        // Silenciosa: sem invalidação de cache para não causar re-render durante drag
    });

    // ── Estado local dos nós (permite drag sem refetch) ────────────────
    const [localNodes, setLocalNodes] = useState<Node<PoleNodeData>[]>([]);

    // Converte resposta da API para o formato do React Flow
    const apiMappedNodes = useMemo<Node<PoleNodeData>[]>(() => {
        const apiNodes: ApiNode[] = topology?.nodes ?? [];
        return apiNodes.map((n) => ({
            id: n.id,
            type: 'pole' as const,
            position: n.position,
            data: n.data,
        }));
    }, [topology]);

    // Sincroniza nós da API com estado local apenas quando topologia muda
    // (Não sobrescreve drag feito pelo usuário durante a sessão)
    useEffect(() => {
        if (apiMappedNodes.length > 0) {
            setLocalNodes(apiMappedNodes);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [topology]);

    // ── Callback: atualiza posição local e persiste no backend ───────────────
    const onNodeDragStop = useCallback(
        (_event: React.MouseEvent, node: Node<PoleNodeData>) => {
            // Atualiza estado local imediatamente
            setLocalNodes(prev =>
                prev.map(n => n.id === node.id ? { ...n, position: node.position } : n)
            );
            // Persiste silenciosamente no backend
            const nodeId = parseInt(node.id, 10);
            if (!isNaN(nodeId)) {
                patchPosition.mutate({
                    nodeId,
                    pos_x: node.position.x,
                    pos_y: node.position.y,
                });
            }
        },
        [patchPosition]
    );

    // ── Mapeia arestas da API → Edge do React Flow ───────────────────────
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

    if (apiMappedNodes.length === 0 && !isLoading) {
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
        <ReactFlow
            nodes={localNodes}
            edges={reactFlowEdges}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            onNodeDragStop={onNodeDragStop}
            onNodesChange={(changes: NodeChange<Node<PoleNodeData>>[]) => {
                setLocalNodes(prev => applyNodeChanges(changes, prev));
            }}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            className="rounded-xl"
        >
            <Background gap={20} size={1} color="#e2e8f0" />

            <Controls
                className="!bg-white/80 !border-slate-200 !shadow-md !rounded-lg"
                showInteractive={false}
            />

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
    );
}

// ── COMPONENTE PÚBLICO ───────────────────────────────────────────────────
export default function TopologyDiagram() {
    const { selectedProjectId } = useUIStore();

    if (!selectedProjectId) {
        return (
            <div className="flex flex-col items-center justify-center h-64 gap-2 text-slate-400">
                <svg className="w-10 h-10 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                        d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
                <p className="text-sm">Selecione um projeto no menu lateral para visualizar a topologia.</p>
            </div>
        );
    }

    return (
        <div
            className="w-full rounded-2xl overflow-hidden border border-white/60 shadow-xl bg-slate-50/80"
            style={{ minHeight: '620px', height: '70vh' }}
        >
            {/* ReactFlowProvider necessário para usar múltiplas instâncias ou custom hooks */}
            <ReactFlowProvider>
                <TopologyCanvas projectId={selectedProjectId} />
            </ReactFlowProvider>
        </div>
    );
}
