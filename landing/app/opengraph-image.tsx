import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "BillSnap — Snap a Bill, Export to Excel";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OGImage() {
  return new ImageResponse(
    (
      <div
        style={{
          background: "#FFFBF7",
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "sans-serif",
          padding: "80px",
        }}
      >
        {/* Logo */}
        <div
          style={{
            fontSize: 48,
            fontWeight: 800,
            color: "#FF6B35",
            letterSpacing: "-1px",
            marginBottom: 32,
          }}
        >
          BillSnap
        </div>

        {/* Headline */}
        <div
          style={{
            fontSize: 64,
            fontWeight: 800,
            color: "#1A1A1A",
            textAlign: "center",
            lineHeight: 1.15,
            maxWidth: 900,
          }}
        >
          Stop typing bills.{" "}
          <span style={{ color: "#FF6B35" }}>Just snap and done.</span>
        </div>

        {/* Sub */}
        <div
          style={{
            fontSize: 28,
            color: "#6B7280",
            textAlign: "center",
            marginTop: 28,
            maxWidth: 800,
            lineHeight: 1.4,
          }}
        >
          Turn your bill photos into Excel sheets — in minutes.
          <br />
          Built for Indian shop owners.
        </div>

        {/* Badges */}
        <div
          style={{
            display: "flex",
            gap: 16,
            marginTop: 48,
          }}
        >
          {["🇮🇳 Made in India", "₹0 to try", "Free early access"].map(
            (badge) => (
              <div
                key={badge}
                style={{
                  background: "#FFF0E8",
                  border: "1px solid #FFCDB0",
                  borderRadius: 999,
                  padding: "10px 24px",
                  fontSize: 22,
                  color: "#C94B0A",
                  fontWeight: 600,
                }}
              >
                {badge}
              </div>
            )
          )}
        </div>
      </div>
    ),
    { ...size }
  );
}
