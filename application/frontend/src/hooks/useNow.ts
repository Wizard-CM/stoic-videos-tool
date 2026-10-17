import { useEffect, useState } from "react";

// The current time in ms, updated every second while `isTicking` is true.
export function useNow(isTicking: boolean) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!isTicking) return;
    setNow(Date.now());
    const intervalId = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(intervalId);
  }, [isTicking]);

  return now;
}
