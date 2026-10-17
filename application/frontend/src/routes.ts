export type ProjectStep = "script" | "cast" | "storyboard" | "render";

export type LibraryTab = "characters" | "backgrounds";

export type Route =
  | { name: "projects" }
  | { name: "project-step"; projectId: string; step: ProjectStep }
  | { name: "library"; tab: LibraryTab }
  // `characterId` / `backgroundId` are null when designing a new one.
  | { name: "character-studio"; characterId: string | null }
  | { name: "background-studio"; backgroundId: string | null }
  | { name: "not-found" };

export const ROUTES = {
  projects: "#/",
  library: (tab: LibraryTab = "characters") => (tab === "characters" ? "#/library" : "#/library/backgrounds"),
  newCharacter: "#/characters/new",
  editCharacter: (characterId: string) => `#/characters/${characterId}`,
  newBackground: "#/backgrounds/new",
  editBackground: (backgroundId: string) => `#/backgrounds/${backgroundId}`,
  projectStep: (projectId: string, step: ProjectStep) => `#/projects/${projectId}/${step}`,
};

export const PROJECT_STEPS: ProjectStep[] = ["script", "cast", "storyboard", "render"];

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

  if (pathParts[0] === "library" && pathParts.length <= 2) {
    return { name: "library", tab: pathParts[1] === "backgrounds" ? "backgrounds" : "characters" };
  }

  if (pathParts[0] === "characters" || pathParts[0] === "backgrounds") {
    const isCharacter = pathParts[0] === "characters";
    if (pathParts.length === 1) return { name: "library", tab: isCharacter ? "characters" : "backgrounds" };
    const itemId = pathParts[1] === "new" ? null : pathParts[1];
    if (isCharacter) return { name: "character-studio", characterId: itemId };
    return { name: "background-studio", backgroundId: itemId };
  }

  return { name: "not-found" };
}
