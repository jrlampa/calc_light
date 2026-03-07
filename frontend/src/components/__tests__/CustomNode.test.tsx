import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import CustomNode, { type PoleNodeData } from '../CustomNode';

// Mock @xyflow/react handles — jsdom has no layout engine
vi.mock('@xyflow/react', () => ({
    Handle: () => null,
    Position: { Left: 'left', Right: 'right', Top: 'top', Bottom: 'bottom' },
}));

// Mock the store so we can control resultsByNode and trafoDados per-test
const mockUseUIStore = vi.fn(() => ({ highlightOverloaded: false, overloadedNodeIds: [] }));
const mockUseElectricalStore = vi.fn(() => ({ resultsByNode: {}, trafoDados: null }));

vi.mock('../../store', () => ({
    useUIStore: (...args: unknown[]) => mockUseUIStore(...args),
    useElectricalStore: (...args: unknown[]) => mockUseElectricalStore(...args),
}));

beforeEach(() => {
    mockUseUIStore.mockReturnValue({ highlightOverloaded: false, overloadedNodeIds: [] });
    mockUseElectricalStore.mockReturnValue({ resultsByNode: {}, trafoDados: null });
});

function renderNode(data: PoleNodeData) {
    return render(<CustomNode id="1" data={data} />);
}

describe('CustomNode', () => {
    it('renders the pole label', () => {
        renderNode({ label: 'Poste A', effort_dan: 0 });
        expect(screen.getByText('Poste A')).toBeTruthy();
    });

    it('renders effort badge with formatted value', () => {
        renderNode({ label: 'P1', effort_dan: 123.456 });
        expect(screen.getByText('123.5 daN')).toBeTruthy();
    });

    it('renders green badge for low effort (< 300 daN)', () => {
        const { container } = renderNode({ label: 'P1', effort_dan: 100 });
        const badge = container.querySelector('.bg-emerald-500\\/90');
        expect(badge).toBeTruthy();
    });

    it('renders amber badge for medium effort (300–500 daN)', () => {
        const { container } = renderNode({ label: 'P1', effort_dan: 400 });
        const badge = container.querySelector('.bg-amber-400\\/90');
        expect(badge).toBeTruthy();
    });

    it('renders red badge when is_overloaded is true', () => {
        const { container } = renderNode({ label: 'P1', effort_dan: 600, is_overloaded: true, utilization_percent: 120, nominal_capacity: 500 });
        const badge = container.querySelector('.bg-red-500\\/90');
        expect(badge).toBeTruthy();
    });

    it('shows utilization percentage when available', () => {
        renderNode({ label: 'P1', effort_dan: 200, utilization_percent: 85.5, is_overloaded: false, nominal_capacity: 300 });
        expect(screen.getByText('85.5%')).toBeTruthy();
    });

    it('defaults effort to 0 when not provided', () => {
        renderNode({ label: 'P1', effort_dan: 0 });
        expect(screen.getByText('0.0 daN')).toBeTruthy();
    });

    // ── Ghost node path ────────────────────────────────────────────────────

    it('renders ghost node with "Rede Existente" footer', () => {
        renderNode({ label: 'Ghost 1', effort_dan: 0, is_ghost: true });
        expect(screen.getByText('Rede Existente')).toBeTruthy();
        expect(screen.getByText('Ghost 1')).toBeTruthy();
    });

    it('ghost node does not render an effort badge', () => {
        const { container } = renderNode({ label: 'G', effort_dan: 500, is_ghost: true });
        expect(container.querySelector('.bg-red-500\\/90')).toBeNull();
        expect(container.querySelector('.bg-emerald-500\\/90')).toBeNull();
    });

    // ── Transformer node path ──────────────────────────────────────────────

    it('renders transformer node with loading percentage', () => {
        mockUseElectricalStore.mockReturnValueOnce({
            resultsByNode: {},
            trafoDados: { carga_atual_kva: 30, carga_projetada_kva: 45, trafo_loading_percent: 75.5, trafo_status: 'Normal' },
        });
        renderNode({ label: 'Trafo', effort_dan: 0, is_transformer: true });
        expect(screen.getByText('75.5%')).toBeTruthy();
        expect(screen.getByText('Normal')).toBeTruthy();
    });

    it('renders overloaded transformer with animate-pulse class', () => {
        mockUseElectricalStore.mockReturnValueOnce({
            resultsByNode: {},
            trafoDados: { carga_atual_kva: 50, carga_projetada_kva: 80, trafo_loading_percent: 110.0, trafo_status: 'Sobrecarga' },
        });
        const { container } = renderNode({ label: 'Trafo', effort_dan: 0, is_transformer: true });
        expect(screen.getByText('110.0%')).toBeTruthy();
        expect(container.querySelector('.animate-pulse')).toBeTruthy();
    });

    it('falls through to normal node when is_transformer=true but trafoDados is null', () => {
        renderNode({ label: 'T', effort_dan: 50, is_transformer: true });
        expect(screen.getByText('50.0 daN')).toBeTruthy();
    });

    // ── Electrical badges (elec data path) ────────────────────────────────

    it('renders electrical badges when resultsByNode contains node data', () => {
        mockUseElectricalStore.mockReturnValueOnce({
            resultsByNode: {
                '1': {
                    id: '1', carga_kva: 5, carga_acum_kva: 10,
                    dv_trecho_perc: 2.1, dv_acum_perc: 4.5,
                    v_final: 120, icc_amperes: 3500,
                    cable_temp_celsius: 65, thermal_status: 'Ok !', status: 'ok',
                },
            },
            trafoDados: null,
        });
        renderNode({ label: 'P1', effort_dan: 100 });
        expect(screen.getByText(/ΔV/)).toBeTruthy();
        expect(screen.getByText('120V')).toBeTruthy();
        expect(screen.getByText('3.5kA')).toBeTruthy();
        expect(screen.getByText('65°C')).toBeTruthy();
    });

    it('tempColor applies text-red-400 when cable_temp > 90°C', () => {
        mockUseElectricalStore.mockReturnValueOnce({
            resultsByNode: {
                '1': {
                    id: '1', carga_kva: 5, carga_acum_kva: 10,
                    dv_trecho_perc: 2, dv_acum_perc: 5,
                    v_final: 120, icc_amperes: 2000,
                    cable_temp_celsius: 95, thermal_status: 'Ok !', status: 'ok',
                },
            },
            trafoDados: null,
        });
        const { container } = renderNode({ label: 'P1', effort_dan: 100 });
        expect(container.querySelector('.text-red-400')).toBeTruthy();
    });

    it('tempColor applies text-amber-400 when 70 < cable_temp ≤ 90°C', () => {
        mockUseElectricalStore.mockReturnValueOnce({
            resultsByNode: {
                '1': {
                    id: '1', carga_kva: 5, carga_acum_kva: 10,
                    dv_trecho_perc: 2, dv_acum_perc: 5,
                    v_final: 120, icc_amperes: 2000,
                    cable_temp_celsius: 75, thermal_status: 'Ok !', status: 'ok',
                },
            },
            trafoDados: null,
        });
        const { container } = renderNode({ label: 'P1', effort_dan: 100 });
        expect(container.querySelector('.text-amber-400')).toBeTruthy();
    });

    it('tempColor applies text-emerald-400 when cable_temp ≤ 70°C', () => {
        mockUseElectricalStore.mockReturnValueOnce({
            resultsByNode: {
                '1': {
                    id: '1', carga_kva: 5, carga_acum_kva: 10,
                    dv_trecho_perc: 2, dv_acum_perc: 5,
                    v_final: 120, icc_amperes: 2000,
                    cable_temp_celsius: 60, thermal_status: 'Ok !', status: 'ok',
                },
            },
            trafoDados: null,
        });
        const { container } = renderNode({ label: 'P1', effort_dan: 100 });
        expect(container.querySelector('.text-emerald-400')).toBeTruthy();
    });
});
