import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import CustomEdge, { type ConductorEdgeData } from '../CustomEdge';
import { Position } from '@xyflow/react';

// Mock @xyflow/react — jsdom has no SVG layout engine
vi.mock('@xyflow/react', () => ({
    BaseEdge: () => null,
    EdgeLabelRenderer: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    getBezierPath: () => ['M0,0', 100, 50],
    Position: { Left: 'left', Right: 'right', Top: 'top', Bottom: 'bottom' },
}));

const defaultProps = {
    id: 'edge-1',
    source: 'node-1',
    target: 'node-2',
    sourceX: 0,
    sourceY: 0,
    targetX: 200,
    targetY: 0,
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
};

function renderEdge(data?: ConductorEdgeData) {
    return render(<CustomEdge {...defaultProps} data={data} />);
}

describe('CustomEdge', () => {
    it('renders without crashing when no data is provided', () => {
        expect(() => renderEdge()).not.toThrow();
    });

    it('shows MT conductor label when mt_conductor is set', () => {
        renderEdge({ mt_conductor: 'ACSR 120', mt_sag_m: 1.2 });
        expect(screen.getByText(/MT · ACSR 120/)).toBeTruthy();
    });

    it('shows MT sag value below MT conductor label', () => {
        renderEdge({ mt_conductor: 'ACSR 120', mt_sag_m: 1.5 });
        expect(screen.getByText(/f=1\.5m/)).toBeTruthy();
    });

    it('shows BT conductor label when bt_conductor is set', () => {
        renderEdge({ bt_conductor: 'CA 35', bt_sag_m: 0.8 });
        expect(screen.getByText(/BT · CA 35/)).toBeTruthy();
    });

    it('shows BT sag value when bt_conductor and bt_sag_m are set', () => {
        renderEdge({ bt_conductor: 'CA 35', bt_sag_m: 0.8 });
        expect(screen.getByText(/f=0\.8m/)).toBeTruthy();
    });

    it('shows span length when span_length_m is set', () => {
        renderEdge({ span_length_m: 50 });
        expect(screen.getByText(/50m/)).toBeTruthy();
    });

    it('shows both MT and BT labels simultaneously', () => {
        renderEdge({ mt_conductor: 'XLPE 185', bt_conductor: 'CA 50' });
        expect(screen.getByText(/MT · XLPE 185/)).toBeTruthy();
        expect(screen.getByText(/BT · CA 50/)).toBeTruthy();
    });

    it('does not render MT label when mt_conductor is absent', () => {
        renderEdge({ bt_conductor: 'CA 35' });
        expect(screen.queryByText(/MT ·/)).toBeNull();
    });

    it('does not render BT label when bt_conductor is absent', () => {
        renderEdge({ mt_conductor: 'ACSR 120' });
        expect(screen.queryByText(/BT ·/)).toBeNull();
    });
});
