import { ClaudeStatusBanner } from "./components/claude/ClaudeStatusBanner";
import { Sidebar, type SidebarSection } from "./components/Sidebar";
import { BackgroundStudioScreen } from "./features/background-studio/BackgroundStudioScreen";
import { CastScreen } from "./features/cast/CastScreen";
import { CharacterStudioScreen } from "./features/character-studio/CharacterStudioScreen";
import { LibraryScreen } from "./features/library/LibraryScreen";
import { ProjectsScreen } from "./features/projects/ProjectsScreen";
import { RenderScreen } from "./features/render/RenderScreen";
import { ScriptScreen } from "./features/script/ScriptScreen";
import { StoryboardScreen } from "./features/storyboard/StoryboardScreen";
import { useHashRoute } from "./hooks/useHashRoute";
import { ROUTES, type ProjectStep, type Route } from "./routes";

function ProjectStepScreen({ projectId, step }: { projectId: string; step: ProjectStep }) {
  if (step === "script") return <ScriptScreen projectId={projectId} />;
  if (step === "cast") return <CastScreen projectId={projectId} />;
  if (step === "storyboard") return <StoryboardScreen projectId={projectId} />;
  return <RenderScreen projectId={projectId} />;
}

function RouteScreen({ route }: { route: Route }) {
  if (route.name === "projects") return <ProjectsScreen />;
  if (route.name === "library") return <LibraryScreen tab={route.tab} />;
  if (route.name === "character-studio") {
    // Keyed so each character starts with fresh state.
    return <CharacterStudioScreen key={route.characterId ?? "new"} characterId={route.characterId} />;
  }
  if (route.name === "background-studio") {
    return <BackgroundStudioScreen key={route.backgroundId ?? "new"} backgroundId={route.backgroundId} />;
  }
  if (route.name === "project-step") {
    return (
      <ProjectStepScreen key={`${route.projectId}-${route.step}`} projectId={route.projectId} step={route.step} />
    );
  }
  return (
    <div className="flex flex-col gap-3">
      <p className="m-0 text-[15px] text-muted">This page doesn’t exist.</p>
      <a href={ROUTES.projects}>Go to projects</a>
    </div>
  );
}

function getSidebarSection(route: Route): SidebarSection {
  const isLibraryRoute =
    route.name === "library" || route.name === "character-studio" || route.name === "background-studio";
  return isLibraryRoute ? "library" : "projects";
}

export function App() {
  const route = useHashRoute();

  return (
    <div className="flex min-h-screen flex-wrap bg-page font-sans text-ink">
      <Sidebar activeSection={getSidebarSection(route)} />
      <main className="min-w-0 flex-[999_1_560px] px-10 pt-7 pb-12">
        <ClaudeStatusBanner />
        <RouteScreen route={route} />
      </main>
    </div>
  );
}
