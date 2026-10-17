import type { ReactNode } from "react";
import { ROUTES } from "../routes";

const STEP_LABELS = ["Script", "Cast", "Storyboard (optional)", "Render"];

const DONE_CIRCLE = "border-success-line bg-success-soft text-success";
const ACTIVE_CIRCLE = "border-accent bg-accent text-white";
const TODO_CIRCLE = "border-soft-line bg-surface text-muted";

type StepHeaderProps = {
  title: string;
  activeStep: 1 | 2 | 3 | 4;
  // Shown on the right of the title, e.g. "All changes saved".
  statusText?: ReactNode;
};

function getStepClasses(stepNumber: number, activeStep: number) {
  if (stepNumber < activeStep) return { circle: DONE_CIRCLE, label: "font-normal text-ink-soft" };
  if (stepNumber === activeStep) return { circle: ACTIVE_CIRCLE, label: "font-semibold text-ink" };
  return { circle: TODO_CIRCLE, label: "font-normal text-muted" };
}

export function StepHeader({ title, activeStep, statusText }: StepHeaderProps) {
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
        {STEP_LABELS.map((stepLabel, index) => {
          const stepNumber = index + 1;
          const stepClasses = getStepClasses(stepNumber, activeStep);
          return (
            <li
              key={stepLabel}
              aria-current={stepNumber === activeStep ? "step" : undefined}
              className={`flex items-center gap-2 text-[14.5px] ${stepClasses.label}`}
            >
              <span
                className={`inline-flex size-[26px] items-center justify-center rounded-full border text-[13px] font-semibold ${stepClasses.circle}`}
              >
                {stepNumber}
              </span>
              {stepLabel}
            </li>
          );
        })}
      </ol>
    </header>
  );
}
