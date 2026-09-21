import type { NextConfig } from "next";

// App hibrida Databricks Apps (reglas/07-estado-actual.md, "Migracion
// Next.js a Databricks App"): el backend FastAPI corre en la MISMA
// Databricks App, en loopback puro (127.0.0.1:8001, ver backend/app.py
// __main__) -- nunca alcanzable desde afuera. Next.js es el unico puerto
// publico (DATABRICKS_APP_PORT) y proxea /api/* server-side hacia el
// backend via rewrites, asi el browser solo le habla a Next.js (mismo
// origin, sin CORS). El mismo rewrite corre en `next dev`, asi que local
// no necesita una backend URL propia -- levantar `python -m backend.app`
// en :8001 alcanza. 8001 y no 8000: DATABRICKS_APP_PORT (el puerto que
// toma Next.js) resulto ser 8000 en este workspace -- hallazgo real en
// vivo, los dos procesos colisionaban bindeando el mismo puerto.
const BACKEND_INTERNAL_URL = "http://127.0.0.1:8001";

const nextConfig: NextConfig = {
  // Hallazgo real en vivo: el rewrite de arriba mata la conexión a los 30s
  // por default (server/lib/router-utils/proxy-request.js, hardcodeado
  // cuando experimental.proxyTimeout es undefined) -- suficiente para una
  // ficha de un pokemon (1 tool call), no para una comparación (2 tool
  // calls + más texto generado), que tiraba "socket hang up" del lado de
  // Next.js sin que el backend llegara a loguear el request. 120s alcanzó
  // para comparación/matchups pero NO para multi-agente (orchestrator.py
  // corre los subagentes en serie, no paralelo -- plan + hasta 3 subagentes
  // + síntesis, cada uno su propia llamada a la Messages API -- probado en
  // vivo: superó los 120s real). 300s (5 min) cubre ese caso con margen.
  experimental: {
    proxyTimeout: 300000,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND_INTERNAL_URL}/api/:path*`,
      },
    ];
  },
  images: {
    // reglas/04-frontend.md: imagenes solo de PokeAPI (official-artwork),
    // nunca de Bulbapedia -- unico host que las tools devuelven en image_url.
    remotePatterns: [
      {
        protocol: "https",
        hostname: "raw.githubusercontent.com",
        pathname: "/PokeAPI/sprites/**",
      },
    ],
  },
};

export default nextConfig;
