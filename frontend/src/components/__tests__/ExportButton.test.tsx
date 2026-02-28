import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ExportButton from '../ExportButton';

describe('ExportButton', () => {
    it('renders the "Exportar Excel" label when not exporting', () => {
        render(<ExportButton isExporting={false} onClick={() => {}} />);
        expect(screen.getByText('Exportar Excel')).toBeTruthy();
    });

    it('renders the "Exportando…" label when exporting', () => {
        render(<ExportButton isExporting={true} onClick={() => {}} />);
        expect(screen.getByText('Exportando…')).toBeTruthy();
    });

    it('is disabled when isExporting is true', () => {
        render(<ExportButton isExporting={true} onClick={() => {}} />);
        const btn = screen.getByRole('button', { name: /exportar planilhas excel/i });
        expect((btn as HTMLButtonElement).disabled).toBe(true);
    });

    it('is enabled when isExporting is false', () => {
        render(<ExportButton isExporting={false} onClick={() => {}} />);
        const btn = screen.getByRole('button', { name: /exportar planilhas excel/i });
        expect((btn as HTMLButtonElement).disabled).toBe(false);
    });

    it('calls onClick when clicked and not exporting', () => {
        const onClick = vi.fn();
        render(<ExportButton isExporting={false} onClick={onClick} />);
        fireEvent.click(screen.getByRole('button', { name: /exportar planilhas excel/i }));
        expect(onClick).toHaveBeenCalledOnce();
    });

    it('does not call onClick when button is disabled (isExporting=true)', () => {
        const onClick = vi.fn();
        render(<ExportButton isExporting={true} onClick={onClick} />);
        fireEvent.click(screen.getByRole('button', { name: /exportar planilhas excel/i }));
        // Disabled buttons do not fire click events in the DOM
        expect(onClick).not.toHaveBeenCalled();
    });

    it('has the correct aria-label', () => {
        render(<ExportButton isExporting={false} onClick={() => {}} />);
        expect(screen.getByLabelText('Exportar planilhas Excel')).toBeTruthy();
    });
});
