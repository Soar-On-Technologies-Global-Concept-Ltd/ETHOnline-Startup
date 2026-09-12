"use client";

import { PrivyProvider } from "@privy-io/react-auth";
import React, { useSyncExternalStore } from "react";

const emptySubscribe = () => () => {};

declare global {
  interface BigInt {
    toJSON(): string;
  }
}

if (typeof BigInt !== 'undefined' && !BigInt.prototype.toJSON) {
  BigInt.prototype.toJSON = function (this: bigint) {
    return this.toString();
  };
}

export function PrivyProviderWrapper({ children }: { children: React.ReactNode }) {
  const isMounted = useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false
  );
  const appId = process.env.NEXT_PUBLIC_PRIVY_APP_ID;

  if (!appId || !isMounted) {
    return <>{children}</>;
  }

  return (
    <PrivyProvider
      appId={appId}
      config={{
        loginMethods: ["email"],
        appearance: {
          theme: "dark",
          accentColor: "#00ff00",
        },
        embeddedWallets: {
          ethereum: {
            createOnLogin: "users-without-wallets",
          },
        },
      }}
    >
      {children}
    </PrivyProvider>
  );
}
