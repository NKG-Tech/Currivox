import "./globals.css";
import { ReactNode } from "react";

export const metadata = {
  title: "CV-Agent",
  description: "Analyse et génération intelligente de CV",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
