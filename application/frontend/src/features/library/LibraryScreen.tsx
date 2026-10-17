import { ROUTES, type LibraryTab } from "../../routes";
import { BackgroundsTab } from "./BackgroundsTab";
import { CharactersTab } from "./CharactersTab";

const TABS: { tab: LibraryTab; label: string }[] = [
  { tab: "characters", label: "Characters" },
  { tab: "backgrounds", label: "Backgrounds" },
];

const ACTIVE_TAB = "border-accent font-semibold text-ink hover:text-ink";
const INACTIVE_TAB = "border-transparent text-muted hover:text-ink";

export function LibraryScreen({ tab }: { tab: LibraryTab }) {
  return (
    <div className="flex max-w-[1040px] flex-col gap-6">
      <div className="flex flex-col gap-1.5">
        <h1 className="m-0 text-[30px] font-semibold tracking-[-0.01em]">Library</h1>
        <p className="m-0 text-[15px] text-muted">Characters and backgrounds you can reuse in any video.</p>
      </div>

      <nav aria-label="Library sections" className="flex gap-6 border-b border-line">
        {TABS.map((tabItem) => {
          const isActive = tabItem.tab === tab;
          return (
            <a
              key={tabItem.tab}
              href={ROUTES.library(tabItem.tab)}
              aria-current={isActive ? "page" : undefined}
              className={`-mb-px flex min-h-11 items-center border-b-2 text-[15px] no-underline ${isActive ? ACTIVE_TAB : INACTIVE_TAB}`}
            >
              {tabItem.label}
            </a>
          );
        })}
      </nav>

      {tab === "characters" ? <CharactersTab /> : <BackgroundsTab />}
    </div>
  );
}
