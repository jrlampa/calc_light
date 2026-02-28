import { create } from 'zustand';

interface UIState {
    activeTab: 'data' | 'forces' | 'topology';
    setActiveTab: (tab: 'data' | 'forces' | 'topology') => void;

    selectedProjectId: number | null;
    setSelectedProjectId: (id: number | null) => void;

    selectedNodeId: number | null;
    setSelectedNodeId: (id: number | null) => void;
}

export const useUIStore = create<UIState>((set) => ({
    activeTab: 'data',
    setActiveTab: (tab) => set({ activeTab: tab }),

    selectedProjectId: null,
    setSelectedProjectId: (id) => set({ selectedProjectId: id, selectedNodeId: null }),

    selectedNodeId: null,
    setSelectedNodeId: (id) => set({ selectedNodeId: id })
}));
