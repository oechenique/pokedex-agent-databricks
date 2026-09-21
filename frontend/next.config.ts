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
