import { NextRequest, NextResponse } from "next/server";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
// Indian mobile: 10 digits optionally prefixed with +91 or 0
const PHONE_RE = /^(\+91|0)?[6-9]\d{9}$/;

function isValidContact(contact: string): boolean {
  return EMAIL_RE.test(contact) || PHONE_RE.test(contact.replace(/\s/g, ""));
}

export async function POST(request: NextRequest) {
  let body: unknown;

  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid request" }, { status: 400 });
  }

  if (
    typeof body !== "object" ||
    body === null ||
    !("contact" in body) ||
    typeof (body as Record<string, unknown>).contact !== "string"
  ) {
    return NextResponse.json({ error: "Invalid contact" }, { status: 400 });
  }

  const contact = ((body as Record<string, unknown>).contact as string).trim();

  if (!isValidContact(contact)) {
    return NextResponse.json(
      { error: "Please enter a valid email or 10-digit WhatsApp number." },
      { status: 400 }
    );
  }

  // Forward to BillSnap FastAPI backend
  const apiBase = process.env.BILLSNAP_API_URL;
  if (!apiBase) {
    return NextResponse.json({ error: "Service unavailable." }, { status: 503 });
  }

  try {
    const upstream = await fetch(`${apiBase}/api/v1/waitlist`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ contact }),
    });

    if (upstream.ok || upstream.status === 409) {
      // 409 = already signed up — still treat as success (don't leak)
      return NextResponse.json({ success: true });
    }

    const err = (await upstream.json().catch(() => ({}))) as { detail?: string };
    return NextResponse.json(
      { error: err.detail ?? "Something went wrong. Please try again." },
      { status: 400 }
    );
  } catch {
    return NextResponse.json(
      { error: "Could not connect. Please try again." },
      { status: 503 }
    );
  }
}
