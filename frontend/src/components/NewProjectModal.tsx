import { useState } from 'react';

interface NewProjectModalProps {
    onConfirm: (name: string) => void;
    onClose: () => void;
}

export default function NewProjectModal({ onConfirm, onClose }: NewProjectModalProps) {
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
