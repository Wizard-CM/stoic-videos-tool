import type { ReactNode } from "react";

type PageHeaderProps = {
  parentLabel: string;
  parentHref: string;
  title: string;
  // Shown on the right of the title, e.g. "All changes saved".
  statusText?: ReactNode;
};

// Breadcrumb and title for pages under the library.
export function PageHeader({ parentLabel, parentHref, title, statusText }: PageHeaderProps) {
  return (
    <header className="flex flex-col gap-3.5">
      <p className="m-0 text-sm text-muted">
        <a href={parentHref}>{parentLabel}</a> / {title}
      </p>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="m-0 text-[28px] font-semibold tracking-[-0.01em]">{title}</h1>
        {statusText && <span className="text-sm text-muted">{statusText}</span>}
      </div>
    </header>
  );
}
