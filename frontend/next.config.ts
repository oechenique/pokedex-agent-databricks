import type { NextConfig } from "next";

const nextConfig: NextConfig = {
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
