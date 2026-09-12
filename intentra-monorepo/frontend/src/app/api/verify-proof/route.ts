import { NextResponse } from "next/server";
import type { IDKitResult } from "@worldcoin/idkit";

export async function POST(request: Request): Promise<Response> {
  try {
    const { rp_id, idkitResponse } = (await request.json()) as {
      rp_id: string;
      idkitResponse: IDKitResult;
    };

    if (!rp_id || !idkitResponse) {
      return NextResponse.json({ error: "Missing rp_id or idkitResponse" }, { status: 400 });
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

    // Proof is valid — in a production system, we would forward this to FastAPI
    // to store the nullifier in the Postgres DB to prevent replay attacks.
    // For this frontend flow, returning success is sufficient to advance the UI.
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Error verifying proof:", error);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
