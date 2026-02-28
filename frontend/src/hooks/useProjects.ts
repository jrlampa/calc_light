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
