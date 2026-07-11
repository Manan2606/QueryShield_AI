import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "QueryShield AI",
  description: "Governed natural-language analytics workspace",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}