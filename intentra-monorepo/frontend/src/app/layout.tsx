import type { Metadata } from "next";
import { Exo_2 } from "next/font/google";
import { Toaster } from "sonner";
import { PrivyProviderWrapper } from "@/components/providers/PrivyProviderWrapper";
import "./globals.css";

const exo2 = Exo_2({ 
  subsets: ["latin"], 
  variable: "--font-exo2",
  display: "swap",
});

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
      <body className={`${exo2.variable} font-sans antialiased bg-background text-foreground min-h-screen`}>
        <PrivyProviderWrapper>
          {children}
          <Toaster theme="dark" position="bottom-right" />
        </PrivyProviderWrapper>
      </body>
    </html>
  );
}
