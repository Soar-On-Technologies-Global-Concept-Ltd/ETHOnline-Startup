import { NextResponse } from "next/server";
import { signRequest } from "@worldcoin/idkit-core/signing";

export async function POST(request: Request): Promise<Response> {
  try {
    const { action } = await request.json();
    const signingKeyHex = process.env.RP_SIGNING_KEY;

    if (!signingKeyHex) {
      // In dev/demo environment without signing key, return a mock RP signature
      return NextResponse.json({
        sig: "0x_mock_rp_signature_for_dev_mode",
        nonce: "nonce_" + Math.random().toString(36).substring(7),
        created_at: Math.floor(Date.now() / 1000),
        expires_at: Math.floor(Date.now() / 1000) + 3600,
      });
    }

    const { sig, nonce, createdAt, expiresAt } = signRequest({
      signingKeyHex,
      action,
    });

    return NextResponse.json({
      sig,
      nonce,
      created_at: createdAt,
      expires_at: expiresAt,
    });
  } catch (error) {
    console.error("Error generating RP signature:", error);
    return NextResponse.json({ error: "Failed to generate signature" }, { status: 500 });
  }
}
