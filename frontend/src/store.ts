import { create } from 'zustand';
import { temporal } from 'zundo';

// ── Sync status type ──────────────────────────────────────────────────────

export type SyncStatus = 'idle' | 'saving' | 'saved' | 'synced';

// ── UI Store (global app UI state — NO temporal tracking) ─────────────────

interface UIState {
    activeTab: 'data' | 'forces' | 'topology';
    setActiveTab: (tab: 'data' | 'forces' | 'topology') => void;

    selectedProjectId: number | null;
    setSelectedProjectId: (id: number | null) => void;

    selectedNodeId: number | null;
    setSelectedNodeId: (id: number | null) => void;

    // Overload tracking (Phase 13)
    overloadedNodeIds: number[];
    setOverloadedNodeIds: (ids: number[]) => void;

    highlightOverloaded: boolean;
    setHighlightOverloaded: (v: boolean) => void;

    // Sync status indicator (Phase 18)
    syncStatus: SyncStatus;
    setSyncStatus: (s: SyncStatus) => void;

    lastLocalSaveAt: string | null;
    setLastLocalSaveAt: (ts: string | null) => void;
}

export const useUIStore = create<UIState>((set) => ({
    activeTab: 'data',
    setActiveTab: (tab) => set({ activeTab: tab }),

    selectedProjectId: null,
    setSelectedProjectId: (id) => set({ selectedProjectId: id, selectedNodeId: null, overloadedNodeIds: [], highlightOverloaded: false }),

    selectedNodeId: null,
    setSelectedNodeId: (id) => set({ selectedNodeId: id }),

    overloadedNodeIds: [],
    setOverloadedNodeIds: (ids) => set({ overloadedNodeIds: ids }),

    highlightOverloaded: false,
    setHighlightOverloaded: (v) => set({ highlightOverloaded: v }),

    syncStatus: 'idle',
    setSyncStatus: (s) => set({ syncStatus: s }),

    lastLocalSaveAt: null,
    setLastLocalSaveAt: (ts) => set({ lastLocalSaveAt: ts }),
}));

// ── Topology History Store (with zundo temporal — Phase 18) ───────────────
// Tracks serialisable snapshots of the active project's topology for:
//   1. Auto-save to localStorage (debounced)
//   2. Undo / Redo of node position changes

export interface PersistedNode {
    id: string;
    position: { x: number; y: number };
    data: Record<string, unknown>;
}

export interface PersistedEdge {
    id: string;
    source: string;
    target: string;
    mt_label?: string;
    bt_label?: string;
}

interface TopologyHistoryState {
    projectId: number | null;
    nodes: PersistedNode[];
    edges: PersistedEdge[];
    /** Push a new snapshot into the temporal history. */
    setTopologySnapshot: (
        projectId: number,
        nodes: PersistedNode[],
        edges: PersistedEdge[]
    ) => void;
}

export const useTopologyHistoryStore = create<TopologyHistoryState>()(
    temporal(
        (set) => ({
            projectId: null,
            nodes: [],
            edges: [],
            setTopologySnapshot: (projectId, nodes, edges) =>
                set({ projectId, nodes, edges }),
        }),
        {
            limit: 50,
            // Only track the actual topology data, not the setter function
            partialize: (state) => ({
                projectId: state.projectId,
                nodes: state.nodes,
                edges: state.edges,
            }),
        }
    )
);

// ── Electrical Results Store — Fase 22 (Motor CQT) ───────────────────────────
// Isolado da TopologyHistoryStore para não poluir o undo/redo com resultados de cálculo.

export interface TrechoResult {
    id: string;
    carga_kva: number;
    carga_acum_kva: number;
    dv_trecho_perc: number;
    dv_acum_perc: number;
    v_final: number;
    icc_amperes: number;
    cable_temp_celsius: number;
    thermal_status: string;
    status: string;
}

export interface TrafoDados {
    carga_atual_kva: number;
    carga_projetada_kva: number;
    trafo_loading_percent: number;
    trafo_status: string;
}

interface ElectricalState {
    resultsByNode: Record<string, TrechoResult>;
    trafoDados: TrafoDados | null;
    isCalculating: boolean;
    lastCalculatedAt: string | null;
    setResults: (lado1: TrechoResult[], lado2: TrechoResult[], trafo: TrafoDados) => void;
    setIsCalculating: (v: boolean) => void;
    clearResults: () => void;
}

export const useElectricalStore = create<ElectricalState>((set) => ({
    resultsByNode: {},
    trafoDados: null,
    isCalculating: false,
    lastCalculatedAt: null,

    setResults: (lado1, lado2, trafo) => {
        const map: Record<string, TrechoResult> = {};
        [...lado1, ...lado2].forEach(r => { map[r.id] = r; });
        set({
            resultsByNode: map,
            trafoDados: trafo,
            lastCalculatedAt: new Date().toISOString(),
        });
    },

    setIsCalculating: (v) => set({ isCalculating: v }),

    clearResults: () => set({ resultsByNode: {}, trafoDados: null, lastCalculatedAt: null }),
}));
