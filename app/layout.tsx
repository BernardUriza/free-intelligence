import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AIRE front",
  description: "The waiter — a read-only console over the database AIRE writes",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
