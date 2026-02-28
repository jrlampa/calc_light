import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import RecoveryModal from '../RecoveryModal';

describe('RecoveryModal', () => {
    const isoTs = '2026-02-28T20:00:00.000Z';

    it('renders the disaster-recovery heading', () => {
        render(<RecoveryModal savedAt={isoTs} onRecover={vi.fn()} onDiscard={vi.fn()} />);
        expect(screen.getByRole('alertdialog')).toBeTruthy();
        expect(screen.getByText(/Progresso não sincronizado detectado/i)).toBeTruthy();
    });

    it('shows the human-friendly timestamp', () => {
        render(<RecoveryModal savedAt={isoTs} onRecover={vi.fn()} onDiscard={vi.fn()} />);
        // Some locale substring must appear (date or time digits)
        const el = screen.getByText(/Backup local salvo em:/i).closest('p');
        expect(el?.textContent).toContain('28');
    });

    it('calls onRecover when the recover button is clicked', () => {
        const onRecover = vi.fn();
        render(<RecoveryModal savedAt={isoTs} onRecover={onRecover} onDiscard={vi.fn()} />);
        fireEvent.click(screen.getByRole('button', { name: /Recuperar versão local/i }));
        expect(onRecover).toHaveBeenCalledOnce();
    });

    it('calls onDiscard when the discard button is clicked', () => {
        const onDiscard = vi.fn();
        render(<RecoveryModal savedAt={isoTs} onRecover={vi.fn()} onDiscard={onDiscard} />);
        fireEvent.click(screen.getByRole('button', { name: /Descartar progresso local e usar versão da nuvem/i }));
        expect(onDiscard).toHaveBeenCalledOnce();
    });

    it('renders the body description text', () => {
        render(<RecoveryModal savedAt={isoTs} onRecover={vi.fn()} onDiscard={vi.fn()} />);
        expect(screen.getByText(/Detectamos um progresso não salvo/i)).toBeTruthy();
    });

    it('handles an invalid timestamp gracefully without crashing', () => {
        render(<RecoveryModal savedAt="not-a-date" onRecover={vi.fn()} onDiscard={vi.fn()} />);
        // Should fall back to the raw string
        expect(screen.getByText(/Backup local salvo em:/i).closest('p')?.textContent).toContain('not-a-date');
    });
});
