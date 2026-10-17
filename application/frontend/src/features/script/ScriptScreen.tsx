import { useState } from "react";
import type { Options, Project } from "../../api/client";
import { ErrorMessage, LoadingMessage } from "../../components/Messages";
import { SaveStatus } from "../../components/SaveStatus";
import { StepHeader } from "../../components/StepHeader";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { useOptions } from "../../hooks/useOptions";
import { useProject } from "../../hooks/useProject";
import { useScriptValidation } from "../../hooks/useScriptValidation";
import { navigateTo, ROUTES } from "../../routes";
import { ScriptBox } from "./ScriptBox";
import { ScriptSettingsPanel } from "./ScriptSettingsPanel";
import { useScriptDraft } from "./useScriptDraft";
import { ValidationSummary } from "./ValidationSummary";

const VALIDATE_DELAY_MS = 400;

type ScriptEditorProps = {
  project: Project;
  options: Options;
};

function ScriptEditor({ project, options }: ScriptEditorProps) {
  const { draft, updateDraft, hasUnsavedChanges, saveError, saveUnsavedChanges } = useScriptDraft(project);
  const debouncedScript = useDebouncedValue(draft.script, VALIDATE_DELAY_MS);
  const { validation, validationError } = useScriptValidation(debouncedScript);
  const [isContinuing, setIsContinuing] = useState(false);
  const [continueError, setContinueError] = useState<string | null>(null);

  const estimatedLengthSeconds = validation?.estimated_length_s ?? project.estimated_length_s;
  const hasScriptErrors = validation === null || validation.error_count > 0;

  const handleContinueClick = async () => {
    setIsContinuing(true);
    setContinueError(null);
    const isSaved = await saveUnsavedChanges();
    if (isSaved) {
      navigateTo(ROUTES.projectStep(project.id, "cast"));
      return;
    }
    setContinueError("Your changes aren’t saved yet. Try again.");
    setIsContinuing(false);
  };

  return (
    <div className="flex max-w-[1080px] flex-col gap-6">
      <StepHeader
        title={draft.title}
        activeStep={1}
        statusText={<SaveStatus hasUnsavedChanges={hasUnsavedChanges} saveError={saveError} />}
      />

      <div className="flex flex-wrap items-start gap-6">
        <section aria-label="Script" className="flex min-w-0 flex-[999_1_520px] flex-col gap-3">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="m-0 text-[17px] font-semibold">Script</h2>
            <p className="m-0 text-[13.5px] text-muted">One line per turn: NAME [emotion]: dialogue</p>
          </div>
          <ScriptBox
            script={draft.script}
            issues={validation?.issues ?? []}
            onScriptChange={(script) => updateDraft({ script })}
          />
          <ValidationSummary validation={validation} validationError={validationError} />
        </section>

        <ScriptSettingsPanel
          options={options}
          title={draft.title}
          settings={draft.settings}
          estimatedLengthSeconds={estimatedLengthSeconds}
          isContinueDisabled={hasScriptErrors || isContinuing}
          continueError={continueError}
          onTitleChange={(title) => updateDraft({ title })}
          onSettingsChange={(settings) => updateDraft({ settings })}
          onContinueClick={handleContinueClick}
        />
      </div>
    </div>
  );
}

export function ScriptScreen({ projectId }: { projectId: string }) {
  const { project, projectError } = useProject(projectId);
  const { options, optionsError } = useOptions();

  if (projectError || optionsError) return <ErrorMessage message={projectError ?? optionsError} />;
  if (!project || !options) return <LoadingMessage />;
  return <ScriptEditor project={project} options={options} />;
}
