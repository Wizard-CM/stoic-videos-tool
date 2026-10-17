import { useState } from "react";
import type { Options, Project } from "../../api/client";
import { ErrorMessage, LoadingMessage } from "../../components/Messages";
import { StepHeader } from "../../components/StepHeader";
import { PRIMARY_BUTTON, SECONDARY_BUTTON } from "../../components/styles";
import { useBackgroundList } from "../../hooks/useBackgroundList";
import { useCharacterList } from "../../hooks/useCharacterList";
import { useOptions } from "../../hooks/useOptions";
import { useProject } from "../../hooks/useProject";
import { useScriptValidation } from "../../hooks/useScriptValidation";
import { navigateTo, ROUTES } from "../../routes";
import { CastBackgroundSection } from "./CastBackgroundSection";
import { CastCharacterSection } from "./CastCharacterSection";
import { SpeakerList } from "./SpeakerList";

type CastEditorProps = {
  initialProject: Project;
  options: Options;
  speakers: string[];
};

function CastEditor({ initialProject, options, speakers }: CastEditorProps) {
  const [project, setProject] = useState(initialProject);
  const { characters, charactersError, reloadCharacters } = useCharacterList();
  const { backgrounds, backgroundsError, reloadBackgrounds } = useBackgroundList();
  const [activeSpeaker, setActiveSpeaker] = useState(
    () => speakers.find((speaker) => !initialProject.cast[speaker]) ?? speakers[0],
  );

  const hasEveryCharacter = speakers.every((speaker) => Boolean(project.cast[speaker]));

  return (
    <div className="flex max-w-[1120px] flex-col gap-6">
      <StepHeader projectId={project.id} title={project.title} activeStep="cast" />

      <div className="flex flex-wrap items-start gap-5">
        <SpeakerList
          projectId={project.id}
          speakers={speakers}
          cast={project.cast}
          activeSpeaker={activeSpeaker}
          onSpeakerSelect={setActiveSpeaker}
        />

        {/* Every speaker's panel stays mounted, so Claude tasks keep going while another speaker is shown. */}
        {speakers.map((speaker) => (
          <div
            key={speaker}
            className={`${speaker === activeSpeaker ? "flex" : "hidden"} min-w-0 flex-[999_1_680px] flex-col gap-5`}
          >
            <CastCharacterSection
              project={project}
              speaker={speaker}
              options={options}
              characters={characters}
              charactersError={charactersError}
              onProjectChange={setProject}
              onCharactersChange={reloadCharacters}
            />
            <CastBackgroundSection
              project={project}
              speaker={speaker}
              characters={characters}
              backgrounds={backgrounds}
              backgroundsError={backgroundsError}
              onProjectChange={setProject}
              onBackgroundsChange={reloadBackgrounds}
            />
          </div>
        ))}
      </div>

      <div className="flex flex-col items-end gap-2 border-t border-line pt-5">
        <div className="flex flex-wrap justify-end gap-2.5">
          <button
            type="button"
            className={`${SECONDARY_BUTTON} min-h-[46px]`}
            disabled={!hasEveryCharacter}
            onClick={() => navigateTo(ROUTES.projectStep(project.id, "render"))}
          >
            Skip storyboard and render
          </button>
          <button
            type="button"
            className={`${PRIMARY_BUTTON} min-h-[46px]`}
            disabled={!hasEveryCharacter}
            onClick={() => navigateTo(ROUTES.projectStep(project.id, "storyboard"))}
          >
            Continue to storyboard
          </button>
        </div>
        {!hasEveryCharacter && <p className="m-0 text-sm text-muted">Give every speaker a character to continue.</p>}
      </div>
    </div>
  );
}

function CastSpeakersLoader({ project, options }: { project: Project; options: Options }) {
  const { validation, validationError } = useScriptValidation(project.script);

  if (validationError) return <ErrorMessage message={validationError} />;
  if (!validation) return <LoadingMessage />;
  if (validation.speakers.length === 0) {
    return (
      <div className="flex max-w-[1120px] flex-col gap-6">
        <StepHeader projectId={project.id} title={project.title} activeStep="cast" />
        <p className="m-0 text-[15px] text-muted">
          No speakers found in the script. <a href={ROUTES.projectStep(project.id, "script")}>Go back to the script</a>.
        </p>
      </div>
    );
  }
  return <CastEditor initialProject={project} options={options} speakers={validation.speakers} />;
}

export function CastScreen({ projectId }: { projectId: string }) {
  const { project, projectError } = useProject(projectId);
  const { options, optionsError } = useOptions();

  if (projectError || optionsError) return <ErrorMessage message={projectError ?? optionsError} />;
  if (!project || !options) return <LoadingMessage />;
  return <CastSpeakersLoader project={project} options={options} />;
}
