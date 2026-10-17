export type ProjectStep = "script" | "cast" | "storyboard" | "render";

export type Route =
  | { name: "projects" }
  | { name: "project-step"; projectId: string; step: ProjectStep }
  | { name: "characters" }
  | { name: "new-character" }
  | { name: "edit-character"; characterId: string }
  | { name: "not-found" };

export const ROUTES = {
  projects: "#/",
  characters: "#/characters",
  newCharacter: "#/characters/new",
  editCharacter: (characterId: string) => `#/characters/${characterId}`,
  projectStep: (projectId: string, step: ProjectStep) => `#/projects/${projectId}/${step}`,
};

const PROJECT_STEPS: ProjectStep[] = ["script", "cast", "storyboard", "render"];

export function navigateTo(routeHash: string) {
  window.location.hash = routeHash;
}

function isProjectStep(value: string): value is ProjectStep {
  return PROJECT_STEPS.includes(value as ProjectStep);
}

export function parseRoute(hash: string): Route {
  const pathParts = hash.replace(/^#\/?/, "").split("/").filter(Boolean);

  if (pathParts.length === 0) return { name: "projects" };

  if (pathParts[0] === "projects" && pathParts.length === 3 && isProjectStep(pathParts[2])) {
    return { name: "project-step", projectId: pathParts[1], step: pathParts[2] };
  }

  if (pathParts[0] === "characters") {
    if (pathParts.length === 1) return { name: "characters" };
    if (pathParts[1] === "new") return { name: "new-character" };
    return { name: "edit-character", characterId: pathParts[1] };
  }

  return { name: "not-found" };
}
