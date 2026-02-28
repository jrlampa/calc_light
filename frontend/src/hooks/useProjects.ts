import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';

export interface ProjectNode {
    id: number;
    project_id: number;
    pole_id: number;
    label: string;
    pos_x: number;
    pos_y: number;
    effort_dan: number;
}

export interface NodeSpanConfig {
    id: number;
    source_node_id: number;
    target_node_id: number;
    mt_conductor_id?: number | null;
    mt_sag_m: number;
    bt_conductor_id?: number | null;
    bt_sag_m: number;
    span_length_m: number;
    angle_deg: number;
}

export interface ProjectSettings {
    enable_equipment_drag: boolean;
}

export const useProjectNodes = (projectId: number | null) => {
    return useQuery({
        queryKey: ['projects', projectId, 'nodes'],
        queryFn: () => api.get<ProjectNode[]>(`/projects/${projectId}/nodes`).then(res => res.data),
        enabled: !!projectId,
    });
};

export const useSaveNode = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ projectId, data }: { projectId: number, data: Omit<ProjectNode, 'id' | 'effort_dan'> }) =>
            api.post(`/projects/${projectId}/nodes`, data).then(res => res.data),
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ queryKey: ['projects', variables.projectId, 'nodes'] });
            queryClient.invalidateQueries({ queryKey: ['topology', variables.projectId] });
        },
    });
};

export const useSaveSpan = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ projectId, data }: { projectId: number, data: Omit<NodeSpanConfig, 'id'> }) =>
            api.post(`/projects/${projectId}/edges`, data).then(res => res.data),
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ queryKey: ['topology', variables.projectId] });
        },
    });
};

// ── Project Settings (Phase 19) ───────────────────────────────────────────────

export const useProjectSettings = (projectId: number | null) => {
    return useQuery({
        queryKey: ['projects', projectId],
        queryFn: () => api.get<ProjectSettings & { id: number; name: string }>(`/projects/${projectId}`).then(res => res.data),
        enabled: !!projectId,
        select: (data) => ({ enable_equipment_drag: data.enable_equipment_drag }),
    });
};

export const useUpdateProjectSettings = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ projectId, settings }: { projectId: number; settings: ProjectSettings }) =>
            api.patch(`/projects/${projectId}/settings`, settings).then(res => res.data),
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ queryKey: ['projects', variables.projectId] });
            queryClient.invalidateQueries({ queryKey: ['topology', variables.projectId] });
        },
    });
};

// ── Node Equipment (Phase 19) ─────────────────────────────────────────────────

export const useNodeEquipment = (projectId: number | null, nodeId: number | null) => {
    return useQuery({
        queryKey: ['projects', projectId, 'nodes', nodeId, 'equipment'],
        queryFn: () => api.get<number[]>(`/projects/${projectId}/nodes/${nodeId}/equipment`).then(res => res.data),
        enabled: !!projectId && !!nodeId,
    });
};

export const useSetNodeEquipment = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ projectId, nodeId, equipmentIds }: { projectId: number; nodeId: number; equipmentIds: number[] }) =>
            api.put(`/projects/${projectId}/nodes/${nodeId}/equipment`, { equipment_ids: equipmentIds }).then(res => res.data),
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ queryKey: ['projects', variables.projectId, 'nodes', variables.nodeId, 'equipment'] });
            queryClient.invalidateQueries({ queryKey: ['topology', variables.projectId] });
        },
    });
};
