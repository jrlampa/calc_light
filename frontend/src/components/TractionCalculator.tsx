import { useState, useEffect } from 'react';

interface Conductor {
    id: number;
    name: string;
    diameter_m: number;
    weight_kg_m: number;
    cable_qty: number;
    network_type: string;
}

interface Pole {
    id: number;
    type_name: string;
    height_m: number;
    resistance_dan: number;
}

interface CalcInput {
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

interface CalcResult {
    total_diameter_m: number;
    total_weight_kg_m: number;
    wind_force_x: number;
    wind_force_y: number;
    traction_dan: number;
    comp_x: number;
    comp_y: number;
    resultant_level_dan: number;
    resultant_angle_deg: number;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function TractionCalculator() {
    const [conductors, setConductors] = useState<Conductor[]>([]);
    const [poles, setPoles] = useState<Pole[]>([]);

    const [inputs, setInputs] = useState<CalcInput[]>([
        { span_m: 52, sag_m: 0.5, angle_deg: 0, pole_height_m: 9.3, anchorage_height_m: 9.1, conductor_id: null, level: 'MT1', level_order: 1, wind_pressure: 16.956 }
    ]);
    const [selectedPole, setSelectedPole] = useState<number | null>(null);
    const [result, setResult] = useState<CalcResult | null>(null);

    useEffect(() => {
        fetch(`${API_URL}/conductors`)
            .then(r => r.json())
            .then(setConductors)
            .catch(e => console.error("Error fetching conductors", e));

        fetch(`${API_URL}/poles`)
            .then(r => r.json())
            .then(setPoles)
            .catch(e => console.error("Error fetching poles", e));
    }, []);

    const handleCalculate = async () => {
        if (!selectedPole) return alert("Selecione um poste");

        // Only send inputs that have a conductor selected
        const validInputs = inputs.filter(i => i.conductor_id !== null);

        // Conductors data needed for backend calculate logic
        const selectedConductors = validInputs.map(i => conductors.find(c => c.id === i.conductor_id));

        try {
            const response = await fetch(`${API_URL}/calculate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    inputs: validInputs,
                    conductors: selectedConductors
                })
            });
            const data = await response.json();
            setResult(data);
        } catch (err) {
            console.error(err);
            alert("Erro ao calcular.");
        }
    };

    const updateInput = (index: number, field: keyof CalcInput, value: any) => {
        const newInputs = [...inputs];
        newInputs[index] = { ...newInputs[index], [field]: value };
        setInputs(newInputs);
    };

    return (
        <div className="glass-panel">
            <div className="header">
                <h1>CACL LIGHT</h1>
                <p>Cálculo de Tração e Esforço Mecânico em Postes</p>
            </div>

            <div className="form-group">
                <label>Selecione o Poste</label>
                <select onChange={e => setSelectedPole(Number(e.target.value))}>
                    <option value="">-- Escolha --</option>
                    {poles.map(p => (
                        <option key={p.id} value={p.id}>{p.type_name} {p.height_m}m / {p.resistance_dan}daN</option>
                    ))}
                </select>
            </div>

            {inputs.map((inp, idx) => (
                <div key={idx} className="calc-section">
                    <div className="calc-title">
                        <span>Nível: {inp.level} (Vão T1)</span>
                    </div>

                    <div className="grid-container">
                        <div className="form-group">
                            <label>Condutor</label>
                            <select onChange={e => updateInput(idx, 'conductor_id', Number(e.target.value))}>
                                <option value="">-- Nenhum --</option>
                                {conductors.map(c => (
                                    <option key={c.id} value={c.id}>{c.name}</option>
                                ))}
                            </select>
                        </div>

                        <div className="form-group">
                            <label>Vão (m)</label>
                            <input type="number" step="0.1" value={inp.span_m} onChange={e => updateInput(idx, 'span_m', Number(e.target.value))} />
                        </div>

                        <div className="form-group">
                            <label>Flecha (m)</label>
                            <input type="number" step="0.1" value={inp.sag_m} onChange={e => updateInput(idx, 'sag_m', Number(e.target.value))} />
                        </div>

                        <div className="form-group">
                            <label>Ângulo (°)</label>
                            <input type="number" step="1" value={inp.angle_deg} onChange={e => updateInput(idx, 'angle_deg', Number(e.target.value))} />
                        </div>

                        <div className="form-group">
                            <label>Altura Ancoragem (m)</label>
                            <input type="number" step="0.1" value={inp.anchorage_height_m} onChange={e => updateInput(idx, 'anchorage_height_m', Number(e.target.value))} />
                        </div>
                    </div>
                </div>
            ))}

            <button className="btn-primary" onClick={handleCalculate}>Calcular Esforço</button>

            {result && (
                <div className="results-panel">
                    <h3>Resultados do Cálculo</h3>
                    <div className="results-grid">
                        <div className="result-item">
                            <span className="result-label">Tração (daN)</span>
                            <span className="result-value">{result.traction_dan}</span>
                        </div>
                        <div className="result-item">
                            <span className="result-label">Resultante Nível (daN)</span>
                            <span className="result-value">{result.resultant_level_dan}</span>
                        </div>
                        <div className="result-item">
                            <span className="result-label">Ângulo Resultante (°)</span>
                            <span className="result-value">{result.resultant_angle_deg}°</span>
                        </div>
                        <div className="result-item">
                            <span className="result-label">Força Vento X / Y</span>
                            <span className="result-value">{result.wind_force_x} / {result.wind_force_y}</span>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
