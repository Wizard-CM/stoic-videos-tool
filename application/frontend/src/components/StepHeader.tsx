import type { ReactNode } from "react";
import { PROJECT_STEPS, ROUTES, type ProjectStep } from "../routes";

const STEP_LABELS: Record<ProjectStep, string> = {
  script: "Script",
  cast: "Cast",
  storyboard: "Storyboard (optional)",
  render: "Render",
};

const DONE_CIRCLE = "border-success-line bg-success-soft text-success";
const ACTIVE_CIRCLE = "border-accent bg-accent text-white";
const TODO_CIRCLE = "border-soft-line bg-surface text-muted";

type StepHeaderProps = {
  projectId: string;
  title: string;
  activeStep: ProjectStep;
  // Shown on the right of the title, e.g. "All changes saved".
  statusText?: ReactNode;
};

function getStepClasses(stepIndex: number, activeIndex: number) {
  if (stepIndex < activeIndex) return { circle: DONE_CIRCLE, label: "font-normal text-ink-soft" };
  if (stepIndex === activeIndex) return { circle: ACTIVE_CIRCLE, label: "font-semibold text-ink" };
  return { circle: TODO_CIRCLE, label: "font-normal text-muted" };
}

export function StepHeader({ projectId, title, activeStep, statusText }: StepHeaderProps) {
  const activeIndex = PROJECT_STEPS.indexOf(activeStep);

  return (
    <header className="flex flex-col gap-3.5">
      <p className="m-0 text-sm text-muted">
        <a href={ROUTES.projects}>Projects</a> / {title}
      </p>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="m-0 text-[28px] font-semibold tracking-[-0.01em]">{title}</h1>
        {statusText && <span className="text-sm text-muted">{statusText}</span>}
      </div>
      <ol aria-label="Steps" className="m-0 flex list-none flex-wrap gap-x-5 gap-y-1.5 p-0">
        {PROJECT_STEPS.map((step, stepIndex) => {
          const stepClasses = getStepClasses(stepIndex, activeIndex);
          return (
            <li key={step}>
              <a
                href={ROUTES.projectStep(projectId, step)}
                aria-current={step === activeStep ? "step" : undefined}
                className={`flex min-h-11 items-center gap-2 text-[14.5px] no-underline hover:text-ink ${stepClasses.label}`}
              >
                <span
                  className={`inline-flex size-[26px] items-center justify-center rounded-full border text-[13px] font-semibold ${stepClasses.circle}`}
                >
                  {stepIndex + 1}
                </span>
                {STEP_LABELS[step]}
              </a>
            </li>
          );
        })}
      </ol>
    </header>
  );
}
