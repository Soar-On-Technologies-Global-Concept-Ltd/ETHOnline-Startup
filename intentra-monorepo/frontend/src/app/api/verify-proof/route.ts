import { NextResponse } from "next/server";
import type { IDKitResult } from "@worldcoin/idkit";

export async function POST(request: Request): Promise<Response> {
  try {
    const { rp_id, idkitResponse } = (await request.json()) as {
      rp_id: string;
      idkitResponse: IDKitResult;
    };

    if (!idkitResponse) {
      return NextResponse.json({ error: "Missing idkitResponse" }, { status: 400 });
    }

    // In dev / sandbox test mode without live World Portal RP ID:
    if (!rp_id || rp_id === "rp_staging_default" || rp_id.startsWith("mock_")) {
      return NextResponse.json({ success: true, isDev: true });
    }

    const response = await fetch(
      `https://developer.world.org/api/v4/verify/${rp_id}`,
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(idkitResponse),
      }
    );

    if (!response.ok) {
      const errorData = await response.text();
      console.error("World ID Verification failed:", errorData);
      return NextResponse.json({ error: "Verification failed" }, { status: 400 });
    }

    // Proof is valid — return success to advance transaction lifecycle
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Error verifying proof:", error);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
