import { useState, useEffect } from 'react';

export interface Conductor {
    id: number;
    name: string;
    diameter_m: number;
    weight_kg_m: number;
    cable_qty: number;
    network_type: string;
}

export interface Pole {
    id: number;
    type_name: string;
    height_m: number;
    resistance_dan: number;
}

export interface CalcInput {
    span_m: number;
    sag_m: number;
    angle_deg: number;
    pole_height_m: number;
    anchorage_height_m: number;
    conductor_id: number | null;
    level: string;
    level_order: number;
    wind_pressure: number;
}

export interface CalcResult {
    total_diameter_m: number;
    total_weight_kg_m: number;
    wind_force_x: number;
    wind_force_y: number;
    traction_dan: number;
    comp_x: number;
    comp_y: number;
    resultant_level_dan: number;
    resultant_angle_deg: number;
    traction_on_pole_dan: number;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const LEVELS = [
    { id: 'MT1', label: 'MT - 1º Nível' },
    { id: 'MT2', label: 'MT - 2º Nível' },
    { id: 'BT', label: 'BT' },
    { id: 'RAMAIS', label: 'Ramais / BTZero' }
];

export default function TractionCalculator() {
    const [conductors, setConductors] = useState<Conductor[]>([]);
    const [poles, setPoles] = useState<Pole[]>([]);
    const [selectedPole, setSelectedPole] = useState<number | null>(null);

    const createBlankInput = (levelId: string, idx: number): CalcInput => ({
        span_m: 0, sag_m: 0, angle_deg: 0, pole_height_m: 0, anchorage_height_m: 0, conductor_id: null, level: levelId, level_order: idx, wind_pressure: 16.956
    });

    const [levelInputs, setLevelInputs] = useState<Record<string, CalcInput[]>>({
        'MT1': [createBlankInput('MT1', 1), createBlankInput('MT1', 2), createBlankInput('MT1', 3), createBlankInput('MT1', 4)],
        'MT2': [createBlankInput('MT2', 1), createBlankInput('MT2', 2), createBlankInput('MT2', 3), createBlankInput('MT2', 4)],
        'BT': [createBlankInput('BT', 1), createBlankInput('BT', 2), createBlankInput('BT', 3), createBlankInput('BT', 4)],
        'RAMAIS': [createBlankInput('RAMAIS', 1), createBlankInput('RAMAIS', 2), createBlankInput('RAMAIS', 3), createBlankInput('RAMAIS', 4)]
    });

    const [levelResults, setLevelResults] = useState<Record<string, CalcResult | null>>({
        'MT1': null, 'MT2': null, 'BT': null, 'RAMAIS': null
    });

    useEffect(() => {
        fetch(`${API_URL}/conductors`).then(r => r.json()).then(setConductors).catch(console.error);
        fetch(`${API_URL}/poles`).then(r => r.json()).then(setPoles).catch(console.error);
    }, []);

    const updateInput = (levelId: string, index: number, field: keyof CalcInput, value: string | number | null) => {
        setLevelInputs(prev => {
            const newInputs = [...prev[levelId]];
            newInputs[index] = { ...newInputs[index], [field]: value } as CalcInput;
            return { ...prev, [levelId]: newInputs };
        });
    };

    const handleCalculate = async () => {
        if (!selectedPole) return alert("Selecione um poste para as referências de altura.");
        const pole = poles.find(p => p.id === selectedPole);

        const newResults: Record<string, CalcResult | null> = { 'MT1': null, 'MT2': null, 'BT': null, 'RAMAIS': null };

        for (const lvl of LEVELS) {
            const validInputs = levelInputs[lvl.id].filter(i => i.conductor_id !== null && i.span_m > 0);
            if (validInputs.length === 0) continue;

            const finalInputs = validInputs.map(vi => ({
                ...vi,
                pole_height_m: pole ? pole.height_m : vi.pole_height_m
            }));

            const selectedConductors = finalInputs.map(i => conductors.find(c => c.id === i.conductor_id));

            try {
                const response = await fetch(`${API_URL}/calculate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ inputs: finalInputs, conductors: selectedConductors })
                });
                const data = await response.json();
                newResults[lvl.id] = data;
            } catch (err) {
                console.error("Erro ao calcular nível", lvl.id, err);
            }
        }
        setLevelResults(newResults);
    };

    const totalPoleTraction = Object.values(levelResults).reduce((acc, curr) => acc + (curr ? curr.traction_on_pole_dan : 0), 0);
    const selectedPoleData = poles.find(p => p.id === selectedPole);
    const isPoleApproved = selectedPoleData ? totalPoleTraction <= selectedPoleData.resistance_dan : false;

    return (
        <div className="glass-panel" style={{ width: '100%', maxWidth: '1400px' }}>
            <div className="header">
                <h1>CACL LIGHT</h1>
                <p>Cálculo de Tração e Esforço Mecânico em Postes</p>
            </div>

            <div className="form-group" style={{ maxWidth: '400px', margin: '0 0 2rem 0' }}>
                <label>Selecione o Poste Central (Ponto)</label>
                <select title="Selecione o Poste" onChange={e => setSelectedPole(Number(e.target.value))}>
                    <option value="">-- Escolha --</option>
                    {poles.map(p => (
                        <option key={p.id} value={p.id}>{p.type_name} {p.height_m}m / {p.resistance_dan}daN</option>
                    ))}
                </select>
            </div>

            {LEVELS.map(lvl => (
                <div key={lvl.id} className="calc-section" style={{ marginBottom: '2rem' }}>
                    <div className="calc-title">
                        <span>{lvl.label}</span>
                        {levelResults[lvl.id] && (
                            <span style={{ fontSize: '1rem', color: '#10b981' }}>
                                Resultante Nível: {levelResults[lvl.id]?.resultant_level_dan} daN | Tração Poste: {levelResults[lvl.id]?.traction_on_pole_dan} daN
                            </span>
                        )}
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
                        {[0, 1, 2, 3].map(t => (
                            <div key={t} style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '8px' }}>
                                <h4>Tramo T{t + 1}</h4>
                                <div className="form-group">
                                    <label>Condutor</label>
                                    <select title="Condutor" onChange={e => updateInput(lvl.id, t, 'conductor_id', Number(e.target.value))}>
                                        <option value="">-- Nenhum --</option>
                                        {conductors.map(c => (
                                            <option key={c.id} value={c.id}>{c.name}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="form-group">
                                    <label>Vão (m)</label>
                                    <input title="Vão (m)" placeholder="0.0" type="number" step="0.1" value={levelInputs[lvl.id][t].span_m || ''} onChange={e => updateInput(lvl.id, t, 'span_m', Number(e.target.value))} />
                                </div>
                                <div className="form-group">
                                    <label>Flecha (m)</label>
                                    <input title="Flecha (m)" placeholder="0.0" type="number" step="0.01" value={levelInputs[lvl.id][t].sag_m || ''} onChange={e => updateInput(lvl.id, t, 'sag_m', Number(e.target.value))} />
                                </div>
                                <div className="form-group">
                                    <label>Ângulo (°)</label>
                                    <input title="Ângulo (°)" placeholder="0" type="number" step="1" value={levelInputs[lvl.id][t].angle_deg || ''} onChange={e => updateInput(lvl.id, t, 'angle_deg', Number(e.target.value))} />
                                </div>
                                <div className="form-group">
                                    <label>Alt. Ancoragem (m)</label>
                                    <input title="Alt. Ancoragem (m)" placeholder="0.0" type="number" step="0.1" value={levelInputs[lvl.id][t].anchorage_height_m || ''} onChange={e => updateInput(lvl.id, t, 'anchorage_height_m', Number(e.target.value))} />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            ))}

            <button className="btn-primary" style={{ padding: '1rem', fontSize: '1.2rem', marginTop: '1rem' }} onClick={handleCalculate}>Calcular Esforços do Poste</button>

            {selectedPole && (
                <div className="results-panel" style={{ marginTop: '2rem', border: `1px solid ${isPoleApproved ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)'}` }}>
                    <h3>Resultado Geral do Poste</h3>
                    <div className="results-grid">
                        <div className="result-item">
                            <span className="result-label">Tração Total no Poste (daN)</span>
                            <span className="result-value" style={{ color: isPoleApproved ? 'var(--success-color)' : 'var(--danger-color)' }}>
                                {totalPoleTraction.toFixed(2)} daN
                            </span>
                        </div>
                        <div className="result-item">
                            <span className="result-label">Resistência Nominal (daN)</span>
                            <span className="result-value" style={{ color: '#e2e8f0' }}>{selectedPoleData?.resistance_dan} daN</span>
                        </div>
                        <div className="result-item" style={{ gridColumn: 'span 2' }}>
                            <span className="result-label">Situação</span>
                            <span className="result-value" style={{ color: isPoleApproved ? 'var(--success-color)' : 'var(--danger-color)', fontSize: '1.8rem' }}>
                                {isPoleApproved ? 'APROVADO' : 'REPROVADO'}
                            </span>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
