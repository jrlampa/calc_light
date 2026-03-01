import React, { useState } from 'react';
import { useReactFlow } from '@xyflow/react';
import { toast } from 'sonner';
import { saveCanvas, loadCanvas, downloadProjectReport } from '../api';

interface CanvasPersistenceBarProps {
    projectId: number;
}

const CanvasPersistenceBar: React.FC<CanvasPersistenceBarProps> = ({ projectId }) => {
    const { getNodes, getEdges, setNodes, setEdges, setViewport, getViewport } = useReactFlow();
    const [isSaving, setIsSaving] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [isExportingPdf, setIsExportingPdf] = useState(false); // Fase 24

    const handleSave = async () => {
        setIsSaving(true);
        try {
            const nodes = getNodes();
            const edges = getEdges();
            const viewport = getViewport();

            // O backend espera { nodes, edges }, vamos incluir o viewport dentro de um nó invisível ou metadado?
            // Melhor: como o backend é Smart, vamos guardar o viewport num campo 'viewport' no JSON.
            // Para isso, o schema CanvasStateSave deve aceitar campos extras or ser flexível.

            await saveCanvas(projectId, {
                nodes,
                edges,
                // @ts-expect-error - O backend aceita viewport extra via Config.extra = allow
                viewport
            });

            toast.success('Projeto guardado com sucesso!', {
                description: `${nodes.length} nós e ${edges.length} arestas salvos na nuvem.`,
                icon: '💾'
            });
        } catch (error) {
            console.error('Erro ao salvar canvas:', error);
            toast.error('Erro ao guardar projeto. Tente novamente.');
        } finally {
            setIsSaving(false);
        }
    };

    const handleLoad = async () => {
        setIsLoading(true);
        try {
            const data = await loadCanvas(projectId);

            if (data.has_canvas) {
                // Restaurar nós e arestas
                setNodes(data.nodes || []);
                setEdges(data.edges || []);

                // Restaurar viewport se existir no JSON
                if (data.viewport) {
                    setViewport(data.viewport, { duration: 800 });
                }

                toast.success('Projeto carregado!', {
                    description: 'Estado do canvas restaurado com sucesso.',
                    icon: '📂'
                });
            } else {
                toast.info('Nenhum canvas salvo encontrado para este projeto.');
            }
        } catch (error) {
            console.error('Erro ao carregar canvas:', error);
            toast.error('Erro ao carregar projeto.');
        } finally {
            setIsLoading(false);
        }
    };

    // Fase 24: Exportar Memorial de Cálculo em PDF
    const handleExportPdf = async () => {
        setIsExportingPdf(true);
        try {
            await downloadProjectReport(projectId);
            toast.success('Memorial de Cálculo exportado!', {
                description: 'O PDF está sendo baixado.',
                icon: '📄',
            });
        } catch (error: unknown) {
            console.error('Erro ao gerar memorial PDF:', error);
            const axErr = error as { response?: { data?: Blob; status?: number } };
            if (axErr?.response?.status === 422) {
                // O axios recebeu responseType 'blob' — o corpo do erro também é Blob
                try {
                    const text = await axErr.response?.data?.text?.();
                    const detail = text ? (JSON.parse(text)?.detail ?? null) : null;
                    toast.error(
                        detail ?? 'Canvas vazio ou sem transformador. Salve o diagrama antes.'
                    );
                } catch {
                    toast.error('Canvas vazio ou sem transformador. Salve o diagrama antes.');
                }
            } else {
                toast.error('Erro ao gerar o Memorial de Cálculo. Tente novamente.');
            }
        } finally {
            setIsExportingPdf(false);
        }
    };

    return (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2 p-1.5 bg-white/80 backdrop-blur-md border border-slate-200 rounded-2xl shadow-xl transition-all hover:shadow-2xl">
            <button
                onClick={handleSave}
                disabled={isSaving}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl transition-all active:scale-95 disabled:opacity-50"
            >
                {isSaving ? (
                    <span className="w-4 h-4 border-2 border-slate-300 border-t-violet-500 rounded-full animate-spin" />
                ) : (
                    <span className="text-lg">💾</span>
                )}
                {isSaving ? 'Guardando...' : 'Guardar'}
            </button>

            <div className="w-px h-6 bg-slate-200 mx-1" />

            <button
                onClick={handleLoad}
                disabled={isLoading}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl transition-all active:scale-95 disabled:opacity-50"
            >
                {isLoading ? (
                    <span className="w-4 h-4 border-2 border-slate-300 border-t-blue-500 rounded-full animate-spin" />
                ) : (
                    <span className="text-lg">📂</span>
                )}
                {isLoading ? 'Carregando...' : 'Carregar'}
            </button>

            {/* Fase 24 — Exportar Memorial de Cálculo (PDF) */}
            <div className="w-px h-6 bg-slate-200 mx-1" />

            <button
                onClick={handleExportPdf}
                disabled={isExportingPdf}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-emerald-700 bg-white hover:bg-emerald-50 border border-emerald-200 rounded-xl transition-all active:scale-95 disabled:opacity-50"
                title="Gerar Memorial de Cálculo Técnico (PDF)"
            >
                {isExportingPdf ? (
                    <span className="w-4 h-4 border-2 border-emerald-300 border-t-emerald-600 rounded-full animate-spin" />
                ) : (
                    <span className="text-lg">📄</span>
                )}
                {isExportingPdf ? 'Gerando PDF...' : 'Exportar Memorial (PDF)'}
            </button>
        </div>
    );
};

export default CanvasPersistenceBar;
