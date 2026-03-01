import { Package } from 'lucide-react';
import { toast } from 'sonner';
import { useCatalogs } from '../hooks/useCatalogs';
import { useNodeEquipment, useSetNodeEquipment } from '../hooks/useProjects';

interface NodeEquipmentSelectorProps {
    projectId: number;
    nodeId: number;
}

export default function NodeEquipmentSelector({ projectId, nodeId }: NodeEquipmentSelectorProps) {
    const { equipment } = useCatalogs();
    const { data: selectedIds = [] } = useNodeEquipment(projectId, nodeId);
    const setEquipment = useSetNodeEquipment();

    const toggleEquipment = (equipId: number) => {
        const next = selectedIds.includes(equipId)
            ? selectedIds.filter(id => id !== equipId)
            : [...selectedIds, equipId];
        setEquipment.mutate(
            { projectId, nodeId, equipmentIds: next },
            { onError: () => toast.error('Erro ao atualizar equipamentos.') }
        );
    };

    if (equipment.length === 0) return null;

    const totalArea = equipment
        .filter(e => selectedIds.includes(e.id))
        .reduce((sum, e) => sum + e.area_arrasto_m2, 0);

    return (
        <div className="mt-4 p-4 rounded-xl bg-amber-50/60 border border-amber-200/60 space-y-2">
            <div className="flex items-center gap-2 mb-2">
                <Package size={14} className="text-amber-600 shrink-0" />
                <span className="text-xs font-semibold text-amber-800">Equipamentos Acoplados</span>
                {totalArea > 0 && (
                    <span className="ml-auto text-[10px] text-amber-600 font-medium">
                        Área total: {totalArea.toFixed(2)} m²
                    </span>
                )}
            </div>
            <div className="flex flex-wrap gap-2">
                {equipment.map(eq => {
                    const active = selectedIds.includes(eq.id);
                    return (
                        <button
                            key={eq.id}
                            type="button"
                            onClick={() => toggleEquipment(eq.id)}
                            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all border focus:outline-none focus:ring-2 focus:ring-amber-400/50 ${
                                active
                                    ? 'bg-amber-500 text-white border-amber-500 shadow-sm shadow-amber-400/30'
                                    : 'bg-white/60 text-slate-600 border-slate-200 hover:border-amber-300 hover:bg-amber-50'
                            }`}
                        >
                            {eq.name}
                            <span className={`text-[10px] ${active ? 'text-white/80' : 'text-slate-400'}`}>
                                {eq.area_arrasto_m2.toFixed(2)}m²
                            </span>
                        </button>
                    );
                })}
            </div>
        </div>
    );
}
