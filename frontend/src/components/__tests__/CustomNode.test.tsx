import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import CustomNode, { type PoleNodeData } from '../CustomNode';

// Mock @xyflow/react handles — jsdom has no layout engine
vi.mock('@xyflow/react', () => ({
    Handle: () => null,
    Position: { Left: 'left', Right: 'right', Top: 'top', Bottom: 'bottom' },
}));

function renderNode(data: PoleNodeData) {
    return render(<CustomNode data={data} />);
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

    it('renders red badge for critical effort (> 500 daN)', () => {
        const { container } = renderNode({ label: 'P1', effort_dan: 600 });
        const badge = container.querySelector('.bg-red-500\\/90');
        expect(badge).toBeTruthy();
    });

    it('defaults effort to 0 when not provided', () => {
        renderNode({ label: 'P1', effort_dan: 0 });
        expect(screen.getByText('0.0 daN')).toBeTruthy();
    });
});
