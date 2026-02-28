import { create } from 'zustand';

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
}));
