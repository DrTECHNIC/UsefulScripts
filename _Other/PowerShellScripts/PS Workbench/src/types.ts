export type FlagType = "toggle" | "text" | "number" | "select" | "path";
export type PromptMode = "name" | "path";

export type Flag = {
  id: string;
  name: string;
  label: string;
  description: string;
  type: FlagType;
  placeholder?: string;
  defaultValue?: string | boolean;
  options?: string[];
  min?: number;
  max?: number;
  mandatory?: boolean;
  isBoolParam?: boolean;
  isPrimaryPath?: boolean;
  pathKind?: "file" | "directory" | "saveFile";
  parameterSets?: string[];
  mandatoryInSets?: string[];
};

export type ScriptItem = {
  id: string;
  file: string;
  title: string;
  shortTitle: string;
  description: string;
  kind: "rename" | "inspect";
  icon?: string;
  sourcePath: string;
  groupId?: string;
  group?: string;
  hidden?: boolean;
  defaultParameterSet?: string;
  flags: Flag[];
};

export type ThemeColors = {
  background: string;
  surface: string;
  raised: string;
  border: string;
  text: string;
  muted: string;
  accent: string;
  success: string;
  warning: string;
  danger: string;
  terminal: string;
};

export type ParsedScriptResult = {
  ok: boolean;
  error?: string;
  title?: string;
  description?: string;
  defaultParameterSet?: string;
  inferredKind?: "rename" | "inspect";
  flags: Flag[];
};

export type ShellInfo = {
  shellName: string;
  shellExe: string;
  version: string;
  cwd: string;
  projectRoot: string;
  projectName: string;
  encoding: string;
};

export type TerminalEvent =
  | { type: "stdout"; text: string }
  | { type: "stderr"; text: string }
  | { type: "done"; exitCode: number; cwd: string }
  | { type: "info"; info: ShellInfo }
  | { type: "error"; message: string };

export type StoredConfig = {
  schemaVersion?: number;
  scripts?: ScriptItem[];
  colors?: ThemeColors;
  promptMode?: PromptMode;
  collapsedGroups?: Record<string, boolean>;
};

export type PsWorkbenchAPI = {
  minimizeWindow: () => void;
  maximizeWindow: () => void;
  closeWindow: () => void;
  pickTarget: (mode: "file" | "directory") => Promise<string | null>;
  pickSaveOrOpenFile: (title?: string) => Promise<string | null>;
  pickScriptFile: () => Promise<string | null>;
  getPathForFile: (file: File) => string;
  copyText: (text: string) => Promise<boolean>;
  parseScript: (scriptPath: string) => Promise<ParsedScriptResult>;
  getBundledScripts: () => Promise<ScriptItem[]>;
  unblockScripts: (paths: string[]) => Promise<{ ok: boolean; count: number; error?: string }>;
  getShellInfo: () => Promise<ShellInfo>;
  completePath: (token: string, isFirstToken?: boolean) => Promise<string[]>;
  runCommand: (command: string) => Promise<{ ok: boolean; error?: string }>;
  stopCommand: () => Promise<void>;
  onTerminalEvent: (listener: (event: TerminalEvent) => void) => () => void;
  loadConfig: () => Promise<StoredConfig | null>;
  saveConfig: (config: StoredConfig) => Promise<void>;
};

declare global {
  interface Window {
    psWorkbench?: PsWorkbenchAPI;
  }
}
