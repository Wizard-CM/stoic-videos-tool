import type { ProjectListItem } from "../../api/client";
import type { ChipTone } from "../../components/StatusChip";
import { formatDuration, formatEditedDate } from "../../lib/format";
import { ROUTES } from "../../routes";

export function getProjectChip(project: ProjectListItem): { label: string; tone: ChipTone } {
  if (project.progress !== null) {
    const roundedProgress = Math.round(project.progress);
    if (project.status === "rendering") return { label: `Rendering ${roundedProgress}%`, tone: "busy" };
    return { label: `Storyboard ${roundedProgress}%`, tone: "busy" };
  }

  if (project.status === "ready") return { label: "Ready", tone: "ready" };
  if (project.status === "rendering") return { label: "Rendering", tone: "busy" };
  if (project.status === "storyboarded") return { label: "Storyboard ready", tone: "draft" };
  if (project.status === "stopped") return { label: "Stopped", tone: "warning" };
  if (project.status === "failed") return { label: "Failed", tone: "failed" };
  return { label: "Draft", tone: "draft" };
}

function getLengthText(project: ProjectListItem) {
  if (project.length_s !== null) return formatDuration(project.length_s);
  if (project.estimated_length_s > 0) return `About ${formatDuration(project.estimated_length_s)}`;
  return "No script yet";
}

// "2 min 14 s, 16:9, edited today"
export function getProjectMeta(project: ProjectListItem) {
  return `${getLengthText(project)}, ${project.aspect}, ${formatEditedDate(project.updated_at)}`;
}

// Opens the project on the step it most likely needs next.
export function getProjectOpenRoute(project: ProjectListItem) {
  if (project.status === "draft") return ROUTES.projectStep(project.id, "script");
  if (project.status === "storyboarded") return ROUTES.projectStep(project.id, "storyboard");
  return ROUTES.projectStep(project.id, "render");
}
