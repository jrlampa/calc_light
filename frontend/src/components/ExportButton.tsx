import { Download } from 'lucide-react';

interface ExportButtonProps {
  isExporting: boolean;
  onClick: () => void;
}

/**
 * Botão de exportação Excel com estilo Glassmorphism.
 * Fica desabilitado (loading state) enquanto o ZIP é gerado,
 * evitando cliques múltiplos que sobrecarregariam o servidor.
 */
export default function ExportButton({ isExporting, onClick }: ExportButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={isExporting}
      className="ml-auto flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-xl border border-white/60 bg-white/30 backdrop-blur-md shadow-md shadow-blue-200/30 text-blue-700 hover:bg-white/50 hover:shadow-blue-300/40 active:scale-95 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-400/50 disabled:opacity-60 disabled:cursor-not-allowed"
      title="Exportar planilhas Excel (.xlsm) para todos os postes do projeto"
      aria-label="Exportar planilhas Excel"
    >
      <Download size={16} className={isExporting ? 'animate-bounce' : ''} />
      {isExporting ? 'Exportando…' : 'Exportar Excel'}
    </button>
  );
}
