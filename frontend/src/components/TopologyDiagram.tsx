import { useMemo } from 'react';
import {
    ReactFlow,
    Controls,
    Background,
    Handle,
    Position,
    BaseEdge,
    getBezierPath,
    EdgeLabelRenderer,
    type EdgeProps,
    type Node,
    type Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api';
import { useUIStore } from '../store';

// --- TIPOS ---
interface PoleNodeData extends Record<string, unknown> {
    label: string;
    effort: number;
}

interface ConductorEdgeData extends Record<string, unknown> {
    mt_label?: string;
    bt_label?: string;
}

// --- CUSTOM NODE (2.5D com Esforço Embaixo) ---
const PoleNode = ({ data }: { data: PoleNodeData }) => (
    <div className="flex flex-col items-center">
        <div className="relative flex items-center justify-center w-10 h-10 rounded-full bg-white/10 border border-white/20 shadow-lg">
            <Handle type="target" position={Position.Left} className="!bg-slate-400 !w-2 !h-2" />
            <Handle type="source" position={Position.Right} className="!bg-slate-400 !w-2 !h-2" />
            <span className="text-xs font-bold text-blue-700">{data.label}</span>
        </div>
        {/* Esforço renderizado ABAIXO do nó — regra de design estrita */}
        <div className="mt-2 text-xs font-bold text-red-500 bg-black/60 px-2 py-0.5 rounded">
            {data.effort ?? 0} daN
        </div>
    </div>
);

// --- CUSTOM EDGE (MT em cima / BT embaixo — regra estrita) ---
const DoubleConductorEdge = ({
    sourceX, sourceY, targetX, targetY,
    sourcePosition, targetPosition,
    style = {},
    markerEnd,
    data,
}: EdgeProps) => {
    const edgeData = data as ConductorEdgeData | undefined;
    const [edgePath, labelX, labelY] = getBezierPath({
        sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition,
    });

    return (
        <>
            <BaseEdge path={edgePath} markerEnd={markerEnd} style={{ ...style, strokeWidth: 2, stroke: '#3b82f6' }} />
            <EdgeLabelRenderer>
                <div
                    style={{
                        position: 'absolute',
                        transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
                        pointerEvents: 'all',
                    }}
                    className="nodrag nopan flex flex-col items-center gap-3"
                >
                    {/* Linha Superior → Condutor MT */}
                    <div className="-translate-y-4 text-xs text-blue-400 bg-black/70 px-1.5 py-0.5 rounded">
                        {edgeData?.mt_label ?? '—'}
                    </div>
                    {/* Linha Inferior → Condutor BT */}
                    <div className="translate-y-4 text-xs text-emerald-400 bg-black/70 px-1.5 py-0.5 rounded">
                        {edgeData?.bt_label ?? '—'}
                    </div>
                </div>
            </EdgeLabelRenderer>
        </>
    );
};

export default function TopologyDiagram() {
    const { selectedProjectId } = useUIStore();

    const { data: topology, isLoading } = useQuery({
        queryKey: ['topology', selectedProjectId],
        queryFn: () => api.get(`/topology/project/${selectedProjectId}`).then(r => r.data),
        enabled: !!selectedProjectId,
    });

    const nodeTypes = useMemo(() => ({ pole: PoleNode }), []);
    const edgeTypes = useMemo(() => ({ conductors: DoubleConductorEdge }), []);

    if (!selectedProjectId) {
        return (
            <div className="flex items-center justify-center h-64 text-slate-400">
                Selecione um projeto para visualizar a topologia.
            </div>
        );
    }

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-64 text-slate-500 animate-pulse">
                Calculando topologia no Smart Backend...
            </div>
        );
    }

    const reactFlowNodes: Node<PoleNodeData>[] = (topology?.nodes ?? []).map((n: { id: string; position: { x: number; y: number }; data: PoleNodeData }) => ({
        id: n.id,
        type: 'pole',
        position: n.position,
        data: n.data,
    }));

    const reactFlowEdges: Edge<ConductorEdgeData>[] = (topology?.edges ?? []).map((e: { id: string; source: string; target: string; mt_label?: string; bt_label?: string }) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        type: 'conductors',
        data: { mt_label: e.mt_label, bt_label: e.bt_label },
        animated: true,
    }));

    return (
        <div className="w-full rounded-xl overflow-hidden border border-white/40 shadow-lg" style={{ minHeight: '600px' }}>
            <ReactFlow
                nodes={reactFlowNodes}
                edges={reactFlowEdges}
                nodeTypes={nodeTypes}
                edgeTypes={edgeTypes}
                fitView
            >
                <Background gap={12} size={1} color="#cbd5e1" />
                <Controls />
            </ReactFlow>
        </div>
    );
}
