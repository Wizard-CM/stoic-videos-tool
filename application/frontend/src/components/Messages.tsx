// Small inline messages used next to the action that failed, and while data loads.

export function ErrorMessage({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p role="alert" className="m-0 text-sm text-danger">
      {message}
    </p>
  );
}

export function LoadingMessage({ text = "Loading…" }: { text?: string }) {
  return <p className="m-0 text-[15px] text-muted">{text}</p>;
}
