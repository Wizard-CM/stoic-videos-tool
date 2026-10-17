// Small typed client for the ToonForge local API (see docs/API.md).

// ---------- Shared types ----------

export type Voice = {
  voice_id: string;
  auto: boolean;
  pitch: number;
  speed: number;
};

// Who made a character or background, and what it cost.
export type MadeBy = {
  task_id: string;
  cost_usd: number;
  models: string[];
};

type CharacterFields = {
  id: string;
  name: string;
  description: string;
  gender: string | null;
  age: string | null;
  voice: Voice;
  seed: number;
  made_by: MadeBy | null;
  created_at: string;
  updated_at: string;
};

// The full character. The kit is Claude's drawing (docs/PUPPET_KIT.md); the UI never edits it.
export type Character = CharacterFields & {
  kit: unknown;
  // Not promised by GET /api/characters/{id}; read through getPoseNames() in the studio.
  expressions?: string[];
  gestures?: string[];
};

// List endpoints send this instead of the full character.
export type CharacterSummary = CharacterFields & {
  expressions: string[];
  gestures: string[];
};

export type CharacterChanges = Partial<Pick<CharacterFields, "name" | "description" | "gender" | "age" | "voice">>;

type BackgroundFields = {
  id: string | null;
  name: string;
  description: string;
  made_by: MadeBy | null;
  created_at: string;
  updated_at: string;
};

export type Background = BackgroundFields & { art: unknown };

export type BackgroundSummary = BackgroundFields & { id: string };

export type BackgroundChanges = { name?: string; description?: string };

export type ProjectSettings = {
  aspect: string;
  music: boolean;
  quality: string;
};

export type CastEntry = {
  character: Character;
  library_id: string | null;
  // null means "Claude designs it for this video"; after a storyboard or render it holds that design (id null).
  background: Background | null;
  background_library_id: string | null;
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

export type VoiceOption = {
  id: string;
  label: string;
  gender: string;
  age: string;
};

export type Options = {
  emotions: ChoiceOption[];
  gestures: ChoiceOption[];
  voices: VoiceOption[];
  genders: ChoiceOption[];
  ages: ChoiceOption[];
  aspects: ChoiceOption[];
  qualities: ChoiceOption[];
  script_lengths: ChoiceOption[];
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

export type ScriptRequest = {
  idea: string;
  length: string;
  use_library: boolean;
};

// ---------- Claude ----------

export type ClaudeStatus = {
  ready: boolean;
  message: string;
  cli: string | null;
  auth: string;
  models: { lead: string; workers: { sonnet: string; haiku: string } };
};

export type ClaudeTestResult = {
  ok: boolean;
  message: string;
};

export type ClaudeTaskKind = "character" | "character_revision" | "background" | "background_revision" | "script";

export type ClaudeTaskState = "queued" | "running" | "done" | "failed" | "cancelled";

export type ClaudeActivity = {
  t: string;
  // "lead" (Opus) or a worker name such as "sonnet-worker".
  who: string;
  kind: string;
  text: string;
};

// Which fields are set depends on the task kind.
export type ClaudeTaskResult = {
  character_id?: string;
  background_id?: string;
  title?: string;
  script?: string;
};

export type ClaudeTask = {
  id: string;
  kind: ClaudeTaskKind;
  state: ClaudeTaskState;
  title: string;
  message: string;
  activity: ClaudeActivity[];
  result: ClaudeTaskResult | null;
  error: string | null;
  cost_usd: number | null;
  started_at: string;
  updated_at: string;
};

export type TaskStarted = { task_id: string };

// ---------- Jobs ----------

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
  reaction_count: number;
  frames: StoryboardFrame[];
  preview_url: string;
  preview_length_s: number;
  director_notes: string | null;
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

// "?a=1&b=x", skipping empty values.
function buildQuery(params: Record<string, string | number | null | undefined>) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") query.set(key, String(value));
  }
  const queryText = query.toString();
  return queryText ? `?${queryText}` : "";
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

export function generateScript(projectId: string, request: ScriptRequest) {
  return requestJson<TaskStarted>(`/api/projects/${projectId}/script/generate`, withJsonBody("POST", request));
}

// ---------- Claude ----------

export function getClaudeStatus() {
  return requestJson<ClaudeStatus>("/api/claude/status");
}

export function testClaude() {
  return requestJson<ClaudeTestResult>("/api/claude/test", { method: "POST" });
}

export function listClaudeTasks() {
  return requestJson<ClaudeTask[]>("/api/claude/tasks");
}

export function getClaudeTask(taskId: string) {
  return requestJson<ClaudeTask>(`/api/claude/tasks/${taskId}`);
}

export function cancelClaudeTask(taskId: string) {
  return requestJson<ClaudeTask>(`/api/claude/tasks/${taskId}/cancel`, { method: "POST" });
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
  return `/api/projects/${projectId}/thumbnail.png${buildQuery({ v: version })}`;
}

function getCastPath(projectId: string, speaker: string) {
  return `/api/projects/${projectId}/cast/${encodeURIComponent(speaker)}`;
}

// Snapshots a library character into the project; the speaker keeps its background choice.
export function setCastCharacter(projectId: string, speaker: string, libraryId: string) {
  return requestJson<Project>(getCastPath(projectId, speaker), withJsonBody("PUT", { library_id: libraryId }));
}

export function removeCastMember(projectId: string, speaker: string) {
  return requestJson<Project>(getCastPath(projectId, speaker), { method: "DELETE" });
}

// `null` means Claude designs a background for this video.
export function setCastBackground(projectId: string, speaker: string, libraryId: string | null) {
  return requestJson<Project>(
    `${getCastPath(projectId, speaker)}/background`,
    withJsonBody("PUT", { library_id: libraryId }),
  );
}

// ---------- Characters ----------

export function listCharacters() {
  return requestJson<CharacterSummary[]>("/api/characters");
}

export function getCharacter(characterId: string) {
  return requestJson<Character>(`/api/characters/${characterId}`);
}

export function generateCharacter(request: { name: string; description: string; gender?: string; age?: string }) {
  return requestJson<TaskStarted>("/api/characters/generate", withJsonBody("POST", request));
}

export function reviseCharacter(characterId: string, feedback: string) {
  return requestJson<TaskStarted>(`/api/characters/${characterId}/revise`, withJsonBody("POST", { feedback }));
}

export function updateCharacter(characterId: string, changes: CharacterChanges) {
  return requestJson<Character>(`/api/characters/${characterId}`, withJsonBody("PUT", changes));
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

export type CharacterPreviewParams = {
  expression?: string;
  gesture?: string;
  width?: number;
  height?: number;
  crop?: string;
  // Cache buster, usually the character's updated_at.
  version?: string;
};

export function getCharacterPreviewUrl(characterId: string, params: CharacterPreviewParams) {
  const { version, ...previewParams } = params;
  return `/api/characters/${characterId}/preview.png${buildQuery({ ...previewParams, v: version })}`;
}

export type CharacterSheet = "expressions" | "mouths" | "gestures" | "eyes" | "hands";

export function getCharacterSheetUrl(characterId: string, sheet: CharacterSheet, version: string) {
  return `/api/characters/${characterId}/sheet.png${buildQuery({ sheet, v: version })}`;
}

export function getCharacterAvatarUrl(characterId: string, size: number, version = "") {
  return `/api/characters/${characterId}/avatar.png${buildQuery({ size, v: version })}`;
}

export function renderVoiceSample(voice: Voice, age?: string | null) {
  return requestBlob("/api/voices/sample", withJsonBody("POST", { voice, age: age ?? undefined }));
}

// ---------- Backgrounds ----------

export function listBackgrounds() {
  return requestJson<BackgroundSummary[]>("/api/backgrounds");
}

export function getBackground(backgroundId: string) {
  return requestJson<Background>(`/api/backgrounds/${backgroundId}`);
}

export function generateBackground(request: { name: string; description: string; character_id?: string }) {
  return requestJson<TaskStarted>("/api/backgrounds/generate", withJsonBody("POST", request));
}

export function reviseBackground(backgroundId: string, feedback: string) {
  return requestJson<TaskStarted>(`/api/backgrounds/${backgroundId}/revise`, withJsonBody("POST", { feedback }));
}

export function updateBackground(backgroundId: string, changes: BackgroundChanges) {
  return requestJson<Background>(`/api/backgrounds/${backgroundId}`, withJsonBody("PUT", changes));
}

export function deleteBackground(backgroundId: string) {
  return requestJson<{ ok: boolean }>(`/api/backgrounds/${backgroundId}`, { method: "DELETE" });
}

export function getBackgroundPreviewUrl(
  backgroundId: string,
  params: { width?: number; characterId?: string | null; version?: string },
) {
  const query = buildQuery({ width: params.width, character_id: params.characterId, v: params.version });
  return `/api/backgrounds/${backgroundId}/preview.png${query}`;
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
