import { useEffect, useState } from "react";
import { getErrorMessage, validateScript, type ScriptValidation } from "../api/client";

// Validates the given script whenever it changes. Callers debounce the script if it changes while typing.
export function useScriptValidation(script: string) {
  const [validation, setValidation] = useState<ScriptValidation | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    let isCancelled = false;

    validateScript(script)
      .then((result) => {
        if (isCancelled) return;
        setValidation(result);
        setValidationError(null);
      })
      .catch((error) => {
        if (!isCancelled) setValidationError(getErrorMessage(error));
      });

    return () => {
      isCancelled = true;
    };
  }, [script]);

  return { validation, validationError };
}
