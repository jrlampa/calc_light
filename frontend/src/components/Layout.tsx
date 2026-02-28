import React from 'react';
import { Cloud, Loader2 } from 'lucide-react';
import { useUIStore, type SyncStatus } from '../store';

interface LayoutProps {
    sidebarContent: React.ReactNode;
    children: React.ReactNode;
}

// ── Micro-indicador de sincronização ─────────────────────────────────────

const SYNC_LABELS: Record<SyncStatus, string> = {
    idle: '',
    saving: 'Salvando...',
    saved: 'Salvo no Navegador',
    synced: 'Sincronizado',
};

function SyncIndicator() {
    const { syncStatus, lastLocalSaveAt } = useUIStore();

    if (syncStatus === 'idle') return null;

    const label = SYNC_LABELS[syncStatus];

    return (
        <div
            className={`flex items-center gap-1.5 text-[11px] font-medium transition-all duration-300 select-none ${
                syncStatus === 'saving'
                    ? 'text-amber-500'
                    : syncStatus === 'saved'
                    ? 'text-blue-500'
                    : 'text-emerald-500'
            }`}
            title={
                syncStatus === 'saved' && lastLocalSaveAt
                    ? `Último backup: ${new Date(lastLocalSaveAt).toLocaleTimeString('pt-BR')}`
                    : undefined
            }
            aria-live="polite"
        >
            {syncStatus === 'saving' && (
                <Loader2 size={11} className="animate-spin flex-shrink-0" />
            )}
            {(syncStatus === 'saved' || syncStatus === 'synced') && (
                <Cloud size={11} className="flex-shrink-0" />
            )}
            {label && <span>{label}</span>}
        </div>
    );
}

// ── Layout ────────────────────────────────────────────────────────────────

const Layout: React.FC<LayoutProps> = ({ sidebarContent, children }) => {
    return (
        <div className="min-h-screen bg-slate-50 relative flex flex-col overflow-hidden font-sans text-slate-800">

            {/* Decorative Blobs for Light Glassmorphism Effect */}
            <div className="absolute top-[-10%] left-[-10%] w-96 h-96 bg-blue-300 rounded-full mix-blend-multiply filter blur-3xl opacity-40 animate-blob"></div>
            <div className="absolute top-[20%] right-[-5%] w-96 h-96 bg-cyan-300 rounded-full mix-blend-multiply filter blur-3xl opacity-40 animate-blob animation-delay-2000"></div>
            <div className="absolute bottom-[-10%] left-[20%] w-96 h-96 bg-indigo-300 rounded-full mix-blend-multiply filter blur-3xl opacity-40 animate-blob animation-delay-4000"></div>

            {/* ── Barra de cabeçalho com indicador de sincronia ─────────── */}
            <header className="relative z-20 h-9 flex items-center justify-end px-5 bg-white/30 backdrop-blur-sm border-b border-white/40 shadow-sm shadow-slate-100/40">
                <SyncIndicator />
            </header>

            {/* ── Corpo principal (Sidebar + Main) ──────────────────────── */}
            <div className="flex flex-1 overflow-hidden">
                {/* Glass Sidebar */}
                <aside className="w-72 flex-shrink-0 z-10 m-4 rounded-2xl bg-white/40 backdrop-blur-md border border-white/60 shadow-lg shadow-slate-200/50 flex flex-col p-6">
                    {sidebarContent}
                </aside>

                {/* Main Content Area */}
                <main className="flex-1 z-10 my-4 mr-4 flex flex-col min-h-0 bg-white/40 backdrop-blur-md border border-white/60 shadow-lg shadow-slate-200/50 rounded-2xl overflow-hidden">
                    {children}
                </main>
            </div>
        </div>
    );
};

export default Layout;

