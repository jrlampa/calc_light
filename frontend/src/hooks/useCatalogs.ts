import { useQuery } from '@tanstack/react-query';
import { api } from '../api';

export interface PoleType {
    id: number;
    type_name: string;
    height_m: number;
    resistance_dan: number;
}

export interface ConductorType {
    id: number;
    name: string;
    diameter_m: number;
    weight_kg_m: number;
    cable_qty: number;
    network_type: string;
}

export interface EquipmentType {
    id: number;
    name: string;
    area_arrasto_m2: number;
}

export const useCatalogs = () => {
    const polesQuery = useQuery({
        queryKey: ['catalogs', 'poles'],
        queryFn: () => api.get<PoleType[]>('/catalogs/poles').then((res) => res.data),
        staleTime: Infinity, // Static data, no need to refetch
    });

    const conductorsQuery = useQuery({
        queryKey: ['catalogs', 'conductors'],
        queryFn: () => api.get<ConductorType[]>('/catalogs/conductors').then((res) => res.data),
        staleTime: Infinity,
    });

    const equipmentQuery = useQuery({
        queryKey: ['catalogs', 'equipment'],
        queryFn: () => api.get<EquipmentType[]>('/catalogs/equipment').then((res) => res.data),
        staleTime: Infinity,
    });

    return {
        poles: polesQuery.data || [],
        conductors: conductorsQuery.data || [],
        equipment: equipmentQuery.data || [],
        isLoadingPoles: polesQuery.isLoading,
        isLoadingConductors: conductorsQuery.isLoading,
        isLoadingEquipment: equipmentQuery.isLoading,
    };
};
