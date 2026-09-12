import type { Metadata } from "next";
import { Inter, Outfit } from "next/font/google";
import { Toaster } from "sonner";
import { PrivyProviderWrapper } from "@/components/providers/PrivyProviderWrapper";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });
const outfit = Outfit({ subsets: ["latin"], variable: "--font-display" });

export const metadata: Metadata = {
  title: "Intentra",
  description: "AI commerce secured by cryptographic signatures",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} ${outfit.variable} font-sans antialiased bg-background text-foreground min-h-screen`}>
        <PrivyProviderWrapper>
          {children}
          <Toaster theme="dark" position="bottom-right" />
        </PrivyProviderWrapper>
      </body>
    </html>
  );
}
