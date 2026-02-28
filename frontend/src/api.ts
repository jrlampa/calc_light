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
