import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useUIStore } from './store';
import { FileText, Activity, Network, Plus, FolderOpen } from 'lucide-react';
import TractionCalculator from './components/TractionCalculator';
import TopologyDiagram from './components/TopologyDiagram';
import ForceDiagram from './components/ForceDiagram';
import Layout from './components/Layout';
import { api } from './api';

function App() {
  const { activeTab, setActiveTab, selectedProjectId, setSelectedProjectId } = useUIStore();
  const queryClient = useQueryClient();

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
    }
  });

  const handleCreateProject = () => {
    const name = prompt("Nome do novo projeto:");
    if (name) createProjectMutation.mutate(name);
  };

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
          onClick={handleCreateProject}
          className="text-blue-500 hover:text-blue-600 hover:bg-blue-50 p-1 rounded-md transition-colors"
          title="Novo Projeto"
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
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all duration-200 border ${selectedProjectId === p.id
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
    </>
  );

  return (
    <Layout sidebarContent={SidebarContent}>
      {selectedProjectId ? (
        <div className="flex flex-col h-full w-full">
          {/* TABS HEADER */}
          <div className="flex items-center gap-2 border-b border-white/50 px-6 pt-4 pb-0 bg-white/20">
            <button
              onClick={() => setActiveTab('data')}
              className={`flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 transition-all duration-200 ${activeTab === 'data'
                ? 'border-blue-500 text-blue-700 bg-white/40 rounded-t-lg shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.02)]'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-white/20'
                }`}
            >
              <FileText size={18} /> Entrada de Dados
            </button>
            <button
              onClick={() => setActiveTab('forces')}
              className={`flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 transition-all duration-200 ${activeTab === 'forces'
                ? 'border-blue-500 text-blue-700 bg-white/40 rounded-t-lg shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.02)]'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-white/20'
                }`}
            >
              <Activity size={18} /> Diagrama de Forças
            </button>
            <button
              onClick={() => setActiveTab('topology')}
              className={`flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 transition-all duration-200 ${activeTab === 'topology'
                ? 'border-blue-500 text-blue-700 bg-white/40 rounded-t-lg shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.02)]'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-white/20'
                }`}
            >
              <Network size={18} /> Unifilar Topológico
            </button>
          </div>

          {/* TAB CONTENT */}
          <div className="flex-1 p-6 overflow-y-auto custom-scrollbar">
            {activeTab === 'data' && (
              <div className="animate-in fade-in duration-300">
                <div className="mb-6 pb-4 border-b border-slate-200/50">
                  <h3 className="text-xl font-bold text-slate-800">Formulário CACL LIGHT</h3>
                  <p className="text-sm text-slate-500">Insira os dados físicos do projeto para cálculo.</p>
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
        </div>
      )}
    </Layout>
  );
}

export default App;
