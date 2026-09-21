import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Esqueleto de validación (reglas/07-estado-actual.md, tercer intento de
  // frontend real): Databricks Apps no corre `next start` con el repo
  // fuente -- necesita el build standalone (server.js autocontenido) para
  // funcionar como server real, no export estático.
  output: "standalone",
};

export default nextConfig;
