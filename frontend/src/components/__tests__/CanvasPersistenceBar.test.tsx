import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import CanvasPersistenceBar from '../CanvasPersistenceBar';

// ── Mocks de módulos externos ─────────────────────────────────────────────

// Mock react-flow internals (useReactFlow requer ReactFlowProvider)
vi.mock('@xyflow/react', () => ({
    useReactFlow: () => ({
        getNodes: vi.fn(() => []),
        getEdges: vi.fn(() => []),
        getViewport: vi.fn(() => ({ x: 0, y: 0, zoom: 1 })),
        setNodes: vi.fn(),
        setEdges: vi.fn(),
        setViewport: vi.fn(),
    }),
}));

// Mock sonner — captura chamadas de toast
const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();
const mockToastInfo = vi.fn();
vi.mock('sonner', () => ({
    toast: {
        success: (...args: unknown[]) => mockToastSuccess(...args),
        error: (...args: unknown[]) => mockToastError(...args),
        info: (...args: unknown[]) => mockToastInfo(...args),
    },
}));

// Mock api.ts — controla comportamento por teste
const mockSaveCanvas = vi.fn();
const mockLoadCanvas = vi.fn();
const mockDownloadProjectReport = vi.fn();

vi.mock('../../api', () => ({
    saveCanvas: (...args: unknown[]) => mockSaveCanvas(...args),
    loadCanvas: (...args: unknown[]) => mockLoadCanvas(...args),
    downloadProjectReport: (...args: unknown[]) => mockDownloadProjectReport(...args),
}));

// ── Setup ────────────────────────────────────────────────────────────────────

beforeEach(() => {
    vi.clearAllMocks();
});

// ── Testes ───────────────────────────────────────────────────────────────────

describe('CanvasPersistenceBar — Render', () => {
    it('renders Guardar button', () => {
        render(<CanvasPersistenceBar projectId={1} />);
        expect(screen.getByText('Guardar')).toBeTruthy();
    });

    it('renders Carregar button', () => {
        render(<CanvasPersistenceBar projectId={1} />);
        expect(screen.getByText('Carregar')).toBeTruthy();
    });

    it('renders Exportar Memorial (PDF) button', () => {
        render(<CanvasPersistenceBar projectId={1} />);
        expect(screen.getByText('Exportar Memorial (PDF)')).toBeTruthy();
    });

    it('PDF button has correct title attribute', () => {
        render(<CanvasPersistenceBar projectId={1} />);
        const btn = screen.getByTitle('Gerar Memorial de Cálculo Técnico (PDF)');
        expect(btn).toBeTruthy();
    });
});

describe('CanvasPersistenceBar — PDF Export (Fase 24)', () => {
    it('calls downloadProjectReport with the correct projectId on click', async () => {
        mockDownloadProjectReport.mockResolvedValueOnce(undefined);

        render(<CanvasPersistenceBar projectId={42} />);
        const btn = screen.getByText('Exportar Memorial (PDF)');

        fireEvent.click(btn);

        await waitFor(() => {
            expect(mockDownloadProjectReport).toHaveBeenCalledOnce();
            expect(mockDownloadProjectReport).toHaveBeenCalledWith(42);
        });
    });

    it('shows success toast after successful PDF download', async () => {
        mockDownloadProjectReport.mockResolvedValueOnce(undefined);

        render(<CanvasPersistenceBar projectId={1} />);
        fireEvent.click(screen.getByText('Exportar Memorial (PDF)'));

        await waitFor(() => {
            expect(mockToastSuccess).toHaveBeenCalledOnce();
        });
    });

    it('shows loading label while PDF is being generated', async () => {
        // Promessa que nunca resolve durante o teste → estado de loading persiste
        mockDownloadProjectReport.mockReturnValueOnce(new Promise(() => {}));

        render(<CanvasPersistenceBar projectId={1} />);
        fireEvent.click(screen.getByText('Exportar Memorial (PDF)'));

        await waitFor(() => {
            expect(screen.getByText('Gerando PDF...')).toBeTruthy();
        });
    });

    it('PDF button is disabled while generating', async () => {
        mockDownloadProjectReport.mockReturnValueOnce(new Promise(() => {}));

        render(<CanvasPersistenceBar projectId={1} />);
        const btn = screen.getByText('Exportar Memorial (PDF)').closest('button')!;

        fireEvent.click(btn);

        await waitFor(() => {
            expect((btn as HTMLButtonElement).disabled).toBe(true);
        });
    });

    it('shows generic error toast on non-422 failure', async () => {
        const error = { response: { status: 500 } };
        mockDownloadProjectReport.mockRejectedValueOnce(error);

        render(<CanvasPersistenceBar projectId={1} />);
        fireEvent.click(screen.getByText('Exportar Memorial (PDF)'));

        await waitFor(() => {
            expect(mockToastError).toHaveBeenCalledOnce();
            const call = mockToastError.mock.calls[0][0] as string;
            expect(call.toLowerCase()).toContain('memorial');
        });
    });

    it('shows 422 fallback error toast when blob text fails to parse', async () => {
        const badBlob = { text: vi.fn().mockRejectedValue(new Error('parse fail')) };
        const error = { response: { status: 422, data: badBlob } };
        mockDownloadProjectReport.mockRejectedValueOnce(error);

        render(<CanvasPersistenceBar projectId={1} />);
        fireEvent.click(screen.getByText('Exportar Memorial (PDF)'));

        await waitFor(() => {
            expect(mockToastError).toHaveBeenCalledOnce();
            const call = mockToastError.mock.calls[0][0] as string;
            expect(call.toLowerCase()).toContain('canvas');
        });
    });

    it('restores button label after PDF download completes', async () => {
        mockDownloadProjectReport.mockResolvedValueOnce(undefined);

        render(<CanvasPersistenceBar projectId={1} />);
        fireEvent.click(screen.getByText('Exportar Memorial (PDF)'));

        // After resolve the label should be back
        await waitFor(() => {
            expect(screen.getByText('Exportar Memorial (PDF)')).toBeTruthy();
        });
    });
});
