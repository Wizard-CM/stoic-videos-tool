import { useEffect, useState } from "react";
import { getErrorMessage, getOptions, type Options } from "../api/client";

export function useOptions() {
  const [options, setOptions] = useState<Options | null>(null);
  const [optionsError, setOptionsError] = useState<string | null>(null);

  useEffect(() => {
    getOptions()
      .then(setOptions)
      .catch((error) => setOptionsError(getErrorMessage(error)));
  }, []);

  return { options, optionsError };
}
