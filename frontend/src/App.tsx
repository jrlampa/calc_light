import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useHotkeys } from 'react-hotkeys-hook';
import { toast } from 'sonner';
import { useUIStore } from './store';
import { FileText, Activity, Network, Plus, FolderOpen } from 'lucide-react';
import TractionCalculator from './components/TractionCalculator';
import TopologyDiagram from './components/TopologyDiagram';
import ForceDiagram from './components/ForceDiagram';
import Layout from './components/Layout';
import ShortcutsModal from './components/ShortcutsModal';
import { api } from './api';

// ── MODAL DE NOVO PROJETO ────────────────────────────────────────────────
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

// ── COMPONENTE PRINCIPAL ─────────────────────────────────────────────────
function App() {
  const { activeTab, setActiveTab, selectedProjectId, setSelectedProjectId } = useUIStore();
  const queryClient = useQueryClient();

  const [isShortcutsOpen, setIsShortcutsOpen] = useState(false);
  const [isNewProjectOpen, setIsNewProjectOpen] = useState(false);

  // Fetch Projects List
  const { data: projects = [], isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.get('/projects').then(res => res.data)
  });

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
  useHotkeys('alt+1', () => { setActiveTab('data');     toast('Aba 1: Entrada de Dados', { icon: '��' }); }, { preventDefault: true });
  useHotkeys('alt+2', () => { setActiveTab('forces');   toast('Aba 2: Diagrama de Forças', { icon: '⚡' }); }, { preventDefault: true });
  useHotkeys('alt+3', () => { setActiveTab('topology'); toast('Aba 3: Unifilar Topológico', { icon: '🗺️' }); }, { preventDefault: true });

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
    </>
  );
}

export default App;
