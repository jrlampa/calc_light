import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';
import { Info, Link2, MapPin, Package, Plus, Settings2 } from 'lucide-react';
import { useUIStore } from '../store';
import { useCatalogs } from '../hooks/useCatalogs';
import {
    useNodeEquipment,
    useProjectNodes,
    useProjectSettings,
    useSaveNode,
    useSaveSpan,
    useSetNodeEquipment,
    useUpdateProjectSettings,
} from '../hooks/useProjects';

// ── CLASSES DE ESTILO REUTILIZÁVEIS ──────────────────────────────────────
const focusRing = 'outline-none focus:ring-2 focus:ring-blue-400/50 focus:border-blue-400 transition-all';

const inputCls = `w-full bg-white/50 border border-slate-200 rounded-lg px-4 py-2 text-slate-700 ${focusRing}`;

const selectCls = `w-full bg-white/50 border border-slate-200 rounded-lg px-4 py-2 text-slate-700 ${focusRing}`;

const selectSmCls = `w-full bg-white/70 border border-slate-200 rounded-md px-3 py-1.5 text-sm text-slate-700 ${focusRing}`;

const inputSmCls = `w-full bg-white/70 border border-slate-200 rounded-md px-3 py-1.5 text-sm text-slate-700 ${focusRing}`;

// Auto-seleciona o texto inteiro ao receber foco (fluxo contínuo tipo Excel)
const onFocusSelect = (e: React.FocusEvent<HTMLInputElement>) => e.target.select();

// ── TIPOS ────────────────────────────────────────────────────────────────
interface NodeFormData {
    label: string;
    pole_id: number;
    pos_x: number;
    pos_y: number;
}

interface SpanFormData {
    source_node_id: number;
    target_node_id: number;
    mt_conductor_id: number | null;
    mt_sag_m: number;
    bt_conductor_id: number | null;
    bt_sag_m: number;
    span_length_m: number;
    angle_deg: number;
}

// ── SUB-COMPONENTE: Seletor de Equipamentos por Nó (Fase 19) ─────────────
function NodeEquipmentSelector({ projectId, nodeId }: { projectId: number; nodeId: number }) {
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

// ── SUB-COMPONENTE: Painel de Configurações do Projeto (Fase 19) ──────────
function ProjectSettingsPanel({ projectId }: { projectId: number }) {
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

// ── COMPONENTE PRINCIPAL ──────────────────────────────────────────────────
export default function TractionCalculator() {
    const { selectedProjectId } = useUIStore();
    const { poles, conductors } = useCatalogs();
    const { data: settings } = useProjectSettings(selectedProjectId);

    const { data: nodes = [], isLoading: isLoadingNodes } = useProjectNodes(selectedProjectId);
    const saveNode = useSaveNode();
    const saveSpan = useSaveSpan();

    // ID do nó selecionado para exibir equipamentos acoplados
    const [selectedNodeIdForEquip, setSelectedNodeIdForEquip] = useState<number | null>(null);
    const enableEquipDrag = settings?.enable_equipment_drag ?? false;

    const nodeForm = useForm<NodeFormData>({
        defaultValues: { label: '', pole_id: undefined, pos_x: 0, pos_y: 0 }
    });

    const spanForm = useForm<SpanFormData>({
        defaultValues: {
            source_node_id: undefined, target_node_id: undefined,
            mt_conductor_id: null, mt_sag_m: 0,
            bt_conductor_id: null, bt_sag_m: 0,
            span_length_m: 50, angle_deg: 0
        }
    });

    const onSubmitNode = (data: NodeFormData) => {
        if (!selectedProjectId) return;
        saveNode.mutate({
            projectId: selectedProjectId,
            data: {
                project_id: selectedProjectId,
                pole_id: Number(data.pole_id),
                label: data.label,
                pos_x: Number(data.pos_x),
                pos_y: Number(data.pos_y)
            }
        }, {
            onSuccess: () => {
                nodeForm.reset();
                toast.success('Poste cadastrado com sucesso!');
            },
            onError: (err) => toast.error(`Erro ao salvar poste: ${err.message}`),
        });
    };

    const onSubmitSpan = (data: SpanFormData) => {
        if (!selectedProjectId) return;
        saveSpan.mutate({
            projectId: selectedProjectId,
            data: {
                source_node_id: Number(data.source_node_id),
                target_node_id: Number(data.target_node_id),
                mt_conductor_id: data.mt_conductor_id ? Number(data.mt_conductor_id) : null,
                mt_sag_m: Number(data.mt_sag_m),
                bt_conductor_id: data.bt_conductor_id ? Number(data.bt_conductor_id) : null,
                bt_sag_m: Number(data.bt_sag_m),
                span_length_m: Number(data.span_length_m),
                angle_deg: Number(data.angle_deg)
            }
        }, {
            onSuccess: () => {
                spanForm.reset();
                toast.success('Vão estabelecido com sucesso!');
            },
            onError: (err) => toast.error(`Erro ao salvar vão: ${err.message}`),
        });
    };

    if (!selectedProjectId) return null;

    return (
        <div className="flex flex-col gap-6">
            {/* Configurações do Projeto (toggle de arrasto) */}
            <ProjectSettingsPanel projectId={selectedProjectId} />

            <div className="flex flex-col gap-6 lg:flex-row">
                {/* COLUMN 1: POSTES */}
                <div className="flex-1 bg-white/60 backdrop-blur-md border border-white/60 shadow-lg shadow-slate-200/50 rounded-2xl p-6">
                    <div className="flex items-center gap-2 mb-6 border-b border-slate-200/50 pb-4">
                        <div className="p-2 bg-blue-100 text-blue-600 rounded-lg">
                            <MapPin size={20} />
                        </div>
                        <h2 className="text-lg font-semibold text-slate-800">Adicionar Poste Físico</h2>
                    </div>

                    <form onSubmit={nodeForm.handleSubmit(onSubmitNode)} className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-600 mb-1">
                                Identificação (Label)
                            </label>
                            <input
                                {...nodeForm.register('label', { required: true })}
                                className={inputCls}
                                placeholder="Ex: Poste Central - P01"
                                onFocus={onFocusSelect}
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-600 mb-1">
                                Tipo de Poste (Catálogo Light)
                            </label>
                            <select
                                {...nodeForm.register('pole_id', { required: true })}
                                className={selectCls}
                            >
                                <option value="">Selecione o Poste</option>
                                {poles.map(p => (
                                    <option key={p.id} value={p.id}>
                                        {p.type_name} ({p.height_m}m / {p.resistance_dan}daN)
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-600 mb-1">Posição X</label>
                                <input
                                    type="number"
                                    step="0.1"
                                    {...nodeForm.register('pos_x')}
                                    className={inputCls}
                                    onFocus={onFocusSelect}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-600 mb-1">Posição Y</label>
                                <input
                                    type="number"
                                    step="0.1"
                                    {...nodeForm.register('pos_y')}
                                    className={inputCls}
                                    onFocus={onFocusSelect}
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={saveNode.isPending}
                            className="w-full mt-4 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 rounded-lg shadow-md shadow-blue-500/30 transition-all flex items-center justify-center gap-2 focus:outline-none focus:ring-2 focus:ring-blue-400/50"
                        >
                            {saveNode.isPending ? 'Salvando...' : <><Plus size={18} /> Cadastrar Poste</>}
                        </button>
                    </form>

                    {/* Listed Nodes summary + equipment selector */}
                    <div className="mt-8 pt-6 border-t border-slate-200/50">
                        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">
                            Postes Cadastrados no Projeto ({nodes.length})
                        </h3>
                        <div className="space-y-2 max-h-48 overflow-y-auto custom-scrollbar pr-2">
                            {nodes.map(n => (
                                <div
                                    key={n.id}
                                    className={`flex justify-between items-center text-sm p-2 rounded-md border cursor-pointer transition-colors ${
                                        enableEquipDrag && selectedNodeIdForEquip === n.id
                                            ? 'bg-amber-50 border-amber-200'
                                            : 'bg-white/40 border-white hover:bg-white/60'
                                    }`}
                                    onClick={() => {
                                        if (!enableEquipDrag) return;
                                        setSelectedNodeIdForEquip(prev => prev === n.id ? null : n.id);
                                    }}
                                    title={enableEquipDrag ? 'Clique para gerenciar equipamentos acoplados' : undefined}
                                >
                                    <span className="font-medium text-slate-700">{n.label}</span>
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs text-slate-500">Pole ID: {n.pole_id}</span>
                                        {enableEquipDrag && (
                                            <Package size={12} className="text-amber-500" />
                                        )}
                                    </div>
                                </div>
                            ))}
                            {nodes.length === 0 && !isLoadingNodes && (
                                <p className="text-xs text-slate-400">Nenhum poste cadastrado.</p>
                            )}
                        </div>

                        {/* Equipment selector — aparece ao clicar num nó com modo avançado ativo */}
                        {enableEquipDrag && selectedNodeIdForEquip && (
                            <NodeEquipmentSelector
                                projectId={selectedProjectId}
                                nodeId={selectedNodeIdForEquip}
                            />
                        )}
                        {enableEquipDrag && !selectedNodeIdForEquip && nodes.length > 0 && (
                            <p className="mt-3 text-[11px] text-amber-600 flex items-center gap-1">
                                <Package size={11} />
                                Clique num poste para gerenciar equipamentos acoplados.
                            </p>
                        )}
                    </div>
                </div>

                {/* COLUMN 2: VÃOS (SPANS) */}
                <div className="flex-1 bg-white/60 backdrop-blur-md border border-white/60 shadow-lg shadow-slate-200/50 rounded-2xl p-6">
                    <div className="flex items-center gap-2 mb-6 border-b border-slate-200/50 pb-4">
                        <div className="p-2 bg-indigo-100 text-indigo-600 rounded-lg">
                            <Link2 size={20} />
                        </div>
                        <h2 className="text-lg font-semibold text-slate-800">Conectar Postes (Criar Vão)</h2>
                    </div>

                    <form onSubmit={spanForm.handleSubmit(onSubmitSpan)} className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-600 mb-1">Poste Origem</label>
                                <select
                                    {...spanForm.register('source_node_id', { required: true })}
                                    className={selectCls}
                                >
                                    <option value="">-- Selecione --</option>
                                    {nodes.map(n => <option key={n.id} value={n.id}>{n.label}</option>)}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-600 mb-1">Poste Destino</label>
                                <select
                                    {...spanForm.register('target_node_id', { required: true })}
                                    className={selectCls}
                                >
                                    <option value="">-- Selecione --</option>
                                    {nodes.map(n => <option key={n.id} value={n.id}>{n.label}</option>)}
                                </select>
                            </div>
                        </div>

                        <div className="p-4 rounded-xl bg-white/40 border border-white mt-4 space-y-4">
                            <h3 className="text-sm font-semibold text-slate-700">Cabeamento Média Tensão (MT)</h3>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-medium text-slate-500 mb-1">Condutor</label>
                                    <select {...spanForm.register('mt_conductor_id')} className={selectSmCls}>
                                        <option value="">Sem Condutor MT</option>
                                        {conductors.filter(c => c.name.includes('MT')).map(c => (
                                            <option key={c.id} value={c.id}>{c.name}</option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-slate-500 mb-1">Flecha (m)</label>
                                    <input
                                        type="number"
                                        step="0.01"
                                        {...spanForm.register('mt_sag_m')}
                                        className={inputSmCls}
                                        onFocus={onFocusSelect}
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="p-4 rounded-xl bg-white/40 border border-white space-y-4">
                            <h3 className="text-sm font-semibold text-slate-700">Cabeamento Baixa Tensão (BT)</h3>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-medium text-slate-500 mb-1">Condutor</label>
                                    <select {...spanForm.register('bt_conductor_id')} className={selectSmCls}>
                                        <option value="">Sem Condutor BT</option>
                                        {conductors.filter(c => c.name.includes('BT')).map(c => (
                                            <option key={c.id} value={c.id}>{c.name}</option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-slate-500 mb-1">Flecha (m)</label>
                                    <input
                                        type="number"
                                        step="0.01"
                                        {...spanForm.register('bt_sag_m')}
                                        className={inputSmCls}
                                        onFocus={onFocusSelect}
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4 pt-2">
                            <div>
                                <label className="block text-sm font-medium text-slate-600 mb-1">Distância do Vão (m)</label>
                                <input
                                    type="number"
                                    step="0.1"
                                    {...spanForm.register('span_length_m', { required: true })}
                                    className={inputCls}
                                    onFocus={onFocusSelect}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-600 mb-1">Ângulo Deflexão (°)</label>
                                <input
                                    type="number"
                                    step="1"
                                    {...spanForm.register('angle_deg', { required: true })}
                                    className={inputCls}
                                    onFocus={onFocusSelect}
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={saveSpan.isPending}
                            className="w-full mt-6 bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2.5 rounded-lg shadow-md shadow-indigo-500/30 transition-all flex items-center justify-center gap-2 focus:outline-none focus:ring-2 focus:ring-blue-400/50"
                        >
                            {saveSpan.isPending ? 'Salvando...' : <><Link2 size={18} /> Estabelecer Conexão (Vão)</>}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}

