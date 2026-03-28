export { COOKIE_NAME, ONE_YEAR_MS } from "@shared/const";

// URL base para el backend de AutomataAI
export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

// Generate login URL at runtime so redirect URI reflects the current origin.
export const getLoginUrl = () => {
    // Para AutomataAI con JWT, redirigimos a /login localmente si no hay token
    return "/login";
};
