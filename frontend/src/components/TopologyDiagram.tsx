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
    ReactFlowProvider,
    useReactFlow,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useHotkeys } from 'react-hotkeys-hook';
import { toast } from 'sonner';
import { Loader2, Upload, Zap } from 'lucide-react';
import { api } from '../api';
import { useUIStore } from '../store';
import CustomNode, { type PoleNodeData } from './CustomNode';
import CustomEdge, { type ConductorEdgeData } from './CustomEdge';
import GisImportModal, { type ParsedPoint } from './GisImportModal';
import GhostNodeModal, { type GhostNodeChoice } from './GhostNodeModal';
import SolverModal from './SolverModal';

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

// Tamanho do passo de nudge (setas do teclado)
const NUDGE_PX = 10;

// ── COMPONENTE INTERNO (dentro do ReactFlowProvider) ─────────────────────
function TopologyCanvas({ projectId }: { projectId: number }) {
    const { selectedNodeId, setSelectedNodeId } = useUIStore();
    const nodeTypes = useMemo(() => ({ pole: CustomNode }), []);
    const edgeTypes = useMemo(() => ({ conductors: CustomEdge }), []);
    const queryClient = useQueryClient();
    const { screenToFlowPosition } = useReactFlow();

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

    // ── Estado local dos nós (permite drag e nudge sem refetch) ─────────
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
    useEffect(() => {
        if (apiMappedNodes.length > 0) {
            setLocalNodes(apiMappedNodes);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [topology]);

    // ── Callback: atualiza posição local e persiste no backend ──────────
    const onNodeDragStop = useCallback(
        (_event: React.MouseEvent, node: Node<PoleNodeData>) => {
            setLocalNodes(prev =>
                prev.map(n => n.id === node.id ? { ...n, position: node.position } : n)
            );
            const nodeId = parseInt(node.id, 10);
            if (!isNaN(nodeId)) {
                patchPosition.mutate({ nodeId, pos_x: node.position.x, pos_y: node.position.y });
            }
        },
        [patchPosition]
    );

    // ── Helper: mover nó selecionado por delta ───────────────────────────
    const nudgeSelectedNode = useCallback(
        (dx: number, dy: number) => {
            if (!selectedNodeId) return;
            const selectedIdStr = String(selectedNodeId);
            let newPos = { x: 0, y: 0 };

            setLocalNodes(prev => prev.map(n => {
                if (n.id === selectedIdStr) {
                    newPos = { x: n.position.x + dx, y: n.position.y + dy };
                    return { ...n, position: newPos };
                }
                return n;
            }));

            patchPosition.mutate({ nodeId: selectedNodeId, pos_x: newPos.x, pos_y: newPos.y });
        },
        [selectedNodeId, patchPosition]
    );

    // ── Herança de Condutores: ao conectar A→B herda cabos do vão de saída de A ─
    const onConnect = useCallback(
        async (params: Connection) => {
            if (!params.source || !params.target) return;
            const sourceId = parseInt(params.source, 10);
            const targetId = parseInt(params.target, 10);
            if (isNaN(sourceId) || isNaN(targetId)) return;

            // Buscar condutores do vão de saída do nó origem
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
            } catch { /* sem herança disponível — continua sem cabos */ }

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

    // ── Drop-on-Pane: captura nó de origem da aresta ─────────────────────
    const onConnectStart = useCallback((_: React.MouseEvent | React.TouchEvent, params: OnConnectStartParams) => {
        connectSourceRef.current = params.nodeId ?? null;
    }, []);

    // ── Drop-on-Pane: abre modal se aresta foi solta sem destino ─────────
    const onConnectEnd = useCallback(
        (event: MouseEvent | TouchEvent) => {
            if (!connectSourceRef.current) return;
            const target = event.target as Element;
            // Se o evento ocorreu num handle ou num nó, não é drop-on-pane
            if (target.closest('.react-flow__node') || target.closest('.react-flow__handle')) return;

            // Captura posição em coordenadas do flow para posicionar o novo nó
            // TouchEvent usa changedTouches[0] (touches[] fica vazio no touchend)
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

    // ── Criar nó (real ou ghost) após escolha do modal ───────────────────
    const handleGhostChoice = useCallback(
        async (choice: GhostNodeChoice) => {
            setShowGhostModal(false);
            const sourceId = connectSourceRef.current;
            if (!sourceId) return;

            const isGhost = choice === 'ghost';
            const label = isGhost ? 'Rede Existente' : 'Novo Poste';
            const { x, y } = connectDropPosRef.current;

            try {
                // 1. Criar o nó destino
                const nodeRes = await api.post(`/projects/${projectId}/nodes`, {
                    project_id: projectId,
                    pole_id: 0,
                    label,
                    pos_x: x,
                    pos_y: y,
                    is_ghost: isGhost,
                });
                const targetId = nodeRes.data.id;

                // 2. Criar aresta source → novo nó (sem condutores)
                await api.post(`/projects/${projectId}/edges`, {
                    source_node_id: parseInt(sourceId, 10),
                    target_node_id: targetId,
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

    // ── Atalhos de teclado — Nudge (setas direcionais) ───────────────────
    const nudgeOpts = { preventDefault: true, enabled: !!selectedNodeId } as const;
    useHotkeys('up',    () => nudgeSelectedNode(0, -NUDGE_PX), nudgeOpts);
    useHotkeys('down',  () => nudgeSelectedNode(0,  NUDGE_PX), nudgeOpts);
    useHotkeys('left',  () => nudgeSelectedNode(-NUDGE_PX, 0), nudgeOpts);
    useHotkeys('right', () => nudgeSelectedNode( NUDGE_PX, 0), nudgeOpts);

    // ── Atalho Delete/Backspace: apagar nó selecionado ───────────────────
    useHotkeys(
        ['delete', 'backspace'],
        () => {
            if (!selectedNodeId) return;
            const node = localNodes.find(n => n.id === String(selectedNodeId));
            const label = (node?.data as PoleNodeData)?.label ?? `Nó ${selectedNodeId}`;

            // Remove do estado local imediatamente
            setLocalNodes(prev => prev.filter(n => n.id !== String(selectedNodeId)));
            setSelectedNodeId(null);
            toast.warning(`"${label}" removido da visualização.`, {
                description: 'Para remover permanentemente, use a aba de Dados.',
                duration: 5000,
            });
        },
        { enabled: !!selectedNodeId }
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

            {showGhostModal && (
                <GhostNodeModal
                    onChoose={handleGhostChoice}
                    onClose={() => { setShowGhostModal(false); connectSourceRef.current = null; }}
                />
            )}
        </>
    );
}

// ── COMPONENTE PÚBLICO ───────────────────────────────────────────────────
export default function TopologyDiagram() {
    const { selectedProjectId } = useUIStore();
    const queryClient = useQueryClient();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [parsedPoints, setParsedPoints] = useState<ParsedPoint[]>([]);
    const [showImportModal, setShowImportModal] = useState(false);
    const [showSolverModal, setShowSolverModal] = useState(false);
    const [isParsing, setIsParsing] = useState(false);

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file || !selectedProjectId) return;
        setIsParsing(true);
        try {
            const form = new FormData();
            form.append('file', file);
            const res = await api.post(`/projects/${selectedProjectId}/parse-file`, form);
            if (!res.data.length) {
                toast.warning('Nenhum ponto encontrado no arquivo.');
            } else {
                setParsedPoints(res.data);
                setShowImportModal(true);
            }
        } catch (err: unknown) {
            const axErr = err as { response?: { data?: { detail?: string } } };
            toast.error(axErr?.response?.data?.detail ?? 'Erro ao processar arquivo GIS.');
        } finally {
            setIsParsing(false);
            e.target.value = '';
        }
    };

    const handleImported = () => {
        queryClient.invalidateQueries({ queryKey: ['topology', selectedProjectId] });
    };

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
        <>
            <div
                className="relative w-full rounded-2xl overflow-hidden border border-white/60 shadow-xl bg-slate-50/80"
                style={{ minHeight: '620px', height: '70vh' }}
            >
                {/* ── Botões overlay: Importar GIS + Otimizar Rede ───── */}
                <div className="absolute top-3 right-3 z-10 flex gap-2">
                    {/* Botão Otimizar Rede */}
                    <button
                        onClick={() => setShowSolverModal(true)}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-white/60 bg-white/50 backdrop-blur-md shadow-sm text-indigo-700 hover:bg-white/70 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-indigo-400/50"
                        title="Otimizar flechas dos condutores para reduzir esforços"
                        aria-label="Otimizar Rede"
                    >
                        <Zap size={13} />
                        Otimizar Rede
                    </button>

                    {/* Botão Importar GIS */}
                    <button
                        onClick={() => fileInputRef.current?.click()}
                        disabled={isParsing}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-white/60 bg-white/50 backdrop-blur-md shadow-sm text-blue-700 hover:bg-white/70 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-400/50 disabled:opacity-60 disabled:cursor-not-allowed"
                        title="Importar postes de arquivo GIS (.kml, .kmz, .geojson, .xlsx)"
                        aria-label="Importar arquivo GIS"
                    >
                        {isParsing
                            ? <Loader2 size={13} className="animate-spin" />
                            : <Upload size={13} />
                        }
                        {isParsing ? 'Processando...' : 'Importar GIS'}
                    </button>
                    <input
                        ref={fileInputRef}
                        type="file"
                        className="hidden"
                        accept=".kml,.kmz,.geojson,.json,.xlsx,.xls"
                        onChange={handleFileChange}
                    />
                </div>

                <ReactFlowProvider>
                    <TopologyCanvas projectId={selectedProjectId} />
                </ReactFlowProvider>
            </div>

            {showImportModal && (
                <GisImportModal
                    projectId={selectedProjectId}
                    points={parsedPoints}
                    onClose={() => setShowImportModal(false)}
                    onImported={handleImported}
                />
            )}

            {showSolverModal && (
                <SolverModal
                    projectId={selectedProjectId}
                    onClose={() => setShowSolverModal(false)}
                />
            )}
        </>
    );
}
