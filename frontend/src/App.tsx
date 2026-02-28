import { useCallback, useEffect, useRef, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useHotkeys } from 'react-hotkeys-hook';
import { toast } from 'sonner';
import { AlertTriangle, X } from 'lucide-react';
import { useUIStore, useTopologyHistoryStore } from './store';
import { FileText, Activity, Network, Plus, FolderOpen } from 'lucide-react';
import TractionCalculator from './components/TractionCalculator';
import TopologyDiagram from './components/TopologyDiagram';
import ForceDiagram from './components/ForceDiagram';
import Layout from './components/Layout';
import ShortcutsModal from './components/ShortcutsModal';
import ExportButton from './components/ExportButton';
import RecoveryModal from './components/RecoveryModal';
import { api, downloadProjectExcel } from './api';

// ── Auto-save key helpers ─────────────────────────────────────────────────

const backupKey = (projectId: number) => `cacl_backup_${projectId}`;

interface LocalBackup {
    savedAt: string; // ISO timestamp
    projectId: number;
    nodes: unknown[];
    edges: unknown[];
}

function saveToLocalStorage(projectId: number, nodes: unknown[], edges: unknown[]) {
    const backup: LocalBackup = {
        savedAt: new Date().toISOString(),
        projectId,
        nodes,
        edges,
    };
    try {
        localStorage.setItem(backupKey(projectId), JSON.stringify(backup));
    } catch {
        // localStorage quota exceeded — silently skip
    }
}

function loadFromLocalStorage(projectId: number): LocalBackup | null {
    try {
        const raw = localStorage.getItem(backupKey(projectId));
        return raw ? (JSON.parse(raw) as LocalBackup) : null;
    } catch {
        return null;
    }
}

// ── Debounce helper ───────────────────────────────────────────────────────

function useDebounce<T extends (...args: Parameters<T>) => void>(fn: T, delay: number): T {
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const fnRef = useRef<T>(fn);
    // Keep fnRef up-to-date without resetting the timer
    fnRef.current = fn;
    const debounced = useCallback(
        (...args: Parameters<T>) => {
            if (timerRef.current) clearTimeout(timerRef.current);
            timerRef.current = setTimeout(() => fnRef.current(...args), delay);
        },
        // delay is intentionally the only dep — fnRef handles fn updates without creating a new timer
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [delay]
    );
    return debounced as T;
}

// ── MODAL DE NOVO PROJETO ─────────────────────────────────────────────────
function NewProjectModal({ onConfirm, onClose }: { onConfirm: (name: string) => void; onClose: () => void }) {
  const [name, setName] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (trimmed) {
      onConfirm(trimmed);
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/30 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="w-full max-w-sm bg-white/80 backdrop-blur-xl border border-white/70 rounded-2xl shadow-2xl shadow-slate-400/30 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200/60 bg-white/40">
          <h2 className="text-base font-bold text-slate-800">Novo Projeto</h2>
        </div>
        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1">Nome do Projeto</label>
            <input
              autoFocus
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Ex: Linha 01 - Subestação Norte"
              className="w-full bg-white/50 border border-slate-200 rounded-lg px-4 py-2 text-slate-700 outline-none focus:ring-2 focus:ring-blue-400/50 focus:border-blue-400 transition-all"
            />
          </div>
          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100/60 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400/50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-md shadow-blue-500/30 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400/50"
            >
              Criar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── COMPONENTE PRINCIPAL ──────────────────────────────────────────────────
function App() {
  const {
    activeTab, setActiveTab,
    selectedProjectId, setSelectedProjectId,
    overloadedNodeIds, setOverloadedNodeIds,
    highlightOverloaded, setHighlightOverloaded,
    setSyncStatus, setLastLocalSaveAt,
  } = useUIStore();
  const queryClient = useQueryClient();

  const [isShortcutsOpen, setIsShortcutsOpen] = useState(false);
  const [isNewProjectOpen, setIsNewProjectOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  // ── Disaster Recovery state (Phase 18) ──────────────────────────────
  const [recoveryBackup, setRecoveryBackup] = useState<{ savedAt: string; backup: LocalBackup } | null>(null);

  // Fetch Projects List
  const { data: projects = [], isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.get('/projects').then(res => res.data)
  });

  // Fetch topology to detect overloaded nodes (passive, background query)
  const { data: topology } = useQuery({
    queryKey: ['topology', selectedProjectId],
    queryFn: () => api.get(`/topology/project/${selectedProjectId}`).then(r => r.data),
    enabled: !!selectedProjectId,
    staleTime: 30_000,
  });

  // Sync overloaded node IDs into global store whenever topology changes
  useEffect(() => {
    if (!topology?.nodes) {
      setOverloadedNodeIds([]);
      return;
    }
    const overloaded: number[] = topology.nodes
      .filter((n: { id: string; data: { is_overloaded?: boolean } }) => n.data?.is_overloaded)
      .map((n: { id: string }) => parseInt(n.id, 10))
      .filter((id: number) => !isNaN(id));
    setOverloadedNodeIds(overloaded);
  }, [topology, setOverloadedNodeIds]);

  // ── Auto-Save: subscribe to topology history changes (Phase 18) ──────
  const debouncedSave = useDebounce(
    useCallback(
      (projectId: number, nodes: unknown[], edges: unknown[]) => {
        saveToLocalStorage(projectId, nodes, edges);
        const ts = new Date().toISOString();
        setLastLocalSaveAt(ts);
        setSyncStatus('saved');
      },
      [setLastLocalSaveAt, setSyncStatus]
    ),
    1500
  );

  useEffect(() => {
    // Subscribe to topology history store changes
    const unsub = useTopologyHistoryStore.subscribe((state) => {
      if (!state.projectId || state.nodes.length === 0) return;
      setSyncStatus('saving');
      debouncedSave(state.projectId, state.nodes, state.edges);
    });
    return unsub;
  }, [debouncedSave, setSyncStatus]);

  // ── Disaster Recovery: check on project select (Phase 18) ───────────
  useEffect(() => {
    if (!selectedProjectId) {
      setRecoveryBackup(null);
      return;
    }

    const backup = loadFromLocalStorage(selectedProjectId);
    if (!backup) return;

    // Compare with server project updated_at
    const projectData = (Array.isArray(projects) ? projects : []).find(
      (p: { id: number; updated_at?: string }) => p.id === selectedProjectId
    );
    if (!projectData?.updated_at) return;

    const serverTs = new Date(projectData.updated_at).getTime();
    const localTs = new Date(backup.savedAt).getTime();

    if (localTs > serverTs) {
      setRecoveryBackup({ savedAt: backup.savedAt, backup });
    } else {
      setRecoveryBackup(null);
    }
  }, [selectedProjectId, projects]);

  const handleRecoverLocal = useCallback(() => {
    if (!recoveryBackup || !selectedProjectId) return;
    // Restore the topology history store from the backup so TopologyCanvas syncs
    const { setTopologySnapshot } = useTopologyHistoryStore.getState();
    setTopologySnapshot(
      selectedProjectId,
      recoveryBackup.backup.nodes as import('./store').PersistedNode[],
      recoveryBackup.backup.edges as import('./store').PersistedEdge[]
    );
    setRecoveryBackup(null);
    toast.success('Versão local recuperada com sucesso!');
  }, [recoveryBackup, selectedProjectId]);

  const handleDiscardLocal = useCallback(() => {
    if (selectedProjectId) {
      try { localStorage.removeItem(backupKey(selectedProjectId)); } catch { /* ignore */ }
    }
    setRecoveryBackup(null);
    toast('Versão da nuvem carregada.', { icon: '☁️' });
  }, [selectedProjectId]);

  // Create Project Mutation
  const createProjectMutation = useMutation({
    mutationFn: (name: string) => api.post('/projects', { name }).then(res => res.data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      setSelectedProjectId(data.id);
      toast.success(`Projeto "${data.name}" criado!`);
    },
    onError: () => toast.error('Erro ao criar projeto. Tente novamente.'),
  });

  // ── Atalhos Globais ──────────────────────────────────────────────────
  // Alt+1/2/3: navegar entre abas
  useHotkeys('alt+1', () => { setActiveTab('data');     toast('Aba 1: Entrada de Dados', { icon: '📋' }); }, { preventDefault: true });
  useHotkeys('alt+2', () => { setActiveTab('forces');   toast('Aba 2: Diagrama de Forças', { icon: '⚡' }); }, { preventDefault: true });
  useHotkeys('alt+3', () => { setActiveTab('topology'); toast('Aba 3: Unifilar Topológico', { icon: '🗺️' }); }, { preventDefault: true });

  // Ctrl+Z: Desfazer (Undo) — Phase 18
  useHotkeys('ctrl+z', (e) => {
    e.preventDefault();
    const { undo, pastStates } = useTopologyHistoryStore.temporal.getState();
    if (pastStates.length === 0) {
      toast('Nada para desfazer.', { icon: '↩️' });
      return;
    }
    undo();
    toast('Desfeito.', { icon: '↩️' });
  }, { preventDefault: true });

  // Ctrl+Y / Ctrl+Shift+Z: Refazer (Redo) — Phase 18
  useHotkeys('ctrl+y,ctrl+shift+z', (e) => {
    e.preventDefault();
    const { redo, futureStates } = useTopologyHistoryStore.temporal.getState();
    if (futureStates.length === 0) {
      toast('Nada para refazer.', { icon: '↪️' });
      return;
    }
    redo();
    toast('Refeito.', { icon: '↪️' });
  }, { preventDefault: true });

  // Ctrl+S: acionar submit do formulário ativo na Aba 1
  useHotkeys('ctrl+s', (e) => {
    e.preventDefault();
    if (activeTab === 'data') {
      // Dispara click no botão submit do formulário de nó (primeiro da Aba 1)
      const submitBtn = document.querySelector<HTMLButtonElement>('form [type="submit"]');
      if (submitBtn) { submitBtn.click(); }
      else { toast('Nenhum formulário ativo para salvar.', { icon: 'ℹ️' }); }
    } else {
      toast('Ctrl+S disponível apenas na Aba de Dados.', { icon: 'ℹ️' });
    }
    // Mark as synced (manual save to API)
    setSyncStatus('synced');
  }, { preventDefault: true });

  // Shift+?: abrir/fechar mapa de atalhos
  useHotkeys('shift+?', () => setIsShortcutsOpen(prev => !prev), { preventDefault: true });

  // Esc: fechar modais abertos
  useHotkeys('escape', () => {
    setIsShortcutsOpen(false);
    setIsNewProjectOpen(false);
  });

  const SidebarContent = (
    <>
      <div className="flex items-center gap-2 mb-8 text-xl font-bold text-slate-800">
        <div className="p-2 bg-blue-500 text-white rounded-xl shadow-lg shadow-blue-500/30">
          <Activity size={24} />
        </div>
        CACL LIGHT
      </div>

      <div className="flex items-center justify-between mb-4">
        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Meus Projetos</span>
        <button
          onClick={() => setIsNewProjectOpen(true)}
          className="text-blue-500 hover:text-blue-600 hover:bg-blue-50 p-1 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400/50"
          title="Novo Projeto (Ctrl+N)"
          aria-label="Criar novo projeto"
        >
          <Plus size={18} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
        {isLoading ? (
          <p className="text-sm text-slate-500 animate-pulse">Carregando projetos...</p>
        ) : (Array.isArray(projects) ? projects : []).map((p: { id: number; name: string }) => (
          <button
            key={p.id}
            onClick={() => setSelectedProjectId(p.id)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all duration-200 border focus:outline-none focus:ring-2 focus:ring-blue-400/50 ${selectedProjectId === p.id
              ? 'bg-white border-white/80 shadow-sm text-blue-700 font-medium'
              : 'bg-transparent border-transparent text-slate-600 hover:bg-white/40 hover:border-white/40'
              }`}
          >
            <FolderOpen size={16} className={selectedProjectId === p.id ? "text-blue-500" : "text-slate-400"} />
            <span className="truncate">{p.name}</span>
          </button>
        ))}
        {projects.length === 0 && !isLoading && (
          <p className="text-xs text-slate-400 text-center mt-4">Nenhum projeto encontrado.</p>
        )}
      </div>

      {/* Botão de atalhos no rodapé da sidebar */}
      <button
        onClick={() => setIsShortcutsOpen(true)}
        className="mt-6 flex items-center gap-2 text-xs text-slate-400 hover:text-slate-600 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400/50 rounded-md px-1 py-0.5"
        title="Atalhos de teclado (Shift+?)"
      >
        <kbd className="inline-flex items-center justify-center w-5 h-5 rounded border border-slate-200 bg-white/70 text-[10px] font-semibold">?</kbd>
        Atalhos de teclado
      </button>
    </>
  );

  return (
    <>
      <Layout sidebarContent={SidebarContent}>
        {selectedProjectId ? (
          <div className="flex flex-col h-full w-full">
            {/* ── BANNER DE ALERTA DE SOBRECARGA ──────────────────────────── */}
            {overloadedNodeIds.length > 0 && (
              <div
                className="flex items-center justify-between gap-3 px-5 py-2.5 bg-red-50/90 border-b border-red-200/60 text-red-700 backdrop-blur-sm cursor-pointer group"
                onClick={() => {
                  setActiveTab('topology');
                  setHighlightOverloaded(!highlightOverloaded);
                }}
                role="alert"
                aria-live="polite"
              >
                <div className="flex items-center gap-2 text-sm font-medium">
                  <AlertTriangle size={16} className="shrink-0 animate-pulse" />
                  <span>
                    {overloadedNodeIds.length} poste{overloadedNodeIds.length > 1 ? 's excedem' : ' excede'} a capacidade nominal.
                    <span className="ml-1.5 text-xs font-normal opacity-70">
                      {highlightOverloaded ? 'Clique para mostrar todos' : 'Clique para destacar na topologia →'}
                    </span>
                  </span>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); setHighlightOverloaded(false); }}
                  className="p-0.5 rounded hover:bg-red-100/60 transition-colors focus:outline-none focus:ring-2 focus:ring-red-400/50"
                  aria-label="Fechar alerta"
                >
                  <X size={14} />
                </button>
              </div>
            )}

            {/* TABS HEADER */}
            <div className="flex items-center gap-2 border-b border-white/50 px-6 pt-4 pb-0 bg-white/20">
              <button
                onClick={() => setActiveTab('data')}
                className={`flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-400/50 rounded-t-lg ${activeTab === 'data'
                  ? 'border-blue-500 text-blue-700 bg-white/40 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.02)]'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-white/20'
                  }`}
              >
                <FileText size={18} /> Entrada de Dados
                <span className="ml-1 text-[10px] opacity-50 font-normal">Alt+1</span>
              </button>
              <button
                onClick={() => setActiveTab('forces')}
                className={`flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-400/50 rounded-t-lg ${activeTab === 'forces'
                  ? 'border-blue-500 text-blue-700 bg-white/40 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.02)]'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-white/20'
                  }`}
              >
                <Activity size={18} /> Diagrama de Forças
                <span className="ml-1 text-[10px] opacity-50 font-normal">Alt+2</span>
              </button>
              <button
                onClick={() => setActiveTab('topology')}
                className={`flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-400/50 rounded-t-lg ${activeTab === 'topology'
                  ? 'border-blue-500 text-blue-700 bg-white/40 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.02)]'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-white/20'
                  }`}
              >
                <Network size={18} /> Unifilar Topológico
                <span className="ml-1 text-[10px] opacity-50 font-normal">Alt+3</span>
              </button>

              {/* ── Botão de Exportação Excel (Glassmorphism) ─────────────── */}
              <ExportButton
                isExporting={isExporting}
                onClick={async () => {
                  if (!selectedProjectId) return;
                  setIsExporting(true);
                  try {
                    await downloadProjectExcel(selectedProjectId);
                    toast.success('Exportação concluída! Verifique seus downloads.');
                  } catch (error: unknown) {
                    const axErr = error as { response?: { status?: number } };
                    if (axErr?.response?.status === 400) {
                      toast.error('Projeto vazio, adicione postes antes de exportar');
                    } else {
                      toast.error('Erro ao exportar planilhas. Tente novamente.');
                    }
                  } finally {
                    setIsExporting(false);
                  }
                }}
              />
            </div>

            {/* TAB CONTENT */}
            <div className="flex-1 p-6 overflow-y-auto custom-scrollbar">
              {activeTab === 'data' && (
                <div className="animate-in fade-in duration-300">
                  <div className="mb-6 pb-4 border-b border-slate-200/50">
                    <h3 className="text-xl font-bold text-slate-800">Formulário CACL LIGHT</h3>
                    <p className="text-sm text-slate-500">Insira os dados físicos do projeto para cálculo. Use <kbd className="px-1 py-0.5 rounded bg-slate-100 text-xs font-mono">Tab</kbd> para navegar e <kbd className="px-1 py-0.5 rounded bg-slate-100 text-xs font-mono">Enter</kbd> para salvar.</p>
                  </div>
                  <TractionCalculator />
                </div>
              )}
              {activeTab === 'forces' && (
                <div className="h-full w-full animate-in fade-in duration-300">
                  <ForceDiagram />
                </div>
              )}
              {activeTab === 'topology' && (
                <div className="h-full w-full animate-in fade-in duration-300 rounded-xl overflow-hidden border border-white/50 shadow-sm">
                  <TopologyDiagram />
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-slate-400">
            <div className="p-4 bg-white/40 rounded-full mb-4 shadow-sm border border-white/60">
              <Activity size={48} className="text-blue-300" />
            </div>
            <h2 className="text-xl font-medium text-slate-600">Nenhum projeto selecionado</h2>
            <p className="text-sm mt-2">Crie ou selecione um projeto no painel lateral para começar.</p>
            <p className="text-xs text-slate-300 mt-4">
              Dica: pressione <kbd className="px-1 py-0.5 rounded bg-slate-100 text-xs font-mono text-slate-500">Shift+?</kbd> para ver todos os atalhos
            </p>
          </div>
        )}
      </Layout>

      {/* Modais globais */}
      {isShortcutsOpen && <ShortcutsModal onClose={() => setIsShortcutsOpen(false)} />}
      {isNewProjectOpen && (
        <NewProjectModal
          onConfirm={(name) => createProjectMutation.mutate(name)}
          onClose={() => setIsNewProjectOpen(false)}
        />
      )}

      {/* Modal de Recuperação de Desastres (Phase 18) */}
      {recoveryBackup && (
        <RecoveryModal
          savedAt={recoveryBackup.savedAt}
          onRecover={handleRecoverLocal}
          onDiscard={handleDiscardLocal}
        />
      )}
    </>
  );
}

export default App;
