// Small typed client for the ToonForge local API (see docs/API.md).

// ---------- Shared types ----------

export type ParamValue = string | number | boolean;

// Param keys come from GET /api/options, so the UI never hardcodes them.
export type CharacterParams = Record<string, ParamValue>;

export type Voice = {
  voice_id: string;
  auto: boolean;
  pitch: number;
  speed: number;
};

export type CharacterBackground = {
  generator: string;
  seed: number;
};

export type Character = {
  id?: string | null;
  name: string;
  description: string;
  params: CharacterParams;
  voice: Voice;
  background: CharacterBackground;
  seed: number;
  created_at?: string;
  updated_at?: string;
};

export type ProjectSettings = {
  aspect: string;
  music: boolean;
  quality: string;
};

export type CastEntry = {
  character: Character;
  library_id: string | null;
};

export type ProjectStatus = "draft" | "storyboarded" | "rendering" | "stopped" | "ready" | "failed";

export type Project = {
  id: string;
  title: string;
  script: string;
  settings: ProjectSettings;
  cast: Record<string, CastEntry>;
  status: ProjectStatus;
  length_s: number | null;
  estimated_length_s: number;
  output_url: string | null;
  output_path: string | null;
  has_storyboard: boolean;
  created_at: string;
  updated_at: string;
};

export type ProjectListItem = {
  id: string;
  title: string;
  status: ProjectStatus;
  length_s: number | null;
  estimated_length_s: number;
  aspect: string;
  updated_at: string;
  has_thumbnail: boolean;
  progress: number | null;
};

export type ProjectChanges = {
  title?: string;
  script?: string;
  settings?: Partial<ProjectSettings>;
};

export type ChoiceOption = {
  value: string;
  label: string;
};

export type Control = {
  key: string;
  label: string;
  section: string;
  type: "slider" | "select" | "color" | "toggle";
  low?: string;
  high?: string;
  options?: ChoiceOption[];
  options_by_gender?: Record<string, ChoiceOption[]>;
  swatches?: ChoiceOption[];
};

export type VoiceOption = {
  id: string;
  label: string;
  gender: string;
  age: string;
};

export type Options = {
  controls: Control[];
  sections: string[];
  emotions: ChoiceOption[];
  backgrounds: ChoiceOption[];
  voices: VoiceOption[];
  aspects: ChoiceOption[];
  qualities: ChoiceOption[];
  max_length_s: number;
};

export type ScriptLine = {
  line_no: number;
  speaker: string;
  emotion: string | null;
  intensity: number | null;
  text: string;
  tagged: boolean;
};

export type ScriptIssue = {
  line_no: number | null;
  level: "error" | "warning";
  message: string;
};

export type ScriptValidation = {
  lines: ScriptLine[];
  speakers: string[];
  issues: ScriptIssue[];
  error_count: number;
  warning_count: number;
  estimated_length_s: number;
};

export type AutofillResult = {
  character: Character;
  matched: string[];
  unmatched: string[];
};

export type PreflightCheck = {
  key: string;
  label: string;
  ok: boolean;
  message: string;
};

export type Preflight = {
  ok: boolean;
  checks: PreflightCheck[];
};

export type JobState = "queued" | "running" | "done" | "failed" | "cancelled" | "stopped";

export type JobStage = {
  key: string;
  label: string;
  state: "done" | "active" | "waiting" | "skipped";
  note: string;
};

export type Job = {
  kind: "storyboard" | "render";
  state: JobState;
  percent: number;
  eta_s: number | null;
  message: string;
  stages: JobStage[];
  chunk: { done: number; total: number } | null;
  latest_frame_url: string | null;
  latest_frame_caption: string | null;
  error: string | null;
  started_at: string;
  updated_at: string;
};

export type StoryboardFrame = {
  t: number;
  t_label: string;
  shot_label: string;
  caption: string;
  url: string;
};

export type Storyboard = {
  length_s: number;
  shot_count: number;
  cutaway_count: number;
  longest_pause_s: number;
  frames: StoryboardFrame[];
  preview_url: string;
  preview_length_s: number;
  aspect: string;
};

// ---------- Request helpers ----------

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function readErrorDetail(response: Response) {
  const fallbackMessage = `Request failed (${response.status}).`;
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    // FastAPI validation errors (422) send a list of { msg } objects.
    if (Array.isArray(body.detail)) {
      return body.detail.map((item: { msg?: string }) => item.msg).join(" ");
    }
    return fallbackMessage;
  } catch {
    return fallbackMessage;
  }
}

async function sendRequest(path: string, init?: RequestInit) {
  const response = await fetch(path, init);
  if (!response.ok) {
    throw new ApiError(await readErrorDetail(response), response.status);
  }
  return response;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await sendRequest(path, init);
  return response.json();
}

async function requestBlob(path: string, init?: RequestInit) {
  const response = await sendRequest(path, init);
  return response.blob();
}

function withJsonBody(method: string, body?: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  };
}

export function getErrorMessage(error: unknown) {
  if (error instanceof Error) return error.message;
  return "Something went wrong.";
}

// ---------- Options and script ----------

export function getOptions() {
  return requestJson<Options>("/api/options");
}

export function validateScript(script: string) {
  return requestJson<ScriptValidation>("/api/script/validate", withJsonBody("POST", { script }));
}

// ---------- Projects ----------

export function listProjects() {
  return requestJson<ProjectListItem[]>("/api/projects");
}

export function createProject(title?: string) {
  return requestJson<Project>("/api/projects", withJsonBody("POST", { title }));
}

export function getProject(projectId: string) {
  return requestJson<Project>(`/api/projects/${projectId}`);
}

export function updateProject(projectId: string, changes: ProjectChanges) {
  return requestJson<Project>(`/api/projects/${projectId}`, withJsonBody("PUT", changes));
}

export function duplicateProject(projectId: string) {
  return requestJson<Project>(`/api/projects/${projectId}/duplicate`, { method: "POST" });
}

export function deleteProject(projectId: string) {
  return requestJson<{ ok: boolean }>(`/api/projects/${projectId}`, { method: "DELETE" });
}

export function getProjectThumbnailUrl(projectId: string, version: string) {
  return `/api/projects/${projectId}/thumbnail.png?v=${encodeURIComponent(version)}`;
}

export function setCastMember(projectId: string, speaker: string, castEntry: CastEntry) {
  return requestJson<Project>(
    `/api/projects/${projectId}/cast/${encodeURIComponent(speaker)}`,
    withJsonBody("PUT", castEntry),
  );
}

export function removeCastMember(projectId: string, speaker: string) {
  return requestJson<Project>(`/api/projects/${projectId}/cast/${encodeURIComponent(speaker)}`, {
    method: "DELETE",
  });
}

// ---------- Characters ----------

export function listCharacters() {
  return requestJson<Character[]>("/api/characters");
}

export function createCharacter(character: Character) {
  return requestJson<Character>("/api/characters", withJsonBody("POST", character));
}

export function getCharacter(characterId: string) {
  return requestJson<Character>(`/api/characters/${characterId}`);
}

export function updateCharacter(characterId: string, character: Character) {
  return requestJson<Character>(`/api/characters/${characterId}`, withJsonBody("PUT", character));
}

export function deleteCharacter(characterId: string) {
  return requestJson<{ ok: boolean }>(`/api/characters/${characterId}`, { method: "DELETE" });
}

export function importCharacter(characterJson: unknown) {
  return requestJson<Character>("/api/characters/import", withJsonBody("POST", characterJson));
}

export function getCharacterExportUrl(characterId: string) {
  return `/api/characters/${characterId}/export`;
}

export function getCharacterAvatarUrl(characterId: string, size: number, version = "") {
  return `/api/characters/${characterId}/avatar.png?size=${size}&v=${encodeURIComponent(version)}`;
}

export function newCharacter(defaults: { name?: string; gender?: string }) {
  return requestJson<Character>("/api/characters/new", withJsonBody("POST", defaults));
}

export function autofillCharacter(description: string, character: Character) {
  return requestJson<AutofillResult>(
    "/api/characters/autofill",
    withJsonBody("POST", { description, character }),
  );
}

export function randomizeCharacter(character: Character) {
  return requestJson<{ character: Character }>(
    "/api/characters/randomize",
    withJsonBody("POST", { character }),
  );
}

export function pickAutoVoice(gender: string, age: string, excludedVoiceIds: string[]) {
  return requestJson<{ voice_id: string }>(
    "/api/characters/auto-voice",
    withJsonBody("POST", { gender, age, exclude: excludedVoiceIds }),
  );
}

export function renderCharacterPreview(character: Character, emotion: string) {
  return requestBlob("/api/characters/preview", withJsonBody("POST", { character, emotion }));
}

export function renderVoiceSample(voice: Voice) {
  return requestBlob("/api/voices/sample", withJsonBody("POST", { voice }));
}

// ---------- Jobs, storyboard and render ----------

export function getPreflight(projectId: string) {
  return requestJson<Preflight>(`/api/projects/${projectId}/preflight`);
}

export function startStoryboard(projectId: string) {
  return requestJson<Job>(`/api/projects/${projectId}/storyboard`, { method: "POST" });
}

export function startRender(projectId: string) {
  return requestJson<Job>(`/api/projects/${projectId}/render`, { method: "POST" });
}

export function cancelJob(projectId: string) {
  return requestJson<Job>(`/api/projects/${projectId}/cancel`, { method: "POST" });
}

export function getJob(projectId: string) {
  return requestJson<Job | null>(`/api/projects/${projectId}/job`);
}

export function getStoryboard(projectId: string) {
  return requestJson<Storyboard>(`/api/projects/${projectId}/storyboard`);
}

export function getDownloadUrl(outputUrl: string) {
  const separator = outputUrl.includes("?") ? "&" : "?";
  return `${outputUrl}${separator}download=1`;
}
