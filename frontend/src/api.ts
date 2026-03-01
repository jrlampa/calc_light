import axios from 'axios';

// Utiliza a variável de ambiente VITE_API_URL, ou fallback para localhost na porta 8000
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

export const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Interceptor de respostas — propaga erros para os query handlers (React Query)
api.interceptors.response.use(
    (response) => response,
    (error) => Promise.reject(error)
);

/** Inicia o download do ZIP de exportação Excel para o projeto informado. */
export async function downloadProjectExcel(projectId: number): Promise<void> {
    const response = await api.get(`/projects/${projectId}/export/excel`, {
        responseType: 'blob',
    });
    const url = URL.createObjectURL(new Blob([response.data], { type: 'application/zip' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `projeto_${projectId}_export.zip`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 100);
}
