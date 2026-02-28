import { useQuery } from '@tanstack/react-query';
import { api } from '../api';

export interface ForceVector {
    component_x: number;
    component_y: number;
    magnitude_dan: number;
    angle_deg: number;
    level: string;
    nominal_capacity?: number;
}

export const useNodeForces = (nodeId: number | null) => {
    return useQuery<ForceVector[]>({
        queryKey: ['forces', nodeId],
        queryFn: () =>
            api.get<ForceVector[]>(`/forces-diagram/node/${nodeId}`).then(r => r.data),
        enabled: !!nodeId,
        staleTime: 30_000,
    });
};
