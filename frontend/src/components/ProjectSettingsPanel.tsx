import { useState } from 'react';
import { Info, Settings2 } from 'lucide-react';
import { toast } from 'sonner';
import { useProjectSettings, useUpdateProjectSettings } from '../hooks/useProjects';

interface ProjectSettingsPanelProps {
    projectId: number;
}

export default function ProjectSettingsPanel({ projectId }: ProjectSettingsPanelProps) {
    const { data: settings } = useProjectSettings(projectId);
    const updateSettings = useUpdateProjectSettings();
    const [showTooltip, setShowTooltip] = useState(false);

    const handleToggle = () => {
        const next = !settings?.enable_equipment_drag;
        updateSettings.mutate(
            { projectId, settings: { enable_equipment_drag: next } },
            {
                onSuccess: () =>
                    toast(
                        next
                            ? 'Modo Avançado de Arrasto ativado.'
                            : 'Modo Avançado desativado. Cálculo padrão Enel.',
                        { icon: next ? '⚙️' : '✅' }
                    ),
                onError: () => toast.error('Erro ao atualizar configurações.'),
            }
        );
    };

    const enabled = settings?.enable_equipment_drag ?? false;

    return (
        <div className="bg-white/60 backdrop-blur-md border border-white/60 shadow-lg shadow-slate-200/50 rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-4 pb-4 border-b border-slate-200/50">
                <div className="p-2 bg-slate-100 text-slate-600 rounded-lg">
                    <Settings2 size={20} />
                </div>
                <h2 className="text-lg font-semibold text-slate-800">Configurações do Projeto</h2>
            </div>

            {/* Toggle: enable_equipment_drag */}
            <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                    <div className="flex items-center gap-1.5">
                        <span className="text-sm font-medium text-slate-700">
                            Cálculo Avançado de Arrasto (Equipamentos)
                        </span>
                        <div className="relative">
                            <button
                                type="button"
                                onMouseEnter={() => setShowTooltip(true)}
                                onMouseLeave={() => setShowTooltip(false)}
                                onFocus={() => setShowTooltip(true)}
                                onBlur={() => setShowTooltip(false)}
                                className="text-slate-400 hover:text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-400/50 rounded-full"
                                aria-label="Informações sobre o modo avançado"
                            >
                                <Info size={14} />
                            </button>
                            {showTooltip && (
                                <div className="absolute left-5 top-0 z-20 w-64 p-3 text-xs text-slate-700 bg-white/95 backdrop-blur-md border border-slate-200 rounded-xl shadow-lg shadow-slate-200/50">
                                    <p className="font-semibold text-amber-700 mb-1">⚠️ Modo Avançado</p>
                                    <p>
                                        Ative apenas se exigido pela concessionária. Soma a área de
                                        arrasto de transformadores, cruzetas e chaves ao cálculo do
                                        vento, aumentando o esforço resultante no poste.
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">
                        {enabled
                            ? 'Ativo — equipamentos aumentam o esforço de vento.'
                            : 'Inativo — padrão Enel/Light (apenas cabos e poste).'}
                    </p>
                </div>

                {/* Toggle switch estilo iOS */}
                <button
                    type="button"
                    role="switch"
                    aria-checked={enabled}
                    onClick={handleToggle}
                    disabled={updateSettings.isPending}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-400/50 disabled:opacity-60 ${
                        enabled ? 'bg-amber-500' : 'bg-slate-200'
                    }`}
                >
                    <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-md transition-transform duration-200 ${
                            enabled ? 'translate-x-6' : 'translate-x-1'
                        }`}
                    />
                </button>
            </div>
        </div>
    );
}
