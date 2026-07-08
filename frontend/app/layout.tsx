import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "QueryShield AI Test Console",
  description: "Internal backend testing console for QueryShield AI",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
