import { useForm } from 'react-hook-form';
import { useUIStore } from '../store';
import { useCatalogs } from '../hooks/useCatalogs';
import { useProjectNodes, useSaveNode, useSaveSpan } from '../hooks/useProjects';
import { Plus, Link2, MapPin } from 'lucide-react';

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

export default function TractionCalculator() {
    const { selectedProjectId } = useUIStore();
    const { poles, conductors } = useCatalogs();

    const { data: nodes = [], isLoading: isLoadingNodes } = useProjectNodes(selectedProjectId);
    const saveNode = useSaveNode();
    const saveSpan = useSaveSpan();

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
                alert('Poste adicionado com sucesso!');
            },
            onError: (err) => alert('Erro ao salvar poste: ' + err.message)
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
                alert('Vão adicionado com sucesso!');
            },
            onError: (err) => alert('Erro ao salvar vão: ' + err.message)
        });
    };

    if (!selectedProjectId) return null;

    return (
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
                        <label className="block text-sm font-medium text-slate-600 mb-1">Identificação (Label)</label>
                        <input
                            {...nodeForm.register("label", { required: true })}
                            className="w-full bg-white/50 border border-slate-200 rounded-lg px-4 py-2 text-slate-700 outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all font-medium"
                            placeholder="Ex: Poste Central - P01"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-600 mb-1">Tipo de Poste (Catálogo Light)</label>
                        <select
                            {...nodeForm.register("pole_id", { required: true })}
                            className="w-full bg-white/50 border border-slate-200 rounded-lg px-4 py-2 text-slate-700 outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all"
                        >
                            <option value="">Selecione o Poste</option>
                            {poles.map(p => (
                                <option key={p.id} value={p.id}>{p.type_name} ({p.height_m}m / {p.resistance_dan}daN)</option>
                            ))}
                        </select>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-600 mb-1">Posição X</label>
                            <input type="number" step="0.1" {...nodeForm.register("pos_x")} className="w-full bg-white/50 border border-slate-200 rounded-lg px-4 py-2" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-600 mb-1">Posição Y</label>
                            <input type="number" step="0.1" {...nodeForm.register("pos_y")} className="w-full bg-white/50 border border-slate-200 rounded-lg px-4 py-2" />
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={saveNode.isPending}
                        className="w-full mt-4 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 rounded-lg shadow-md shadow-blue-500/30 transition-all flex items-center justify-center gap-2"
                    >
                        {saveNode.isPending ? 'Salvando...' : <><Plus size={18} /> Cadastrar Poste</>}
                    </button>
                </form>

                {/* Listed Nodes summary */}
                <div className="mt-8 pt-6 border-t border-slate-200/50">
                    <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">Postes Cadastrados no Projeto ({nodes.length})</h3>
                    <div className="space-y-2 max-h-40 overflow-y-auto custom-scrollbar pr-2">
                        {nodes.map(n => (
                            <div key={n.id} className="flex justify-between items-center text-sm p-2 rounded-md bg-white/40 border border-white">
                                <span className="font-medium text-slate-700">{n.label}</span>
                                <span className="text-xs text-slate-500">Pole ID: {n.pole_id}</span>
                            </div>
                        ))}
                        {nodes.length === 0 && !isLoadingNodes && <p className="text-xs text-slate-400">Nenhum poste cadastrado.</p>}
                    </div>
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
                            <select {...spanForm.register("source_node_id", { required: true })} className="w-full bg-white/50 border border-slate-200 rounded-lg px-4 py-2 text-slate-700 outline-none focus:ring-2 focus:ring-indigo-500/50">
                                <option value="">-- Selecione --</option>
                                {nodes.map(n => <option key={n.id} value={n.id}>{n.label}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-600 mb-1">Poste Destino</label>
                            <select {...spanForm.register("target_node_id", { required: true })} className="w-full bg-white/50 border border-slate-200 rounded-lg px-4 py-2 text-slate-700 outline-none focus:ring-2 focus:ring-indigo-500/50">
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
                                <select {...spanForm.register("mt_conductor_id")} className="w-full bg-white/70 border border-slate-200 rounded-md px-3 py-1.5 text-sm">
                                    <option value="">Sem Condutor MT</option>
                                    {conductors.filter(c => c.name.includes("MT")).map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                                </select>
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-slate-500 mb-1">Flecha (m)</label>
                                <input type="number" step="0.01" {...spanForm.register("mt_sag_m")} className="w-full bg-white/70 border border-slate-200 rounded-md px-3 py-1.5 text-sm" />
                            </div>
                        </div>
                    </div>

                    <div className="p-4 rounded-xl bg-white/40 border border-white space-y-4">
                        <h3 className="text-sm font-semibold text-slate-700">Cabeamento Baixa Tensão (BT)</h3>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-xs font-medium text-slate-500 mb-1">Condutor</label>
                                <select {...spanForm.register("bt_conductor_id")} className="w-full bg-white/70 border border-slate-200 rounded-md px-3 py-1.5 text-sm">
                                    <option value="">Sem Condutor BT</option>
                                    {conductors.filter(c => c.name.includes("BT")).map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                                </select>
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-slate-500 mb-1">Flecha (m)</label>
                                <input type="number" step="0.01" {...spanForm.register("bt_sag_m")} className="w-full bg-white/70 border border-slate-200 rounded-md px-3 py-1.5 text-sm" />
                            </div>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4 pt-2">
                        <div>
                            <label className="block text-sm font-medium text-slate-600 mb-1">Distância do Vão (m)</label>
                            <input type="number" step="0.1" {...spanForm.register("span_length_m", { required: true })} className="w-full bg-white/50 border border-slate-200 rounded-lg px-4 py-2" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-600 mb-1">Ângulo Deflexão (°)</label>
                            <input type="number" step="1" {...spanForm.register("angle_deg", { required: true })} className="w-full bg-white/50 border border-slate-200 rounded-lg px-4 py-2" />
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={saveSpan.isPending}
                        className="w-full mt-6 bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2.5 rounded-lg shadow-md shadow-indigo-500/30 transition-all flex items-center justify-center gap-2"
                    >
                        {saveSpan.isPending ? 'Salvando...' : <><Link2 size={18} /> Estabelecer Conexão (Vão)</>}
                    </button>
                </form>
            </div>

        </div>
    );
}
