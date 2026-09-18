import type { Metadata } from "next";
import { Baloo_2, Geist } from "next/font/google";
import "./globals.css";
import ThemeProvider from "./theme-provider";

const geistSans = Geist({
  variable: "--font-body",
  subsets: ["latin"],
});

const baloo = Baloo_2({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["600", "700"],
});

export const metadata: Metadata = {
  title: "Pokédex — Edición Día/Noche",
  description:
    "Laboratorio del Profesor Oak: consultá stats, comparaciones y matchups de tipo con tema Día (Hada/Luz) y Noche (Fantasma/Siniestro).",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="es"
      className={`${geistSans.variable} ${baloo.variable}`}
      suppressHydrationWarning
    >
      <body>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
