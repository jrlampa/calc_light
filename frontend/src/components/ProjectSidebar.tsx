import { Activity, FolderOpen, Plus } from 'lucide-react';

interface Project {
    id: number;
    name: string;
}

interface ProjectSidebarProps {
    projects: Project[];
    isLoading: boolean;
    selectedProjectId: number | null;
    onSelectProject: (id: number) => void;
    onNewProject: () => void;
    onOpenShortcuts: () => void;
}

export default function ProjectSidebar({
    projects,
    isLoading,
    selectedProjectId,
    onSelectProject,
    onNewProject,
    onOpenShortcuts,
}: ProjectSidebarProps) {
    return (
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
                    onClick={onNewProject}
                    className="text-blue-500 hover:text-blue-600 hover:bg-blue-50 p-1 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400/50"
                    title="Novo Projeto"
                    aria-label="Criar novo projeto"
                >
                    <Plus size={18} />
                </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
                {isLoading ? (
                    <p className="text-sm text-slate-500 animate-pulse">Carregando projetos...</p>
                ) : (Array.isArray(projects) ? projects : []).map((p) => (
                    <button
                        key={p.id}
                        onClick={() => onSelectProject(p.id)}
                        className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all duration-200 border focus:outline-none focus:ring-2 focus:ring-blue-400/50 ${selectedProjectId === p.id
                            ? 'bg-white border-white/80 shadow-sm text-blue-700 font-medium'
                            : 'bg-transparent border-transparent text-slate-600 hover:bg-white/40 hover:border-white/40'
                        }`}
                    >
                        <FolderOpen size={16} className={selectedProjectId === p.id ? 'text-blue-500' : 'text-slate-400'} />
                        <span className="truncate">{p.name}</span>
                    </button>
                ))}
                {projects.length === 0 && !isLoading && (
                    <p className="text-xs text-slate-400 text-center mt-4">Nenhum projeto encontrado.</p>
                )}
            </div>

            <button
                onClick={onOpenShortcuts}
                className="mt-6 flex items-center gap-2 text-xs text-slate-400 hover:text-slate-600 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400/50 rounded-md px-1 py-0.5"
                title="Atalhos de teclado (Shift+?)"
            >
                <kbd className="inline-flex items-center justify-center w-5 h-5 rounded border border-slate-200 bg-white/70 text-[10px] font-semibold">?</kbd>
                Atalhos de teclado
            </button>
        </>
    );
}
