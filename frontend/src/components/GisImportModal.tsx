import { useState } from 'react';
import { Loader2, MapPin, X } from 'lucide-react';
import { toast } from 'sonner';
import { api } from '../api';

// ── TIPOS ──────────────────────────────────────────────────────────────────
export interface ParsedPoint {
  label: string;
  lat: number;
  lng: number;
}

interface Props {
  projectId: number;
  points: ParsedPoint[];
  onClose: () => void;
  onImported: () => void;
}

// ── COMPONENTE ─────────────────────────────────────────────────────────────
export default function GisImportModal({ projectId, points, onClose, onImported }: Props) {
  const [selected, setSelected] = useState<Set<number>>(
    () => new Set(points.map((_, i) => i))
  );
  const [importing, setImporting] = useState(false);

  const toggle = (i: number) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  };

  const toggleAll = () => {
    if (selected.size === points.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(points.map((_, i) => i)));
    }
  };

  const handleImport = async () => {
    const selectedPoints = points.filter((_, i) => selected.has(i));
    if (!selectedPoints.length) {
      toast.warning('Nenhum ponto selecionado.');
      return;
    }
    setImporting(true);
    try {
      await api.post(`/projects/${projectId}/import-nodes`, { points: selectedPoints });
      toast.success(`${selectedPoints.length} poste(s) importado(s) com sucesso!`);
      onImported();
      onClose();
    } catch {
      toast.error('Erro ao importar pontos. Tente novamente.');
    } finally {
      setImporting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/30 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="w-full max-w-lg bg-white/80 backdrop-blur-xl border border-white/70 rounded-2xl shadow-2xl overflow-hidden flex flex-col"
        style={{ maxHeight: '80vh' }}
      >
        {/* ── Cabeçalho ───────────────────────────────────────────────── */}
        <div className="px-6 py-4 border-b border-slate-200/60 bg-white/40 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MapPin size={18} className="text-blue-500" />
            <h2 className="text-base font-bold text-slate-800">Importar Pontos GIS</h2>
            <span className="text-xs text-slate-400 ml-1">{points.length} ponto(s) encontrado(s)</span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-slate-100/60 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400/50"
            aria-label="Fechar modal"
          >
            <X size={16} className="text-slate-500" />
          </button>
        </div>

        {/* ── Lista de pontos com checkboxes ──────────────────────────── */}
        <div className="overflow-y-auto flex-1 px-4 py-2 space-y-1 custom-scrollbar">
          {/* Selecionar todos */}
          <label className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-50/80 cursor-pointer border-b border-slate-100/80 mb-1">
            <input
              type="checkbox"
              checked={selected.size === points.length}
              onChange={toggleAll}
              className="w-4 h-4 rounded accent-blue-500"
              aria-label="Selecionar todos os pontos"
            />
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Selecionar todos
            </span>
          </label>

          {points.map((pt, i) => (
            <label
              key={i}
              className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-white/50 cursor-pointer transition-colors"
            >
              <input
                type="checkbox"
                checked={selected.has(i)}
                onChange={() => toggle(i)}
                className="w-4 h-4 rounded accent-blue-500"
              />
              <MapPin size={14} className={selected.has(i) ? 'text-blue-500' : 'text-slate-300'} />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-700 truncate">{pt.label}</p>
                <p className="text-xs text-slate-400">
                  {pt.lat.toFixed(6)}, {pt.lng.toFixed(6)}
                </p>
              </div>
            </label>
          ))}
        </div>

        {/* ── Rodapé ──────────────────────────────────────────────────── */}
        <div className="px-6 py-4 border-t border-slate-200/60 bg-white/40 flex items-center justify-between gap-3">
          <p className="text-xs text-slate-500">{selected.size} de {points.length} selecionados</p>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100/60 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400/50"
            >
              Cancelar
            </button>
            <button
              onClick={handleImport}
              disabled={importing || selected.size === 0}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-md shadow-blue-500/30 transition-colors disabled:opacity-60 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-400/50"
            >
              {importing && <Loader2 size={14} className="animate-spin" />}
              {importing ? 'Importando...' : `Importar ${selected.size} ponto(s)`}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
