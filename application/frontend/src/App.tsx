import { Sidebar } from "./components/Sidebar";
import { CastScreen } from "./features/cast/CastScreen";
import { CharacterEditScreen } from "./features/library/CharacterEditScreen";
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
  if (route.name === "characters") return <LibraryScreen />;
  if (route.name === "new-character") return <CharacterEditScreen key="new" characterId={null} />;
  if (route.name === "edit-character") {
    return <CharacterEditScreen key={route.characterId} characterId={route.characterId} />;
  }
  if (route.name === "project-step") {
    // Keyed so each step and project starts with fresh state.
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

function isCharactersRoute(route: Route) {
  return route.name === "characters" || route.name === "new-character" || route.name === "edit-character";
}

export function App() {
  const route = useHashRoute();
  const activeSection = isCharactersRoute(route) ? "characters" : "projects";

  return (
    <div className="flex min-h-screen flex-wrap bg-page font-sans text-ink">
      <Sidebar activeSection={activeSection} />
      <main className="min-w-0 flex-[999_1_560px] px-10 pt-7 pb-12">
        <RouteScreen route={route} />
      </main>
    </div>
  );
}
