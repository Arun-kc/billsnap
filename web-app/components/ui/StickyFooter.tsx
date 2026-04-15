interface StickyFooterProps {
  children: React.ReactNode;
  className?: string;
}

export default function StickyFooter({
  children,
  className = "",
}: StickyFooterProps) {
  return (
    <div
      className={`fixed bottom-0 left-0 right-0 z-40 bg-white border-t border-[var(--color-border)] px-5 pt-3 pb-3 ${className}`}
      style={{ paddingBottom: "calc(0.75rem + env(safe-area-inset-bottom, 0px))" }}
    >
      {children}
    </div>
  );
}
