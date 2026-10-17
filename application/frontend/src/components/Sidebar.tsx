import type { ReactNode } from "react";
import { ROUTES } from "../routes";
import { CharactersIcon, LogoIcon, ProjectsIcon } from "./icons";

type SidebarProps = {
  activeSection: "projects" | "characters";
};

const ACTIVE_LINK = "bg-accent-soft font-semibold text-accent-dark hover:text-accent-dark";
const INACTIVE_LINK = "text-ink-soft hover:text-ink";

type SidebarLinkProps = {
  href: string;
  isActive: boolean;
  icon: ReactNode;
  label: string;
};

function SidebarLink({ href, isActive, icon, label }: SidebarLinkProps) {
  return (
    <a
      href={href}
      aria-current={isActive ? "page" : undefined}
      className={`flex min-h-11 items-center gap-2.5 rounded-lg px-3 text-[15px] no-underline ${isActive ? ACTIVE_LINK : INACTIVE_LINK}`}
    >
      {icon}
      {label}
    </a>
  );
}

export function Sidebar({ activeSection }: SidebarProps) {
  return (
    <nav
      aria-label="Main"
      className="flex max-w-60 flex-[1_1_200px] flex-col gap-1 border-r border-line bg-surface px-4 py-6"
    >
      <div className="flex items-center gap-2.5 px-2.5 pb-6">
        <LogoIcon />
        <span className="text-lg font-semibold">ToonForge</span>
      </div>
      <SidebarLink
        href={ROUTES.projects}
        isActive={activeSection === "projects"}
        icon={<ProjectsIcon />}
        label="Projects"
      />
      <SidebarLink
        href={ROUTES.characters}
        isActive={activeSection === "characters"}
        icon={<CharactersIcon />}
        label="Characters"
      />
      <p className="mx-3 mt-auto pt-6 text-[13px] text-muted">Runs fully offline on this PC.</p>
    </nav>
  );
}
