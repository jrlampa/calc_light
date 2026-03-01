import { useRef, useState } from 'react';
import { ReactFlowProvider } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Loader2, Upload, Zap } from 'lucide-react';
import { api } from '../api';
import { useUIStore } from '../store';
import GisImportModal, { type ParsedPoint } from './GisImportModal';
import SolverModal from './SolverModal';
import TopologyCanvas from './TopologyCanvas';
import CanvasPersistenceBar from './CanvasPersistenceBar';

export default function TopologyDiagram() {
    const { selectedProjectId } = useUIStore();
    const queryClient = useQueryClient();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [parsedPoints, setParsedPoints] = useState<ParsedPoint[]>([]);
    const [showImportModal, setShowImportModal] = useState(false);
    const [showSolverModal, setShowSolverModal] = useState(false);
    const [isParsing, setIsParsing] = useState(false);

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file || !selectedProjectId) return;
        setIsParsing(true);
        try {
            const form = new FormData();
            form.append('file', file);
            const res = await api.post(`/projects/${selectedProjectId}/parse-file`, form);
            if (!res.data.length) {
                toast.warning('Nenhum ponto encontrado no arquivo.');
            } else {
                setParsedPoints(res.data);
                setShowImportModal(true);
            }
        } catch (err: unknown) {
            const axErr = err as { response?: { data?: { detail?: string } } };
            toast.error(axErr?.response?.data?.detail ?? 'Erro ao processar arquivo GIS.');
        } finally {
            setIsParsing(false);
            e.target.value = '';
        }
    };

    const handleImported = () => {
        queryClient.invalidateQueries({ queryKey: ['topology', selectedProjectId] });
    };

    if (!selectedProjectId) {
        return (
            <div className="flex flex-col items-center justify-center h-64 gap-2 text-slate-400">
                <svg className="w-10 h-10 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                        d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
                <p className="text-sm">Selecione um projeto no menu lateral para visualizar a topologia.</p>
            </div>
        );
    }

    return (
        <>
            <div
                className="relative w-full rounded-2xl overflow-hidden border border-white/60 shadow-xl bg-slate-50/80"
                style={{ minHeight: '620px', height: '70vh' }}
            >
                {/* ── Botões overlay: Otimizar Rede + Importar GIS ─── */}
                <div className="absolute top-3 right-3 z-10 flex gap-2">
                    <button
                        onClick={() => setShowSolverModal(true)}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-white/60 bg-white/50 backdrop-blur-md shadow-sm text-indigo-700 hover:bg-white/70 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-indigo-400/50"
                        title="Otimizar flechas dos condutores para reduzir esforços"
                        aria-label="Otimizar Rede"
                    >
                        <Zap size={13} />
                        Otimizar Rede
                    </button>

                    <button
                        onClick={() => fileInputRef.current?.click()}
                        disabled={isParsing}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-white/60 bg-white/50 backdrop-blur-md shadow-sm text-blue-700 hover:bg-white/70 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-400/50 disabled:opacity-60 disabled:cursor-not-allowed"
                        title="Importar postes de arquivo GIS (.kml, .kmz, .geojson, .xlsx)"
                        aria-label="Importar arquivo GIS"
                    >
                        {isParsing ? <Loader2 size={13} className="animate-spin" /> : <Upload size={13} />}
                        {isParsing ? 'Processando...' : 'Importar GIS'}
                    </button>
                    <input
                        ref={fileInputRef}
                        type="file"
                        className="hidden"
                        accept=".kml,.kmz,.geojson,.json,.xlsx,.xls"
                        onChange={handleFileChange}
                    />
                </div>

                <ReactFlowProvider>
                    <CanvasPersistenceBar projectId={selectedProjectId} />
                    <TopologyCanvas projectId={selectedProjectId} />
                </ReactFlowProvider>
            </div>

            {showImportModal && (
                <GisImportModal
                    projectId={selectedProjectId}
                    points={parsedPoints}
                    onClose={() => setShowImportModal(false)}
                    onImported={handleImported}
                />
            )}

            {showSolverModal && (
                <SolverModal
                    projectId={selectedProjectId}
                    onClose={() => setShowSolverModal(false)}
                />
            )}
        </>
    );
}
