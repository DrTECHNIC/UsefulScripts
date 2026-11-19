import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type DragEvent,
  type KeyboardEvent as ReactKeyboardEvent,
  type MouseEvent as ReactMouseEvent,
  type ReactNode,
} from "react";
import type { Flag, PromptMode, ScriptItem, ShellInfo, ThemeColors } from "./types";

const CONFIG_SCHEMA_VERSION = 4;

const fallbackWebScripts: ScriptItem[] = [
  {
    id: "bundled-hello",
    file: "hello.ps1",
    title: "Привет, Мир!",
    shortTitle: "Привет, Мир!",
    description:
      'Выводит на экран "Hello, World!" с настройкой регистра, количества повторений и цвета текста.',
    kind: "rename",
    icon: "terminal",
    sourcePath: "",
    groupId: undefined,
    group: "",
    hidden: false,
    defaultParameterSet: "Normal",
    flags: [
      {
        id: "uppercase",
        name: "-UpperCase",
        label: "UpperCase",
        description: "Вывод только в верхнем регистре.",
        type: "toggle",
        defaultValue: false,
        parameterSets: ["Upper"],
      },
      {
        id: "lowercase",
        name: "-LowerCase",
        label: "LowerCase",
        description: "Вывод только в нижнем регистре.",
        type: "toggle",
        defaultValue: false,
        parameterSets: ["Lower"],
      },
      {
        id: "count",
        name: "-Count",
        label: "Count",
        description: "Количество выводимых сообщений.",
        type: "number",
        defaultValue: "1",
        placeholder: "Введите число",
        parameterSets: [],
      },
      {
        id: "color",
        name: "-Color",
        label: "Color",
        description: "Цвет выводимого текста в HEX-формате.",
        type: "text",
        defaultValue: "#FFFFFF",
        placeholder: "Введите значение",
        parameterSets: [],
      },
    ],
  },
];

const defaultColors: ThemeColors = {
  background: "#0b0e13",
  surface: "#10141a",
  raised: "#171c23",
  border: "#242a34",
  text: "#e8edf5",
  muted: "#7f8998",
  accent: "#176bdf",
  success: "#34c587",
  warning: "#f1c65a",
  danger: "#d73542",
  terminal: "#080a0d",
};

const colorLabels: Record<keyof ThemeColors, string> = {
  background: "Основной фон",
  surface: "Панели",
  raised: "Поля и элементы",
  border: "Границы",
  text: "Основной текст",
  muted: "Вторичный текст",
  accent: "Акцент",
  success: "Успех",
  warning: "Предупреждение",
  danger: "Ошибка",
  terminal: "Фон терминала",
};

type TerminalEntry = {
  id: number;
  kind: "command" | "stdout" | "stderr" | "system";
  promptSuffix?: string;
  text: string;
};

type AnsiSegment = {
  text: string;
  color?: string;
};

type SidebarBlock =
  | { kind: "script"; script: ScriptItem }
  | { kind: "group"; groupId: string; name: string; items: ScriptItem[] };

type DropTarget =
  | { kind: "on-script"; targetScriptId: string }
  | { kind: "before-script"; targetScriptId: string; intoGroupId?: string }
  | { kind: "after-script"; targetScriptId: string; intoGroupId?: string }
  | { kind: "on-group"; targetGroupId: string }
  | { kind: "before-group"; targetGroupId: string }
  | { kind: "after-group"; targetGroupId: string }
  | { kind: "end" };

type PointerDragState = {
  dragKind: "script" | "group";
  id: string;
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
  active: boolean;
};

type TabCompletionSession = {
  beforeToken: string;
  afterToken: string;
  matches: string[];
  index: number;
  expectedValue: string;
};

function extractTokenAtCursor(
  input: string,
  cursorPos: number,
): { tokenStart: number; tokenEnd: number; token: string; isFirstToken: boolean } {
  const safeCursor = Math.max(0, Math.min(cursorPos, input.length));
  const before = input.slice(0, safeCursor);

  let quote: '"' | "'" | null = null;
  let inToken = false;
  let tokenStart = safeCursor;
  let completedTokens = 0;

  for (let i = 0; i < before.length; i++) {
    const ch = before[i];
    if (quote) {
      if (ch === quote) {
        quote = null;
      }
      continue;
    }

    if (/\s/.test(ch)) {
      if (inToken) {
        completedTokens += 1;
        inToken = false;
      }
      continue;
    }

    if (!inToken) {
      inToken = true;
      tokenStart = i;
    }

    if (ch === '"' || ch === "'") {
      quote = ch;
    }
  }

  if (!inToken) {
    tokenStart = safeCursor;
  }

  let tokenEnd = safeCursor;
  if (quote && input[safeCursor] === quote) {
    tokenEnd = safeCursor + 1;
  }

  return {
    tokenStart,
    tokenEnd,
    token: before.slice(tokenStart),
    isFirstToken: completedTokens === 0,
  };
}

function isProtectedHello(script: ScriptItem | null | undefined): boolean {
  if (!script) return false;
  return script.id === "bundled-hello";
}

function parseAnsiSegments(input: string): AnsiSegment[] {
  const segments: AnsiSegment[] = [];
  const regex = /\x1B\[([0-9;]*)m|\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])/g;
  let lastIndex = 0;
  let currentColor: string | undefined;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(input)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ text: input.slice(lastIndex, match.index), color: currentColor });
    }
    const sgr = match[1];
    if (sgr !== undefined) {
      if (sgr === "" || sgr === "0" || sgr === "39") {
        currentColor = undefined;
      } else {
        const rgbMatch = sgr.match(/(?:^|;)38;2;(\d+);(\d+);(\d+)(?:;|$)/);
        if (rgbMatch) {
          currentColor = `rgb(${rgbMatch[1]}, ${rgbMatch[2]}, ${rgbMatch[3]})`;
        }
      }
    }
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < input.length) {
    segments.push({ text: input.slice(lastIndex), color: currentColor });
  }
  return segments;
}

// Text, number, and path inputs start empty so scripts run with clean command lines
// and fall back to their native PowerShell default values unless the user enters a value.
function buildInitialValuesForFlags(flags: Flag[]): Record<string, string | boolean> {
  return Object.fromEntries(
    flags.map((flag) => {
      if (flag.type === "toggle") return [flag.id, false];
      if (flag.type === "select") {
        const def =
          typeof flag.defaultValue === "string" && flag.defaultValue
            ? flag.defaultValue
            : flag.options?.[0] ?? "";
        return [flag.id, def];
      }
      return [flag.id, ""];
    }),
  );
}

function escapePsString(val: string): string {
  return val.replace(/"/g, '`"');
}

function needsPsQuoting(scriptPath: string): boolean {
  return /[\s'"`$&#;(){}\[\],|<>@]/.test(scriptPath);
}

function getExclusiveSwitchSet(flag: Flag, defaultSet?: string): string | null {
  if (flag.type !== "toggle") return null;
  const sets = flag.parameterSets ?? [];
  if (sets.length === 1 && sets[0] !== defaultSet) {
    return sets[0];
  }
  return null;
}

function isCompatibleWithSet(paramSets: string[] | undefined, activeSet: string): boolean {
  if (!activeSet || !paramSets || paramSets.length === 0) return true;
  return paramSets.includes(activeSet);
}

function isLegacyDefaultScript(script: ScriptItem): boolean {
  return (
    /^script[1-4]$/i.test(script.id) ||
    /^bundled-(renamebyalphabet|renamebydate|renamebyname|fileinfo|hello)$/i.test(script.id)
  );
}

// Enforces group invariants:
// 1. Migrate legacy string-only group names into stable groupIds.
// 2. Permanently dissolve any group that has fewer than 2 visible scripts (clearing BOTH visible and hidden members).
// 3. Keep members of the same groupId contiguous in the array.
function normalizeGroups(scripts: ScriptItem[]): ScriptItem[] {
  // 1. Assign groupId for legacy entries that only had a non-empty `group` name
  const legacyNameToId = new Map<string, string>();
  let normalized = scripts.map((s) => {
    if (s.groupId) return s;
    const trimmedName = s.group?.trim();
    if (!trimmedName) {
      return { ...s, groupId: undefined, group: "" };
    }
    let gid = legacyNameToId.get(trimmedName);
    if (!gid) {
      gid = `group-legacy-${trimmedName.toLowerCase().replace(/\s+/g, "-")}`;
      legacyNameToId.set(trimmedName, gid);
    }
    return { ...s, groupId: gid, group: trimmedName };
  });

  // 2. Count visible members per groupId
  const visibleCounts = new Map<string, number>();
  for (const s of normalized) {
    if (s.groupId && !s.hidden) {
      visibleCounts.set(s.groupId, (visibleCounts.get(s.groupId) ?? 0) + 1);
    }
  }

  // Permanently dissolve any group with < 2 visible scripts
  normalized = normalized.map((s) => {
    if (!s.groupId) return s;
    if ((visibleCounts.get(s.groupId) ?? 0) < 2) {
      return { ...s, groupId: undefined, group: "" };
    }
    return s;
  });

  // 3. Keep members of each surviving groupId contiguous at first occurrence
  const result: ScriptItem[] = [];
  const emittedGroups = new Set<string>();
  for (const s of normalized) {
    if (!s.groupId) {
      result.push(s);
    } else if (!emittedGroups.has(s.groupId)) {
      emittedGroups.add(s.groupId);
      for (const member of normalized) {
        if (member.groupId === s.groupId) {
          result.push(member);
        }
      }
    }
  }

  return result;
}

function applySidebarDrop(
  scripts: ScriptItem[],
  draggedId: string,
  drop: DropTarget,
): { nextScripts: ScriptItem[]; createdGroupId?: string } {
  const dragged = scripts.find((s) => s.id === draggedId);
  if (!dragged) return { nextScripts: scripts };

  // Remove dragged from current position
  const rest = scripts.filter((s) => s.id !== draggedId);

  if (drop.kind === "on-script") {
    const targetIdx = rest.findIndex((s) => s.id === drop.targetScriptId);
    if (targetIdx === -1) return { nextScripts: scripts };
    const target = rest[targetIdx];

    if (target.groupId) {
      // Join target's existing group right after target
      const updatedDragged: ScriptItem = {
        ...dragged,
        groupId: target.groupId,
        group: target.group ?? "",
      };
      const next = [...rest];
      next.splice(targetIdx + 1, 0, updatedDragged);
      return { nextScripts: normalizeGroups(next) };
    } else {
      // Create a brand-new unnamed group containing [target, dragged]
      const newGroupId = `group-${Date.now()}`;
      const updatedTarget: ScriptItem = { ...target, groupId: newGroupId, group: "" };
      const updatedDragged: ScriptItem = { ...dragged, groupId: newGroupId, group: "" };
      const next = [...rest];
      next[targetIdx] = updatedTarget;
      next.splice(targetIdx + 1, 0, updatedDragged);
      return { nextScripts: normalizeGroups(next), createdGroupId: newGroupId };
    }
  }

  if (drop.kind === "on-group") {
    const groupMembers = rest.filter((s) => s.groupId === drop.targetGroupId);
    if (groupMembers.length === 0) return { nextScripts: scripts };
    const groupName = groupMembers[0].group ?? "";
    let lastIdx = -1;
    rest.forEach((s, i) => {
      if (s.groupId === drop.targetGroupId) lastIdx = i;
    });
    const updatedDragged: ScriptItem = {
      ...dragged,
      groupId: drop.targetGroupId,
      group: groupName,
    };
    const next = [...rest];
    next.splice(lastIdx + 1, 0, updatedDragged);
    return { nextScripts: normalizeGroups(next) };
  }

  if (drop.kind === "before-group") {
    const firstIdx = rest.findIndex((s) => s.groupId === drop.targetGroupId);
    if (firstIdx === -1) return { nextScripts: scripts };
    const updatedDragged: ScriptItem = { ...dragged, groupId: undefined, group: "" };
    const next = [...rest];
    next.splice(firstIdx, 0, updatedDragged);
    return { nextScripts: normalizeGroups(next) };
  }

  if (drop.kind === "after-group") {
    let lastIdx = -1;
    rest.forEach((s, i) => {
      if (s.groupId === drop.targetGroupId) lastIdx = i;
    });
    if (lastIdx === -1) return { nextScripts: scripts };
    const updatedDragged: ScriptItem = { ...dragged, groupId: undefined, group: "" };
    const next = [...rest];
    next.splice(lastIdx + 1, 0, updatedDragged);
    return { nextScripts: normalizeGroups(next) };
  }

  if (drop.kind === "before-script" || drop.kind === "after-script") {
    const targetIdx = rest.findIndex((s) => s.id === drop.targetScriptId);
    if (targetIdx === -1) return { nextScripts: scripts };

    let nextGroupId: string | undefined = undefined;
    let nextGroupName = "";
    if (drop.intoGroupId) {
      const sample = rest.find((s) => s.groupId === drop.intoGroupId);
      if (sample) {
        nextGroupId = drop.intoGroupId;
        nextGroupName = sample.group ?? "";
      }
    }

    const updatedDragged: ScriptItem = {
      ...dragged,
      groupId: nextGroupId,
      group: nextGroupName,
    };
    const next = [...rest];
    const insertAt = drop.kind === "before-script" ? targetIdx : targetIdx + 1;
    next.splice(insertAt, 0, updatedDragged);
    return { nextScripts: normalizeGroups(next) };
  }

  // drop.kind === "end"
  const updatedDragged: ScriptItem = { ...dragged, groupId: undefined, group: "" };
  return { nextScripts: normalizeGroups([...rest, updatedDragged]) };
}

function applySidebarGroupDrop(
  scripts: ScriptItem[],
  draggedGroupId: string,
  drop: DropTarget,
): ScriptItem[] {
  const groupMembers = scripts.filter((s) => s.groupId === draggedGroupId);
  if (groupMembers.length === 0) return scripts;

  const rest = scripts.filter((s) => s.groupId !== draggedGroupId);

  if (drop.kind === "before-script") {
    const idx = rest.findIndex((s) => s.id === drop.targetScriptId);
    if (idx === -1) return scripts;
    const next = [...rest];
    next.splice(idx, 0, ...groupMembers);
    return normalizeGroups(next);
  }

  if (drop.kind === "after-script") {
    const idx = rest.findIndex((s) => s.id === drop.targetScriptId);
    if (idx === -1) return scripts;
    const next = [...rest];
    next.splice(idx + 1, 0, ...groupMembers);
    return normalizeGroups(next);
  }

  if (drop.kind === "before-group") {
    const idx = rest.findIndex((s) => s.groupId === drop.targetGroupId);
    if (idx === -1) return scripts;
    const next = [...rest];
    next.splice(idx, 0, ...groupMembers);
    return normalizeGroups(next);
  }

  if (drop.kind === "after-group") {
    let lastIdx = -1;
    rest.forEach((s, i) => {
      if (s.groupId === drop.targetGroupId) lastIdx = i;
    });
    if (lastIdx === -1) return scripts;
    const next = [...rest];
    next.splice(lastIdx + 1, 0, ...groupMembers);
    return normalizeGroups(next);
  }

  if (drop.kind === "end") {
    return normalizeGroups([...rest, ...groupMembers]);
  }

  return scripts;
}

const SCRIPT_ICON_OPTIONS: Array<{ id: string; label: string }> = [
  { id: "terminal", label: "Терминал" },
  { id: "file", label: "Файл" },
  { id: "folder", label: "Папка" },
  { id: "hash", label: "Нумерация" },
  { id: "search", label: "Поиск и анализ" },
  { id: "calendar", label: "Дата и время" },
  { id: "code", label: "Код" },
  { id: "wrench", label: "Инструмент" },
  { id: "sliders", label: "Параметры" },
  { id: "zap", label: "Быстрое действие" },
  { id: "database", label: "Данные" },
  { id: "image", label: "Изображения" },
  { id: "globe", label: "Сеть" },
  { id: "shield", label: "Безопасность" },
];

function stripDefaultHints(text: string): string {
  if (!text) return "";
  let s = String(text);
  s = s.replace(
    /[,;]\s*(?:по\s+умолчанию|по\s+умолч\.?|default)(?=$|[\s.,;:!?)—–-])[^)]*(?=\))/gi,
    "",
  );
  s = s.replace(
    /(?<=\()\s*(?:по\s+умолчанию|по\s+умолч\.?|default)(?=$|[\s.,;:!?)—–-])[^,;)]*[,;]\s*/gi,
    "",
  );
  s = s.replace(
    /\s*\(\s*(?:по\s+умолчанию|по\s+умолч\.?|default)(?=$|[\s.,;:!?)—–-])[^)]*\)/gi,
    "",
  );
  s = s.replace(
    /(?:^|[.!?]\s+|\s*[,;:—–-]\s*)(?:по\s+умолчанию|по\s+умолч\.?|default)(?=$|[\s.,;:!?)—–-])[^.!?\n]*(?:[.!?]|$)/gi,
    (match) => {
      if (match.startsWith(".")) return ".";
      if (match.startsWith("!")) return "!";
      if (match.startsWith("?")) return "?";
      return "";
    },
  );
  s = s.replace(/(?:по\s+умолчанию|по\s+умолч\.?)(?=$|[\s.,;:!?)—–-])/gi, "");
  s = s.replace(/\(\s*\)/g, "");
  s = s.replace(/\s+([.,;:!?])/g, "$1");
  s = s.replace(/\.{2,}/g, ".");
  s = s.replace(/\s{2,}/g, " ");
  return s.trim();
}

function getScriptIconName(script: ScriptItem, idx = 0): string {
  if (script.icon && SCRIPT_ICON_OPTIONS.some((opt) => opt.id === script.icon)) {
    return script.icon;
  }
  if (/^hello\.ps1$/i.test(script.file)) return "terminal";
  if (script.kind === "inspect") return "file";
  if (/date/i.test(script.file)) return "calendar";
  if (/name|num/i.test(script.file)) return "hash";
  return idx % 3 === 0 ? "search" : idx % 3 === 1 ? "calendar" : "hash";
}

function Icon({ name, size = 18 }: { name: string; size?: number }) {
  const paths: Record<string, ReactNode> = {
    terminal: (
      <>
        <path d="m4 6 4 4-4 4" />
        <path d="M10 15h6" />
      </>
    ),
    folder: <path d="M3 6.5h6l1.5 2H21v9.5H3z" />,
    file: (
      <>
        <path d="M6 2.5h8l4 4V21H6z" />
        <path d="M14 2.5v4h4" />
      </>
    ),
    search: (
      <>
        <circle cx="10.5" cy="10.5" r="6.5" />
        <path d="m15.5 15.5 4 4" />
      </>
    ),
    calendar: (
      <>
        <rect x="3" y="5" width="18" height="16" rx="2" />
        <path d="M7 2v6M17 2v6M3 10h18" />
      </>
    ),
    hash: <path d="M9 3 7 21M17 3l-2 18M4 9h16M3 15h16" />,
    copy: (
      <>
        <rect x="8" y="8" width="11" height="12" rx="2" />
        <path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h3" />
      </>
    ),
    play: <path d="m8 5 10 7-10 7z" fill="currentColor" stroke="none" />,
    stop: <rect x="6" y="6" width="12" height="12" rx="1.5" fill="currentColor" stroke="none" />,
    chevron: <path d="m9 18 6-6-6-6" />,
    check: <path d="m5 12 4 4L19 6" />,
    clear: <path d="m7 7 10 10M17 7 7 17" />,
    edit: (
      <>
        <path d="M12 20h9" />
        <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
      </>
    ),
    trash: (
      <>
        <path d="M3 6h18" />
        <path d="M8 6V4h8v2" />
        <path d="M19 6l-1 14H6L5 6" />
      </>
    ),
    refresh: (
      <>
        <path d="M21 12a9 9 0 1 1-2.64-6.36" />
        <path d="M21 3v6h-6" />
      </>
    ),
    unlock: (
      <>
        <rect x="4" y="11" width="16" height="10" rx="2" />
        <path d="M8 11V7a4 4 0 0 1 7.46-2" />
      </>
    ),
    eye: (
      <>
        <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6Z" />
        <circle cx="12" cy="12" r="2.6" />
      </>
    ),
    eyeOff: (
      <>
        <path d="M9.9 4.2A10.9 10.9 0 0 1 12 4c6.5 0 10 8 10 8a17.5 17.5 0 0 1-3.2 4.3" />
        <path d="M6.6 6.6C4.1 8.3 2 12 2 12s3.5 8 10 8a9.8 9.8 0 0 0 4.5-1.1" />
        <path d="m2 2 20 20" />
      </>
    ),
    settings: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M19 12a7 7 0 0 0-.1-1l2-1.6-2-3.4-2.5 1A8 8 0 0 0 14 5.6L13.6 3h-4L9 5.6A8 8 0 0 0 6.7 7L4.2 6 2.3 9.4 4.4 11a7 7 0 0 0 0 2l-2 1.6L4.2 18l2.5-1A8 8 0 0 0 9 18.4l.5 2.6h4l.5-2.6a8 8 0 0 0 2.3-1.4l2.5 1 1.9-3.4-2-1.6a7 7 0 0 0 .2-1Z" />
      </>
    ),
    code: (
      <>
        <path d="m8 7-5 5 5 5" />
        <path d="m16 7 5 5-5 5" />
        <path d="m14 4-4 16" />
      </>
    ),
    wrench: (
      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76Z" />
    ),
    sliders: (
      <>
        <path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3" />
        <path d="M2 14h4M10 8h4M18 16h4" />
      </>
    ),
    zap: <path d="M13 2 3 14h9l-1 8 10-12h-9l1-8Z" />,
    database: (
      <>
        <ellipse cx="12" cy="5" rx="8" ry="3" />
        <path d="M4 5v14c0 1.66 3.58 3 8 3s8-1.34 8-3V5" />
        <path d="M4 12c0 1.66 3.58 3 8 3s8-1.34 8-3" />
      </>
    ),
    image: (
      <>
        <rect x="3" y="4" width="18" height="16" rx="2" />
        <circle cx="8.5" cy="9.5" r="1.5" />
        <path d="m21 15-5-5-8 8" />
      </>
    ),
    globe: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M3 12h18" />
        <path d="M12 3a13 13 0 0 1 0 18 13 13 0 0 1 0-18Z" />
      </>
    ),
    shield: <path d="M12 3 4 6.5v5.5c0 4.5 3.4 8.2 8 9.5 4.6-1.3 8-5 8-9.5V6.5L12 3Z" />,
    minimize: <path d="M6 12h12" />,
    maximize: <rect x="6" y="6" width="12" height="12" />,
  };

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name]}
    </svg>
  );
}

export default function App() {
  const api = window.psWorkbench;
  const isElectron = Boolean(api);

  const [appScripts, setAppScripts] = useState<ScriptItem[]>(fallbackWebScripts);
  // Start with NO script selected so the app launches with a clean terminal
  const [activeId, setActiveId] = useState<string>("");
  const [values, setValues] = useState<Record<string, Record<string, string | boolean>>>(() =>
    Object.fromEntries(
      fallbackWebScripts.map((s) => [s.id, buildInitialValuesForFlags(s.flags)]),
    ),
  );
  const [colors, setColors] = useState<ThemeColors>(defaultColors);
  const [promptMode, setPromptMode] = useState<PromptMode>("name");
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({});
  const [configLoaded, setConfigLoaded] = useState(false);

  // Terminal state
  const [shellInfo, setShellInfo] = useState<ShellInfo>({
    shellName: "Windows PowerShell",
    shellExe: "powershell.exe",
    version: "5.1",
    cwd: "C:\\PS-Workbench",
    projectRoot: "C:\\PS-Workbench",
    projectName: "PS Workbench",
    encoding: "UTF-8",
  });
  const [showBanner, setShowBanner] = useState(true);
  const [entries, setEntries] = useState<TerminalEntry[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [manualInput, setManualInput] = useState("");
  const [commandHistory, setCommandHistory] = useState<string[]>([]);
  const [copied, setCopied] = useState(false);

  // File drag & drop state
  const [isDraggingScriptFile, setIsDraggingScriptFile] = useState(false);
  const [draggingFlagId, setDraggingFlagId] = useState<string | null>(null);

  // Sidebar LMB drag-and-drop state
  const [dragState, setDragState] = useState<PointerDragState | null>(null);
  const [dropTarget, setDropTarget] = useState<DropTarget | null>(null);
  const [renamingGroupId, setRenamingGroupId] = useState<string | null>(null);
  const [renamingGroupValue, setRenamingGroupValue] = useState("");

  // Settings modal state
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsSection, setSettingsSection] = useState<"scripts" | "terminal" | "colors">(
    "scripts",
  );
  const [editingScriptId, setEditingScriptId] = useState<string | null>(null);
  const [formTitle, setFormTitle] = useState("");
  const [formPath, setFormPath] = useState("");
  const [formIcon, setFormIcon] = useState<string>("file");
  const [formGroupId, setFormGroupId] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formHidden, setFormHidden] = useState(false);
  const [formError, setFormError] = useState("");
  const [isParsing, setIsParsing] = useState(false);
  const [unblockNotice, setUnblockNotice] = useState("");

  const nextEntryId = useRef(1);
  const terminalScrollRef = useRef<HTMLDivElement | null>(null);
  const manualInputRef = useRef<HTMLInputElement | null>(null);
  const manualFormRef = useRef<HTMLFormElement | null>(null);
  const historyIndexRef = useRef<number>(-1);
  const historyDraftRef = useRef<string>("");
  const tabSessionRef = useRef<TabCompletionSession | null>(null);
  const scriptListRef = useRef<HTMLElement | null>(null);
  const suppressNextClickRef = useRef(false);
  const dragStateRef = useRef<PointerDragState | null>(null);
  const dropTargetRef = useRef<DropTarget | null>(null);
  const appScriptsRef = useRef<ScriptItem[]>(appScripts);

  dragStateRef.current = dragState;
  dropTargetRef.current = dropTarget;
  appScriptsRef.current = appScripts;

  const visibleScripts = useMemo(
    () => appScripts.filter((script) => !script.hidden),
    [appScripts],
  );

  // Existing valid groups (2+ visible scripts) for dropdown in Settings
  const existingGroups = useMemo(() => {
    const map = new Map<string, { groupId: string; name: string; count: number }>();
    for (const s of visibleScripts) {
      if (!s.groupId) continue;
      const prev = map.get(s.groupId);
      if (prev) {
        prev.count += 1;
      } else {
        map.set(s.groupId, { groupId: s.groupId, name: s.group ?? "", count: 1 });
      }
    }
    return Array.from(map.values()).filter((g) => g.count >= 2);
  }, [visibleScripts]);

  // Ordered sidebar blocks preserving script & group ordering
  const sidebarBlocks = useMemo<SidebarBlock[]>(() => {
    const blocks: SidebarBlock[] = [];
    const seenGroups = new Set<string>();

    for (const script of visibleScripts) {
      if (!script.groupId) {
        blocks.push({ kind: "script", script });
      } else if (!seenGroups.has(script.groupId)) {
        seenGroups.add(script.groupId);
        const members = visibleScripts.filter((s) => s.groupId === script.groupId);
        if (members.length >= 2) {
          blocks.push({
            kind: "group",
            groupId: script.groupId,
            name: members[0].group ?? "",
            items: members,
          });
        } else {
          for (const m of members) {
            blocks.push({ kind: "script", script: m });
          }
        }
      }
    }
    return blocks;
  }, [visibleScripts]);

  const active = useMemo(() => {
    if (!activeId) return null;
    return visibleScripts.find((s) => s.id === activeId) ?? null;
  }, [visibleScripts, activeId]);

  // If the currently selected script gets hidden or deleted, return to clean terminal
  useEffect(() => {
    if (activeId && !visibleScripts.some((s) => s.id === activeId)) {
      setActiveId("");
    }
  }, [visibleScripts, activeId]);

  // Suffix after "PS " so we never duplicate "PS", reflecting live cwd after cd
  const promptSuffix = useMemo(() => {
    const currentCwd = shellInfo.cwd || shellInfo.projectRoot;
    if (promptMode === "path") {
      return currentCwd;
    }
    const displayName =
      (shellInfo.projectName || "PS Workbench").trim().replace(/^PS\s+/i, "") || "Workbench";
    const root = (shellInfo.projectRoot || "").replace(/[\\/]+$/, "");
    const cleanCwd = (currentCwd || "").replace(/[\\/]+$/, "");

    if (root && cleanCwd.toLowerCase() === root.toLowerCase()) {
      return displayName;
    }
    if (root && cleanCwd.toLowerCase().startsWith(`${root.toLowerCase()}\\`)) {
      return `${displayName}${cleanCwd.slice(root.length)}`;
    }
    return cleanCwd || displayName;
  }, [promptMode, shellInfo.projectRoot, shellInfo.projectName, shellInfo.cwd]);

  const activeParameterSet = useMemo(() => {
    if (!active) return "";
    const activeVals = values[active.id] ?? {};
    for (const flag of active.flags) {
      const exclusiveSet = getExclusiveSwitchSet(flag, active.defaultParameterSet);
      if (exclusiveSet && activeVals[flag.id]) {
        return exclusiveSet;
      }
    }
    return active.defaultParameterSet || "";
  }, [active, values]);

  // Load persisted config OR bundled hello.ps1 + shell info on mount.
  // Always keep activeId = "" on startup (clean terminal without pre-selected script).
  useEffect(() => {
    let cancelled = false;
    async function init() {
      if (api) {
        try {
          const info = await api.getShellInfo();
          if (!cancelled && info) setShellInfo(info);
        } catch {
          // ignore
        }

        try {
          const saved = await api.loadConfig();
          const bundled = await api.getBundledScripts();

          if (!cancelled) {
            if (saved?.colors) {
              setColors({ ...defaultColors, ...saved.colors });
            }
            if (saved?.promptMode === "name" || saved?.promptMode === "path") {
              setPromptMode(saved.promptMode);
            }
            if (saved?.collapsedGroups && typeof saved.collapsedGroups === "object") {
              setCollapsedGroups(saved.collapsedGroups);
            }


            const needsMigration = !saved || (saved.schemaVersion ?? 1) < CONFIG_SCHEMA_VERSION;
            let resolvedScripts: ScriptItem[] = [];

            if (saved && Array.isArray(saved.scripts) && saved.scripts.length > 0) {
              if (needsMigration) {
                const userCustom = saved.scripts.filter((s) => !isLegacyDefaultScript(s));
                const refreshedCustom: ScriptItem[] = [];
                for (const item of userCustom) {
                  if (item.sourcePath) {
                    const parsed = await api.parseScript(item.sourcePath);
                    if (parsed.ok) {
                      refreshedCustom.push({
                        ...item,
                        defaultParameterSet: parsed.defaultParameterSet,
                        flags: parsed.flags,
                      });
                      continue;
                    }
                  }
                  refreshedCustom.push(item);
                }
                // Preserve hello's hidden/group metadata if it existed
                const prevHello = saved.scripts.find((s) => s.id === "bundled-hello");
                const mergedBundled = bundled.map((b) =>
                  b.id === "bundled-hello" && prevHello
                    ? {
                        ...b,
                        hidden: Boolean(prevHello.hidden),
                        groupId: prevHello.groupId,
                        group: prevHello.group ?? "",
                      }
                    : b,
                );
                resolvedScripts = normalizeGroups([...mergedBundled, ...refreshedCustom]);
              } else {
                // Ensure bundled-hello always exists and has fresh parsed flags
                const hasHello = saved.scripts.some((s) => s.id === "bundled-hello");
                const helloBundled = bundled.find((b) => b.id === "bundled-hello");
                let merged = saved.scripts.map((s) =>
                  s.id === "bundled-hello" && helloBundled
                    ? {
                        ...helloBundled,
                        hidden: Boolean(s.hidden),
                        groupId: s.groupId,
                        group: s.group ?? "",
                      }
                    : s,
                );
                if (!hasHello && helloBundled) {
                  merged = [helloBundled, ...merged];
                }
                resolvedScripts = normalizeGroups(merged);
              }
            } else {
              resolvedScripts = normalizeGroups(
                bundled.length > 0 ? bundled : fallbackWebScripts,
              );
            }

            if (resolvedScripts.length > 0) {
              setAppScripts(resolvedScripts);
              setValues(
                Object.fromEntries(
                  resolvedScripts.map((s) => [s.id, buildInitialValuesForFlags(s.flags)]),
                ),
              );
            }
          }
        } catch {
          // ignore
        }
      }
      if (!cancelled) setConfigLoaded(true);
    }
    void init();
    return () => {
      cancelled = true;
    };
  }, [api]);

  // Persist config (intentionally does NOT persist activeId so startup is always clean)
  useEffect(() => {
    if (!configLoaded || !api) return;
    void api.saveConfig({
      schemaVersion: CONFIG_SCHEMA_VERSION,
      scripts: appScripts,
      colors,
      promptMode,
      collapsedGroups,
    });
  }, [api, appScripts, colors, promptMode, collapsedGroups, configLoaded]);

  // Subscribe to embedded PowerShell events
  useEffect(() => {
    if (!api) return;
    const unsubscribe = api.onTerminalEvent((event) => {
      if (event.type === "info") {
        setShellInfo(event.info);
        return;
      }
      if (event.type === "stdout") {
        setEntries((prev) => [
          ...prev,
          { id: nextEntryId.current++, kind: "stdout", text: event.text },
        ]);
        return;
      }
      if (event.type === "stderr") {
        setEntries((prev) => [
          ...prev,
          { id: nextEntryId.current++, kind: "stderr", text: event.text },
        ]);
        return;
      }
      if (event.type === "error") {
        setEntries((prev) => [
          ...prev,
          { id: nextEntryId.current++, kind: "stderr", text: event.message },
        ]);
        setIsRunning(false);
        return;
      }
      if (event.type === "done") {
        setShellInfo((prev) => ({ ...prev, cwd: event.cwd || prev.cwd }));
        setIsRunning(false);
      }
    });
    return unsubscribe;
  }, [api]);

  // Auto-scroll terminal to bottom
  useEffect(() => {
    const el = terminalScrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [entries, isRunning]);

  // Auto-refresh flags when switching to a script with a real file path
  useEffect(() => {
    if (!api || !active || !active.sourcePath) return;
    let cancelled = false;
    void api.parseScript(active.sourcePath).then((res) => {
      if (cancelled || !res.ok) return;
      setAppScripts((prev) =>
        prev.map((item) => {
          if (item.id !== active.id) return item;
          const nextItem: ScriptItem = {
            ...item,
            kind: res.inferredKind ?? item.kind,
            defaultParameterSet: res.defaultParameterSet,
            flags: res.flags,
          };
          if (JSON.stringify(item) === JSON.stringify(nextItem)) return item;
          return nextItem;
        }),
      );
      setValues((prev) => {
        const existing = prev[active.id] ?? {};
        const nextDefaults = buildInitialValuesForFlags(res.flags);
        const merged: Record<string, string | boolean> = {};
        for (const f of res.flags) {
          merged[f.id] = existing[f.id] !== undefined ? existing[f.id] : nextDefaults[f.id];
        }
        return { ...prev, [active.id]: merged };
      });
    });
    return () => {
      cancelled = true;
    };
  }, [api, active?.id, active?.sourcePath]);

  // Real-time command generation for selected script (empty when no script is selected)
  const command = useMemo(() => {
    if (!active) return "";

    let scriptRef: string;
    if (active.sourcePath) {
      scriptRef = needsPsQuoting(active.sourcePath)
        ? `& "${escapePsString(active.sourcePath)}"`
        : active.sourcePath;
    } else {
      scriptRef = `.\\scripts\\${active.file}`;
    }

    const parts: string[] = [scriptRef];
    const activeVals = values[active.id] ?? {};

    active.flags.forEach((flag) => {
      if (!isCompatibleWithSet(flag.parameterSets, activeParameterSet)) return;
      const value = activeVals[flag.id];

      if (flag.type === "toggle") {
        if (value) {
          parts.push(flag.isBoolParam ? `${flag.name} $true` : flag.name);
        }
      } else if (typeof value === "string" && value.trim() !== "") {
        const trimmed = value.trim();
        const formatted =
          flag.type === "number" ? trimmed : `"${escapePsString(trimmed)}"`;
        parts.push(`${flag.name} ${formatted}`);
      }
    });

    return parts.join(" ");
  }, [active, values, activeParameterSet]);

  // Automatically route keyboard typing into manual command input when focus is not in an editable field
  useEffect(() => {
    function handleGlobalKeyDown(event: KeyboardEvent) {
      if (settingsOpen || renamingGroupId || isRunning) return;
      if (event.ctrlKey || event.metaKey || event.altKey || event.isComposing) return;

      const activeEl = document.activeElement as HTMLElement | null;
      const tag = activeEl?.tagName?.toLowerCase();
      const isEditable =
        tag === "input" ||
        tag === "textarea" ||
        tag === "select" ||
        Boolean(activeEl?.isContentEditable);
      if (isEditable) return;

      const inputEl = manualInputRef.current;
      if (!inputEl) return;

      if (event.key.length === 1) {
        event.preventDefault();
        historyIndexRef.current = -1;
        tabSessionRef.current = null;
        inputEl.focus();
        setManualInput((prev) => prev + event.key);
      } else if (event.key === "Backspace") {
        event.preventDefault();
        historyIndexRef.current = -1;
        tabSessionRef.current = null;
        inputEl.focus();
        setManualInput((prev) => prev.slice(0, -1));
      } else if (event.key === "Enter" && manualInput.trim().length > 0 && tag !== "button") {
        event.preventDefault();
        manualFormRef.current?.requestSubmit();
      }
    }

    window.addEventListener("keydown", handleGlobalKeyDown);
    return () => window.removeEventListener("keydown", handleGlobalKeyDown);
  }, [settingsOpen, renamingGroupId, isRunning, manualInput]);

  // Sidebar LMB Drag & Drop hit-testing and mouse listeners (for both scripts and groups)
  const computeDropTarget = useCallback(
    (
      clientX: number,
      clientY: number,
      dragKind: "script" | "group",
      draggedId: string,
    ): DropTarget | null => {
      const container = scriptListRef.current;
      if (!container) return null;
      const cRect = container.getBoundingClientRect();
      if (
        clientX < cRect.left - 36 ||
        clientX > cRect.right + 36 ||
        clientY < cRect.top - 24 ||
        clientY > cRect.bottom + 36
      ) {
        return null;
      }

      // Group dragging: reorder among top-level blocks (scripts and other groups)
      if (dragKind === "group") {
        const topBlocks = Array.from(
          container.querySelectorAll<HTMLElement>("[data-drag-top-block]"),
        );
        for (const bEl of topBlocks) {
          const rect = bEl.getBoundingClientRect();
          const kind = bEl.dataset.dragTopKind;
          const id = bEl.dataset.dragTopId!;

          if (clientY >= rect.top && clientY <= rect.bottom) {
            if (kind === "group" && id === draggedId) return null;
            const isUpperHalf = clientY < rect.top + rect.height / 2;
            if (kind === "group") {
              return isUpperHalf
                ? { kind: "before-group", targetGroupId: id }
                : { kind: "after-group", targetGroupId: id };
            }
            return isUpperHalf
              ? { kind: "before-script", targetScriptId: id }
              : { kind: "after-script", targetScriptId: id };
          }

          if (clientY < rect.top) {
            if (kind === "group" && id === draggedId) return null;
            return kind === "group"
              ? { kind: "before-group", targetGroupId: id }
              : { kind: "before-script", targetScriptId: id };
          }
        }
        return { kind: "end" };
      }

      const scriptsById = new Map(appScriptsRef.current.map((s) => [s.id, s]));

      // 1. Check group headers
      const groupHeaders = Array.from(
        container.querySelectorAll<HTMLElement>("[data-drag-group-header]"),
      );
      for (const headerEl of groupHeaders) {
        const rect = headerEl.getBoundingClientRect();
        if (clientY >= rect.top && clientY <= rect.bottom) {
          const targetGroupId = headerEl.dataset.dragGroupHeader!;
          const isCollapsed = headerEl.dataset.groupCollapsed === "true";
          const ratio = (clientY - rect.top) / Math.max(rect.height, 1);
          if (ratio < 0.25) {
            return { kind: "before-group", targetGroupId };
          }
          if (isCollapsed && ratio > 0.78) {
            return { kind: "after-group", targetGroupId };
          }
          return { kind: "on-group", targetGroupId };
        }
      }

      // 2. Check script cards
      const scriptEls = Array.from(
        container.querySelectorAll<HTMLElement>("[data-drag-script-id]"),
      );
      for (const el of scriptEls) {
        const rect = el.getBoundingClientRect();
        if (clientY >= rect.top && clientY <= rect.bottom) {
          const targetScriptId = el.dataset.dragScriptId!;
          if (targetScriptId === draggedId) return null;

          const targetScript = scriptsById.get(targetScriptId);
          const intoGroupId = targetScript?.groupId;
          const ratio = (clientY - rect.top) / Math.max(rect.height, 1);

          if (ratio < 0.26) {
            return { kind: "before-script", targetScriptId, intoGroupId };
          }
          if (ratio > 0.74) {
            return { kind: "after-script", targetScriptId, intoGroupId };
          }
          return { kind: "on-script", targetScriptId };
        }
      }

      // 3. Pointer is in a gap between cards / groups, or above/below the list
      const groupEls = Array.from(
        container.querySelectorAll<HTMLElement>("[data-drag-group-box]"),
      );
      for (const gEl of groupEls) {
        const gRect = gEl.getBoundingClientRect();
        if (clientY >= gRect.top && clientY <= gRect.bottom) {
          const groupId = gEl.dataset.dragGroupBox!;
          const innerCards = Array.from(
            gEl.querySelectorAll<HTMLElement>("[data-drag-script-id]"),
          );
          for (let i = 0; i < innerCards.length; i++) {
            const r = innerCards[i].getBoundingClientRect();
            if (clientY < r.top) {
              const tid = innerCards[i].dataset.dragScriptId!;
              if (tid === draggedId) return null;
              return { kind: "before-script", targetScriptId: tid, intoGroupId: groupId };
            }
          }
          return { kind: "after-group", targetGroupId: groupId };
        }
      }

      // Otherwise check top-level blocks
      const topBlocks = Array.from(
        container.querySelectorAll<HTMLElement>("[data-drag-top-block]"),
      );
      for (const bEl of topBlocks) {
        const bRect = bEl.getBoundingClientRect();
        if (clientY < bRect.top) {
          const kind = bEl.dataset.dragTopKind;
          const id = bEl.dataset.dragTopId!;
          if (kind === "group") {
            return { kind: "before-group", targetGroupId: id };
          }
          if (id === draggedId) return null;
          return { kind: "before-script", targetScriptId: id };
        }
      }

      return { kind: "end" };
    },
    [],
  );

  useEffect(() => {
    if (!dragState) return;

    function handleMouseMove(event: MouseEvent) {
      const curr = dragStateRef.current;
      if (!curr) return;
      const dx = event.clientX - curr.startX;
      const dy = event.clientY - curr.startY;
      const becameActive = curr.active || Math.hypot(dx, dy) >= 5;

      const updated: PointerDragState = {
        ...curr,
        currentX: event.clientX,
        currentY: event.clientY,
        active: becameActive,
      };
      setDragState(updated);

      if (becameActive) {
        const nextDrop = computeDropTarget(
          event.clientX,
          event.clientY,
          curr.dragKind,
          curr.id,
        );
        setDropTarget(nextDrop);
      }
    }

    function handleMouseUp() {
      const curr = dragStateRef.current;
      const target = dropTargetRef.current;

      if (curr?.active) {
        suppressNextClickRef.current = true;
        window.setTimeout(() => {
          suppressNextClickRef.current = false;
        }, 0);

        if (target) {
          if (curr.dragKind === "group") {
            setAppScripts(applySidebarGroupDrop(appScriptsRef.current, curr.id, target));
          } else {
            const { nextScripts, createdGroupId } = applySidebarDrop(
              appScriptsRef.current,
              curr.id,
              target,
            );
            setAppScripts(nextScripts);
            if (createdGroupId) {
              setCollapsedGroups((prev) => ({ ...prev, [createdGroupId]: false }));
            }
          }
        }
      }

      setDragState(null);
      setDropTarget(null);
    }

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [Boolean(dragState), computeDropTarget]);

  function handleScriptMouseDown(event: ReactMouseEvent, scriptId: string) {
    if (event.button !== 0) return;
    setDragState({
      dragKind: "script",
      id: scriptId,
      startX: event.clientX,
      startY: event.clientY,
      currentX: event.clientX,
      currentY: event.clientY,
      active: false,
    });
  }

  function handleGroupMouseDown(event: ReactMouseEvent, groupId: string) {
    if (event.button !== 0) return;
    if (renamingGroupId === groupId) return;
    const target = event.target as HTMLElement | null;
    if (target?.closest("input") || target?.closest(".group-rename-btn")) return;
    setDragState({
      dragKind: "group",
      id: groupId,
      startX: event.clientX,
      startY: event.clientY,
      currentX: event.clientX,
      currentY: event.clientY,
      active: false,
    });
  }

  function updateValue(flag: Flag, value: string | boolean) {
    if (!active) return;
    setValues((current) => {
      const nextForScript = { ...(current[active.id] ?? {}), [flag.id]: value };
      const exclusiveSet = getExclusiveSwitchSet(flag, active.defaultParameterSet);
      if (exclusiveSet && value === true) {
        for (const other of active.flags) {
          if (other.id === flag.id) continue;
          const otherSet = getExclusiveSwitchSet(other, active.defaultParameterSet);
          if (otherSet && otherSet !== exclusiveSet) {
            nextForScript[other.id] = false;
          }
        }
      }
      return { ...current, [active.id]: nextForScript };
    });
  }

  async function copyCommand() {
    if (!command) return;
    let ok = false;
    if (api) {
      ok = await api.copyText(command);
    }
    if (!ok && navigator.clipboard) {
      try {
        await navigator.clipboard.writeText(command);
        ok = true;
      } catch {
        // ignore
      }
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }

  function clearTerminal() {
    setEntries([]);
    setShowBanner(false);
  }

  async function executeInTerminal(cmdText: string) {
    const trimmed = cmdText.trim();
    if (!trimmed) return;

    if (/^(cls|clear|clear-host)$/i.test(trimmed)) {
      clearTerminal();
      return;
    }

    setEntries((prev) => [
      ...prev,
      { id: nextEntryId.current++, kind: "command", promptSuffix, text: trimmed },
    ]);

    if (!api) {
      setEntries((prev) => [
        ...prev,
        {
          id: nextEntryId.current++,
          kind: "system",
          text: "Запущено в браузерном предпросмотре. Для реального PowerShell запустите приложение через Electron (npm run dev).",
        },
      ]);
      return;
    }

    setIsRunning(true);
    const res = await api.runCommand(trimmed);
    if (!res.ok) {
      setEntries((prev) => [
        ...prev,
        {
          id: nextEntryId.current++,
          kind: "stderr",
          text: res.error || "Не удалось выполнить команду",
        },
      ]);
      setIsRunning(false);
    }
  }

  function setManualInputAndCaret(nextValue: string, caretPos?: number) {
    setManualInput(nextValue);
    const pos = caretPos ?? nextValue.length;
    window.requestAnimationFrame(() => {
      const el = manualInputRef.current;
      if (el) {
        el.focus();
        el.setSelectionRange(pos, pos);
      }
    });
  }

  async function handleManualKeyDown(event: ReactKeyboardEvent<HTMLInputElement>) {
    if (isRunning) return;

    if (event.key === "ArrowUp") {
      event.preventDefault();
      tabSessionRef.current = null;
      if (commandHistory.length === 0) return;

      if (historyIndexRef.current === -1) {
        historyDraftRef.current = manualInput;
        historyIndexRef.current = commandHistory.length - 1;
      } else if (historyIndexRef.current > 0) {
        historyIndexRef.current -= 1;
      }

      const recalled = commandHistory[historyIndexRef.current];
      if (recalled !== undefined) {
        setManualInputAndCaret(recalled);
      }
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      tabSessionRef.current = null;
      if (historyIndexRef.current === -1) return;

      if (historyIndexRef.current < commandHistory.length - 1) {
        historyIndexRef.current += 1;
        const recalled = commandHistory[historyIndexRef.current];
        if (recalled !== undefined) {
          setManualInputAndCaret(recalled);
        }
      } else {
        historyIndexRef.current = -1;
        setManualInputAndCaret(historyDraftRef.current);
      }
      return;
    }

    if (event.key === "Tab") {
      event.preventDefault();
      historyIndexRef.current = -1;
      if (!api) return;

      const existing = tabSessionRef.current;
      if (existing && existing.expectedValue === manualInput && existing.matches.length > 0) {
        const step = event.shiftKey ? -1 : 1;
        const nextIdx =
          (existing.index + step + existing.matches.length) % existing.matches.length;
        const nextMatch = existing.matches[nextIdx];
        const nextValue = existing.beforeToken + nextMatch + existing.afterToken;
        existing.index = nextIdx;
        existing.expectedValue = nextValue;
        setManualInputAndCaret(nextValue, existing.beforeToken.length + nextMatch.length);
        return;
      }

      const inputEl = manualInputRef.current;
      const cursorPos = inputEl?.selectionStart ?? manualInput.length;
      const { tokenStart, tokenEnd, token, isFirstToken } = extractTokenAtCursor(
        manualInput,
        cursorPos,
      );

      const matches = await api.completePath(token, isFirstToken);
      if (!matches || matches.length === 0) {
        tabSessionRef.current = null;
        return;
      }

      const initialIdx = event.shiftKey ? matches.length - 1 : 0;
      const chosen = matches[initialIdx];
      const beforeToken = manualInput.slice(0, tokenStart);
      const afterToken = manualInput.slice(tokenEnd);
      const nextValue = beforeToken + chosen + afterToken;

      if (matches.length > 1) {
        tabSessionRef.current = {
          beforeToken,
          afterToken,
          matches,
          index: initialIdx,
          expectedValue: nextValue,
        };
      } else {
        // Single match (e.g. a folder): clear session so pressing Tab again drills into it
        tabSessionRef.current = null;
      }

      setManualInputAndCaret(nextValue, beforeToken.length + chosen.length);
      return;
    }

    if (event.key !== "Shift") {
      tabSessionRef.current = null;
    }
  }

  // "Выполнить" runs ONLY the program-built script command
  async function handleRunButton() {
    if (isRunning && api) {
      await api.stopCommand();
      return;
    }
    if (!active || !command) return;
    await executeInTerminal(command);
  }

  async function handleBrowsePathFlag(flag: Flag) {
    if (!api || !active) return;
    let picked: string | null = null;
    if (flag.isPrimaryPath) {
      picked = await api.pickTarget(active.kind === "inspect" ? "file" : "directory");
    } else if (flag.pathKind === "saveFile") {
      picked =
        activeParameterSet === "Rollback"
          ? await api.pickTarget("file")
          : await api.pickSaveOrOpenFile(`Выберите файл для ${flag.name}`);
    } else {
      picked = await api.pickTarget(flag.pathKind === "file" ? "file" : "directory");
    }
    if (picked) updateValue(flag, picked);
  }

  function resolveDroppedPath(event: DragEvent): string {
    const file = event.dataTransfer.files?.[0];
    if (file) {
      return api
        ? api.getPathForFile(file)
        : (file as File & { path?: string }).path || file.name;
    }
    return event.dataTransfer.getData("text/plain")?.trim().replace(/^"|"$/g, "") || "";
  }

  function toggleGroupCollapse(groupId: string) {
    setCollapsedGroups((prev) => ({
      ...prev,
      [groupId]: !prev[groupId],
    }));
  }

  function startRenameGroup(groupId: string, currentName: string) {
    setRenamingGroupId(groupId);
    setRenamingGroupValue(currentName);
  }

  function commitRenameGroup(groupId: string) {
    const nextName = renamingGroupValue.trim();
    setAppScripts((current) =>
      current.map((s) => (s.groupId === groupId ? { ...s, group: nextName } : s)),
    );
    setRenamingGroupId(null);
    setRenamingGroupValue("");
  }

  function toggleScriptHidden(scriptId: string) {
    setAppScripts((current) =>
      normalizeGroups(
        current.map((item) =>
          item.id === scriptId ? { ...item, hidden: !item.hidden } : item,
        ),
      ),
    );
  }

  // Settings: script CRUD
  function resetScriptForm() {
    setEditingScriptId(null);
    setFormTitle("");
    setFormPath("");
    setFormIcon("file");
    setFormGroupId("");
    setFormDescription("");
    setFormHidden(false);
    setFormError("");
  }

  function startEditScript(script: ScriptItem) {
    if (isProtectedHello(script)) return;
    setEditingScriptId(script.id);
    setFormTitle(script.title);
    setFormPath(script.sourcePath);
    setFormIcon(getScriptIconName(script));
    setFormGroupId(script.groupId ?? "");
    setFormDescription(script.description);
    setFormHidden(Boolean(script.hidden));
    setFormError("");
  }

  async function handlePickScriptFile() {
    if (!api) return;
    const picked = await api.pickScriptFile();
    if (picked) {
      setFormPath(picked);
      setFormError("");
      if (!formTitle.trim()) {
        const baseName = picked.split(/[\\/]/).pop()?.replace(/\.ps1$/i, "") ?? "";
        setFormTitle(baseName);
      }
    }
  }

  function handleScriptFileDrop(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    setIsDraggingScriptFile(false);
    const resolved = resolveDroppedPath(event);
    if (resolved) {
      setFormPath(resolved);
      setFormError("");
      if (!formTitle.trim()) {
        const baseName = resolved.split(/[\\/]/).pop()?.replace(/\.ps1$/i, "") ?? "";
        setFormTitle(baseName);
      }
    }
  }

  async function handleSaveScript() {
    if (editingScriptId === "bundled-hello") return;

    const cleanPath = formPath.trim().replace(/^"|"$/g, "");
    const isAbsolute =
      /^[A-Za-z]:[\\/]/.test(cleanPath) ||
      cleanPath.startsWith("\\\\") ||
      cleanPath.startsWith("/");
    if (!isAbsolute || !cleanPath.toLowerCase().endsWith(".ps1")) {
      setFormError("Укажите абсолютный путь к файлу с расширением .ps1");
      return;
    }

    const fileName = cleanPath.split(/[\\/]/).pop() || "script.ps1";
    const baseName = fileName.replace(/\.ps1$/i, "");

    setIsParsing(true);
    let parsedFlags: Flag[] = [];
    let parsedDefaultSet: string | undefined;
    let parsedTitle = "";
    let parsedDesc = "";
    let inferredKind: "rename" | "inspect" | undefined;

    if (api) {
      const parsed = await api.parseScript(cleanPath);
      if (!parsed.ok) {
        setIsParsing(false);
        setFormError(parsed.error || "Не удалось прочитать скрипт");
        return;
      }
      parsedFlags = parsed.flags;
      parsedDefaultSet = parsed.defaultParameterSet;
      parsedTitle = parsed.title || "";
      parsedDesc = parsed.description || "";
      inferredKind = parsed.inferredKind;
    }
    setIsParsing(false);

    const finalTitle = formTitle.trim() || parsedTitle || baseName;
    const resolvedKind: "rename" | "inspect" = inferredKind ?? "rename";

    if (editingScriptId) {
      const selectedGroup = existingGroups.find((g) => g.groupId === formGroupId);
      const resolvedGroupId = selectedGroup ? selectedGroup.groupId : undefined;
      const resolvedGroupName = selectedGroup ? selectedGroup.name : "";

      setAppScripts((current) =>
        normalizeGroups(
          current.map((item) =>
            item.id === editingScriptId
              ? {
                  ...item,
                  file: fileName,
                  title: finalTitle,
                  shortTitle: finalTitle,
                  description: formDescription.trim() || parsedDesc || cleanPath,
                  kind: api ? resolvedKind : item.kind,
                  icon: formIcon,
                  groupId: resolvedGroupId,
                  group: resolvedGroupName,
                  hidden: formHidden,
                  sourcePath: cleanPath,
                  defaultParameterSet: parsedDefaultSet,
                  flags: api ? parsedFlags : item.flags,
                }
              : item,
          ),
        ),
      );
      if (api) {
        setValues((current) => ({
          ...current,
          [editingScriptId]: buildInitialValuesForFlags(parsedFlags),
        }));
      }
    } else {
      const id = `script-${Date.now()}`;
      const newScript: ScriptItem = {
        id,
        file: fileName,
        title: finalTitle,
        shortTitle: finalTitle,
        description: formDescription.trim() || parsedDesc || cleanPath,
        kind: resolvedKind,
        icon: formIcon,
        groupId: undefined,
        group: "",
        hidden: formHidden,
        sourcePath: cleanPath,
        defaultParameterSet: parsedDefaultSet,
        flags: parsedFlags,
      };
      setAppScripts((current) => normalizeGroups([...current, newScript]));
      setValues((current) => ({
        ...current,
        [id]: buildInitialValuesForFlags(parsedFlags),
      }));
    }

    resetScriptForm();
  }

  function handleDeleteScript(scriptId: string) {
    if (scriptId === "bundled-hello") return;
    setAppScripts((current) => normalizeGroups(current.filter((item) => item.id !== scriptId)));
    if (editingScriptId === scriptId) {
      resetScriptForm();
    }
  }

  async function handleReparseScript(script: ScriptItem) {
    if (!api || !script.sourcePath) return;
    const parsed = await api.parseScript(script.sourcePath);
    if (!parsed.ok) return;
    setAppScripts((current) =>
      current.map((item) =>
        item.id === script.id
          ? {
              ...item,
              kind: parsed.inferredKind ?? item.kind,
              defaultParameterSet: parsed.defaultParameterSet,
              flags: parsed.flags,
            }
          : item,
      ),
    );
    setValues((current) => ({
      ...current,
      [script.id]: buildInitialValuesForFlags(parsed.flags),
    }));
  }

  async function handleUnblockAll() {
    if (!api) return;
    const paths = appScripts.map((s) => s.sourcePath).filter(Boolean);
    const res = await api.unblockScripts(paths);
    setUnblockNotice(
      res.ok
        ? `Выполнен Unblock-File для скриптов (${res.count})`
        : `Ошибка Unblock-File: ${res.error}`,
    );
    window.setTimeout(() => setUnblockNotice(""), 3200);
  }

  const themeStyle = {
    "--color-bg": colors.background,
    "--color-surface": colors.surface,
    "--color-raised": colors.raised,
    "--color-border": colors.border,
    "--color-text": colors.text,
    "--color-muted": colors.muted,
    "--color-accent": colors.accent,
    "--color-success": colors.success,
    "--color-warning": colors.warning,
    "--color-danger": colors.danger,
    "--color-terminal": colors.terminal,
  } as CSSProperties;

  const projectRootDisplay = shellInfo.projectRoot || "C:\\PS-Workbench";
  const phantomHelloPath = `${projectRootDisplay.replace(/[\\/]+$/, "")}\\scripts\\hello.ps1`;

  const draggedScript =
    dragState?.active && dragState.dragKind === "script"
      ? appScripts.find((s) => s.id === dragState.id) ?? null
      : null;

  const draggedGroup =
    dragState?.active && dragState.dragKind === "group"
      ? sidebarBlocks.find(
          (b): b is Extract<SidebarBlock, { kind: "group" }> =>
            b.kind === "group" && b.groupId === dragState.id,
        ) ?? null
      : null;

  function renderScriptCard(script: ScriptItem, idx: number, isTopLevel: boolean) {
    const isBeingDragged = Boolean(
      dragState?.active && dragState.dragKind === "script" && dragState.id === script.id,
    );
    const isGroupTarget =
      dropTarget?.kind === "on-script" && dropTarget.targetScriptId === script.id;
    const showLineBefore =
      dropTarget?.kind === "before-script" && dropTarget.targetScriptId === script.id;
    const showLineAfter =
      dropTarget?.kind === "after-script" && dropTarget.targetScriptId === script.id;

    return (
      <div
        key={script.id}
        className="script-card-slot"
        data-drag-top-block={isTopLevel ? "true" : undefined}
        data-drag-top-kind={isTopLevel ? "script" : undefined}
        data-drag-top-id={isTopLevel ? script.id : undefined}
      >
        {showLineBefore && <div className="drop-line" />}
        <button
          type="button"
          data-drag-script-id={script.id}
          className={`script-card ${active?.id === script.id ? "active" : ""} ${isBeingDragged ? "dragging-source" : ""} ${isGroupTarget ? "drop-group-target" : ""}`}
          onMouseDown={(event) => handleScriptMouseDown(event, script.id)}
          onClick={() => {
            if (suppressNextClickRef.current) return;
            setActiveId(script.id);
          }}
        >
          <span className={`script-icon ${script.kind}`}>
            <Icon name={getScriptIconName(script, idx)} size={18} />
          </span>
          <span className="script-copy">
            <strong>{script.shortTitle}</strong>
            <small>{script.file}</small>
          </span>
          {isGroupTarget ? (
            <span className="drop-group-pill">В группу</span>
          ) : (
            <Icon name="chevron" size={15} />
          )}
        </button>
        {showLineAfter && <div className="drop-line" />}
      </div>
    );
  }

  return (
    <main className={`app-shell ${dragState?.active ? "is-dragging-script" : ""}`} style={themeStyle}>
      <header className="titlebar">
        <div className="brand-mark">
          <Icon name="terminal" size={17} />
        </div>
        <div className="brand">
          PS <strong>Workbench</strong>
        </div>
        <div className="window-actions">
          <button aria-label="Свернуть" onClick={() => api?.minimizeWindow()}>
            <Icon name="minimize" size={15} />
          </button>
          <button aria-label="Развернуть" onClick={() => api?.maximizeWindow()}>
            <Icon name="maximize" size={14} />
          </button>
          <button className="close-window" aria-label="Закрыть" onClick={() => api?.closeWindow()}>
            <Icon name="clear" size={15} />
          </button>
        </div>
      </header>

      <div className="workspace">
        <aside className="sidebar">
          <div className="side-heading">
            <span>Сценарии</span>
            <span className="count">{visibleScripts.length}</span>
          </div>
          <nav
            className="script-list"
            ref={scriptListRef}
            aria-label="Выбор сценария"
          >
            {sidebarBlocks.map((block, blockIdx) => {
              if (block.kind === "script") {
                return renderScriptCard(block.script, blockIdx, true);
              }

              const isCollapsed = Boolean(collapsedGroups[block.groupId]);
              const showLineBeforeGroup =
                dropTarget?.kind === "before-group" &&
                dropTarget.targetGroupId === block.groupId;
              const showLineAfterGroup =
                dropTarget?.kind === "after-group" &&
                dropTarget.targetGroupId === block.groupId;
              const isOnGroup =
                dropTarget?.kind === "on-group" && dropTarget.targetGroupId === block.groupId;
              const isGroupBeingDragged = Boolean(
                dragState?.active &&
                  dragState.dragKind === "group" &&
                  dragState.id === block.groupId,
              );
              const isRenaming = renamingGroupId === block.groupId;

              return (
                <div
                  key={block.groupId}
                  className="script-group-wrapper"
                  data-drag-top-block="true"
                  data-drag-top-kind="group"
                  data-drag-top-id={block.groupId}
                >
                  {showLineBeforeGroup && <div className="drop-line" />}
                  <div
                    className={`script-group ${isOnGroup ? "drop-group-target" : ""} ${isGroupBeingDragged ? "dragging-source" : ""}`}
                    data-drag-group-box={block.groupId}
                  >
                    <div
                      className={`script-group-header ${isCollapsed ? "collapsed" : ""}`}
                      data-drag-group-header={block.groupId}
                      data-group-collapsed={isCollapsed ? "true" : "false"}
                      onMouseDown={(event) => handleGroupMouseDown(event, block.groupId)}
                    >
                      <button
                        type="button"
                        className="group-toggle-btn"
                        onClick={() => {
                          if (suppressNextClickRef.current) return;
                          toggleGroupCollapse(block.groupId);
                        }}
                        onDoubleClick={(e) => {
                          e.stopPropagation();
                          startRenameGroup(block.groupId, block.name);
                        }}
                        aria-expanded={!isCollapsed}
                      >
                        <span className="group-chevron">
                          <Icon name="chevron" size={13} />
                        </span>
                        {isRenaming ? null : (
                          <span className={`group-title ${!block.name ? "unnamed" : ""}`}>
                            {block.name || "Без названия"}
                          </span>
                        )}
                      </button>

                      {isRenaming ? (
                        <input
                          className="group-rename-input"
                          autoFocus
                          value={renamingGroupValue}
                          placeholder="Название группы"
                          onChange={(e) => setRenamingGroupValue(e.target.value)}
                          onBlur={() => commitRenameGroup(block.groupId)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") commitRenameGroup(block.groupId);
                            if (e.key === "Escape") {
                              setRenamingGroupId(null);
                              setRenamingGroupValue("");
                            }
                          }}
                        />
                      ) : (
                        <>
                          <button
                            type="button"
                            className="group-rename-btn"
                            title="Переименовать группу"
                            onClick={(e) => {
                              e.stopPropagation();
                              startRenameGroup(block.groupId, block.name);
                            }}
                          >
                            <Icon name="edit" size={11} />
                          </button>
                          <span className="group-count">{block.items.length}</span>
                        </>
                      )}
                    </div>

                    {!isCollapsed && (
                      <div className="script-group-items">
                        {block.items.map((script, idx) => renderScriptCard(script, idx, false))}
                      </div>
                    )}
                  </div>
                  {showLineAfterGroup && <div className="drop-line" />}
                </div>
              );
            })}

            {dropTarget?.kind === "end" && <div className="drop-line" />}
          </nav>

          <div className="side-footer">
            <span className={`status-dot ${isRunning ? "busy" : ""}`} />
            <div>
              <strong>
                {shellInfo.shellName} {shellInfo.version}
              </strong>
              <small>
                {isRunning
                  ? "Выполняется..."
                  : isElectron
                    ? "Готов к работе"
                    : "Предпросмотр (Web)"}
              </small>
            </div>
            <button
              aria-label="Настройки"
              onClick={() => {
                resetScriptForm();
                setSettingsOpen(true);
              }}
            >
              <Icon name="settings" size={18} />
            </button>
          </div>
        </aside>

        <section className="main-panel">
          <div className="content-head">
            {active ? (
              <div>
                <div className="eyebrow">
                  {active.group?.trim()
                    ? `Сценарий · ${active.group.trim()}`
                    : "Активный сценарий"}
                </div>
                <h1>{active.title}</h1>
                <p>{stripDefaultHints(active.description)}</p>
              </div>
            ) : (
              <div>
                <div className="eyebrow">PS Workbench</div>
                <h1>Терминал PowerShell</h1>
                <p>Выберите сценарий в левой панели или введите команду вручную.</p>
              </div>
            )}
          </div>

          <div className="terminal-card">
            <div className="terminal-toolbar">
              <div className="terminal-title">
                <span className="pwsh-icon">&gt;_</span>
                <span>{shellInfo.shellName}</span>
                <small>{shellInfo.shellExe.replace(/\.exe$/i, "")}</small>
              </div>
              <div className="terminal-tools">
                <button
                  onClick={copyCommand}
                  className={copied ? "copied" : ""}
                  disabled={!command}
                >
                  <Icon name={copied ? "check" : "copy"} size={15} />{" "}
                  {copied ? "Скопировано" : "Копировать"}
                </button>
                <button onClick={clearTerminal} aria-label="Очистить терминал">
                  <Icon name="clear" size={15} /> Очистить
                </button>
              </div>
            </div>

            <div className="terminal-body" ref={terminalScrollRef}>
              {showBanner && (
                <div className="terminal-banner">
                  <div className="terminal-meta">Windows PowerShell 5.1</div>
                  <div className="terminal-meta">
                    (C) Корпорация Майкрософт (Microsoft Corporation). Все права защищены.
                  </div>
                </div>
              )}

              {entries.map((entry) => {
                if (entry.kind === "command") {
                  return (
                    <div className="history-command" key={entry.id}>
                      <span className="prompt">PS</span>
                      {" "}
                      <span className="prompt-path">
                        {entry.promptSuffix ?? promptSuffix}&gt;
                      </span>
                      {entry.text ? (
                        <>
                          {" "}
                          <code>{entry.text}</code>
                        </>
                      ) : null}
                    </div>
                  );
                }
                if (entry.kind === "stdout") {
                  const segs = parseAnsiSegments(entry.text);
                  return (
                    <div className="terminal-line stdout" key={entry.id}>
                      {segs.length === 0
                        ? "\u00A0"
                        : segs.map((seg, i) =>
                            seg.color ? (
                              <span key={i} style={{ color: seg.color }}>
                                {seg.text}
                              </span>
                            ) : (
                              <span key={i}>{seg.text}</span>
                            ),
                          )}
                    </div>
                  );
                }
                return (
                  <div className={`terminal-line ${entry.kind}`} key={entry.id}>
                    {entry.text}
                  </div>
                );
              })}

              <div className="command-line">
                <span className="prompt">PS</span>
                {" "}
                <span className="prompt-path">{promptSuffix}&gt;</span>
                {" "}
                {command ? <code>{command}</code> : null}
                <span className="cursor" />
              </div>
            </div>

            <form
              ref={manualFormRef}
              className="terminal-manual-bar"
              onClick={() => manualInputRef.current?.focus()}
              onSubmit={(event) => {
                event.preventDefault();
                if (isRunning) return;
                const cmd = manualInput.trim();
                setManualInput("");
                historyIndexRef.current = -1;
                historyDraftRef.current = "";
                tabSessionRef.current = null;
                if (cmd) {
                  setCommandHistory((prev) => {
                    if (prev[prev.length - 1] === cmd) return prev;
                    return [...prev, cmd].slice(-200);
                  });
                  void executeInTerminal(cmd);
                }
              }}
            >
              <span className="prompt">PS&gt;</span>
              <input
                ref={manualInputRef}
                value={manualInput}
                onChange={(event) => {
                  historyIndexRef.current = -1;
                  tabSessionRef.current = null;
                  setManualInput(event.target.value);
                }}
                onKeyDown={(event) => void handleManualKeyDown(event)}
                placeholder="Ввести команды PowerShell и нажать Enter..."
                disabled={isRunning}
              />
            </form>

            <div className="terminal-status">
              <button
                className={`run-button status-run-button ${isRunning ? "running" : ""}`}
                onClick={handleRunButton}
                disabled={!isRunning && !command}
              >
                <Icon name={isRunning ? "stop" : "play"} size={14} />{" "}
                {isRunning ? "Остановить" : "Выполнить"}
              </button>
            </div>
          </div>
        </section>

        <aside className="parameters">
          <div className="parameters-head">
            <div>
              <h2>Параметры</h2>
              <span>{active ? `${active.flags.length} доступно` : "0 доступно"}</span>
            </div>
            {active && active.flags.length > 0 && (
              <button
                onClick={() =>
                  setValues((current) => ({
                    ...current,
                    [active.id]: buildInitialValuesForFlags(active.flags),
                  }))
                }
              >
                Сбросить
              </button>
            )}
          </div>
          <div className="parameter-scroll">
            {!active && (
              <div className="empty-flags">
                <p>Выберите сценарий в левой панели, чтобы настроить его параметры.</p>
              </div>
            )}
            {active && active.flags.length === 0 && (
              <div className="empty-flags">
                <p>
                  {active.sourcePath
                    ? "В блоке param(...) этого скрипта параметров не обнаружено."
                    : "Укажите путь к файлу .ps1 в Настройках — параметры загрузятся автоматически."}
                </p>
              </div>
            )}
            {active?.flags.map((flag) => {
              const value = values[active.id]?.[flag.id] ?? (flag.type === "toggle" ? false : "");
              const exclusiveSet = getExclusiveSwitchSet(flag, active.defaultParameterSet);
              const compatible =
                exclusiveSet !== null || isCompatibleWithSet(flag.parameterSets, activeParameterSet);
              const isMandatoryNow =
                flag.mandatory ||
                (Boolean(activeParameterSet) &&
                  Boolean(flag.mandatoryInSets?.includes(activeParameterSet)));

              if (flag.type === "toggle") {
                return (
                  <label
                    className={`toggle-row ${!compatible ? "param-disabled" : ""}`}
                    key={flag.id}
                  >
                    <span>
                      <strong>
                        {flag.label} <code>{flag.name}</code>
                      </strong>
                      <small>{stripDefaultHints(flag.description)}</small>
                    </span>
                    <input
                      type="checkbox"
                      disabled={!compatible}
                      checked={Boolean(value)}
                      onChange={(event) => updateValue(flag, event.target.checked)}
                    />
                    <span className="toggle-ui">
                      <i />
                    </span>
                  </label>
                );
              }

              if (flag.type === "path") {
                const effectivePlaceholder = "C:\\path\\to\\target";
                const pathIcon =
                  flag.isPrimaryPath && active.kind === "rename" ? "folder" : "file";

                return (
                  <div
                    className={`field-group ${!compatible ? "param-disabled" : ""}`}
                    key={flag.id}
                    onDragOver={
                      compatible
                        ? (e) => {
                            e.preventDefault();
                            setDraggingFlagId(flag.id);
                          }
                        : undefined
                    }
                    onDragLeave={() => setDraggingFlagId(null)}
                    onDrop={
                      compatible
                        ? (e) => {
                            e.preventDefault();
                            setDraggingFlagId(null);
                            const dropped = resolveDroppedPath(e);
                            if (dropped) updateValue(flag, dropped);
                          }
                        : undefined
                    }
                  >
                    <span className="field-label">
                      <strong>
                        {flag.isPrimaryPath
                          ? active.kind === "inspect"
                            ? "Путь к файлу"
                            : "Путь к директории"
                          : flag.label}
                        {isMandatoryNow ? <em className="req-star"> *</em> : null}
                      </strong>
                      <code>{flag.name}</code>
                    </span>
                    <small>{stripDefaultHints(flag.description)}</small>
                    <div
                      className={`flag-file-row ${draggingFlagId === flag.id ? "drag-over" : ""}`}
                    >
                      <input
                        type="text"
                        disabled={!compatible}
                        value={String(value)}
                        placeholder={effectivePlaceholder}
                        onChange={(event) => updateValue(flag, event.target.value)}
                      />
                      {String(value) && compatible && (
                        <button
                          type="button"
                          className="flag-clear-btn"
                          title="Очистить путь"
                          onClick={() => updateValue(flag, "")}
                        >
                          <Icon name="clear" size={13} />
                        </button>
                      )}
                      <button
                        type="button"
                        disabled={!compatible}
                        title={pathIcon === "folder" ? "Выбрать директорию" : "Выбрать файл"}
                        onClick={() => void handleBrowsePathFlag(flag)}
                      >
                        <Icon name={pathIcon} size={14} />
                      </button>
                    </div>
                  </div>
                );
              }

              return (
                <label
                  className={`field-group ${!compatible ? "param-disabled" : ""}`}
                  key={flag.id}
                >
                  <span className="field-label">
                    <strong>
                      {flag.label}
                      {isMandatoryNow ? <em className="req-star"> *</em> : null}
                    </strong>
                    <code>{flag.name}</code>
                  </span>
                  <small>{stripDefaultHints(flag.description)}</small>
                  {flag.type === "select" ? (
                    <div className="select-wrap">
                      <select
                        disabled={!compatible}
                        value={String(value)}
                        onChange={(event) => updateValue(flag, event.target.value)}
                      >
                        {flag.options?.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    </div>
                  ) : (
                    <input
                      type={flag.type}
                      disabled={!compatible}
                      value={String(value)}
                      min={flag.min}
                      max={flag.max}
                      placeholder={flag.placeholder}
                      onChange={(event) => updateValue(flag, event.target.value)}
                    />
                  )}
                </label>
              );
            })}
          </div>
        </aside>
      </div>

      {draggedScript && dragState && (
        <div
          className="drag-ghost"
          style={{
            left: dragState.currentX + 12,
            top: dragState.currentY - 18,
          }}
        >
          <span className={`script-icon ${draggedScript.kind}`}>
            <Icon name={getScriptIconName(draggedScript)} size={16} />
          </span>
          <span className="script-copy">
            <strong>{draggedScript.shortTitle}</strong>
            <small>{draggedScript.file}</small>
          </span>
        </div>
      )}

      {draggedGroup && dragState && (
        <div
          className="drag-ghost"
          style={{
            left: dragState.currentX + 12,
            top: dragState.currentY - 18,
          }}
        >
          <span className="script-icon rename">
            <Icon name="folder" size={16} />
          </span>
          <span className="script-copy">
            <strong>{draggedGroup.name || "Без названия"}</strong>
            <small>Группа · {draggedGroup.items.length}</small>
          </span>
        </div>
      )}

      {settingsOpen && (
        <div className="modal-backdrop" onMouseDown={() => setSettingsOpen(false)}>
          <section
            className="settings-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="settings-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <header className="settings-header">
              <div>
                <span className="settings-kicker">PS Workbench</span>
                <h2 id="settings-title">Настройки</h2>
              </div>
              <button
                className="modal-close"
                onClick={() => setSettingsOpen(false)}
                aria-label="Закрыть настройки"
              >
                <Icon name="clear" size={18} />
              </button>
            </header>

            <div className="settings-layout">
              <nav className="settings-nav" aria-label="Разделы настроек">
                <button
                  className={settingsSection === "scripts" ? "active" : ""}
                  onClick={() => setSettingsSection("scripts")}
                >
                  <Icon name="file" size={17} />
                  <span>
                    <strong>Сценарии</strong>
                    <small>Подключение .ps1</small>
                  </span>
                </button>
                <button
                  className={settingsSection === "terminal" ? "active" : ""}
                  onClick={() => setSettingsSection("terminal")}
                >
                  <Icon name="terminal" size={17} />
                  <span>
                    <strong>Терминал</strong>
                    <small>Приветствие и путь</small>
                  </span>
                </button>
                <button
                  className={settingsSection === "colors" ? "active" : ""}
                  onClick={() => setSettingsSection("colors")}
                >
                  <span className="palette-icon" />
                  <span>
                    <strong>Цвета</strong>
                    <small>Палитра интерфейса</small>
                  </span>
                </button>
              </nav>

              <div className="settings-content">
                {settingsSection === "scripts" ? (
                  <>
                    <div className="settings-title-row">
                      <div>
                        <h3>Подключённые сценарии</h3>
                        <p>
                          Добавляйте, скрывайте, редактируйте и удаляйте скрипты. Группировать и
                          переставлять скрипты можно перетаскиванием в левой панели.
                        </p>
                      </div>
                      <span className="settings-count">{appScripts.length}</span>
                    </div>

                    <div className="settings-utility-bar">
                      <button
                        type="button"
                        className="utility-btn"
                        onClick={() => void handleUnblockAll()}
                      >
                        <Icon name="unlock" size={14} /> Разблокировать все (Unblock-File)
                      </button>
                    </div>
                    {unblockNotice && <div className="unblock-notice">{unblockNotice}</div>}

                    <div className="connected-scripts">
                      {appScripts.map((script) => {
                        const locked = isProtectedHello(script);
                        return (
                          <div
                            className={`connected-script ${editingScriptId === script.id ? "editing" : ""} ${script.hidden ? "is-hidden" : ""}`}
                            key={script.id}
                          >
                            <span className="connected-file-icon">
                              <Icon name={getScriptIconName(script)} size={17} />
                            </span>
                            <div className="connected-script-info">
                              <div className="connected-script-title-line">
                                <strong>{script.title}</strong>
                                {locked && <span className="builtin-tag">Встроен</span>}
                                {script.groupId && (
                                  <span className="group-tag">
                                    {script.group?.trim() || "Без названия"}
                                  </span>
                                )}
                                {script.hidden && <span className="hidden-tag">Скрыт</span>}
                              </div>
                              <small>
                                {script.sourcePath || `Не задан путь (${script.file})`}
                              </small>
                            </div>
                            <div className="script-row-actions">
                              <button
                                title={script.hidden ? "Показать в списке" : "Скрыть из списка"}
                                onClick={() => toggleScriptHidden(script.id)}
                              >
                                <Icon name={script.hidden ? "eyeOff" : "eye"} size={14} />
                              </button>
                              {!locked && (
                                <>
                                  {script.sourcePath && (
                                    <button
                                      title="Перечитать флаги из файла"
                                      onClick={() => void handleReparseScript(script)}
                                    >
                                      <Icon name="refresh" size={14} />
                                    </button>
                                  )}
                                  <button
                                    title="Редактировать"
                                    onClick={() => startEditScript(script)}
                                  >
                                    <Icon name="edit" size={14} />
                                  </button>
                                  <button
                                    className="danger-action"
                                    title="Удалить"
                                    onClick={() => handleDeleteScript(script.id)}
                                  >
                                    <Icon name="trash" size={14} />
                                  </button>
                                </>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    <div
                      className={`add-script-card ${isDraggingScriptFile ? "drag-over" : ""}`}
                      onDragOver={(e) => {
                        e.preventDefault();
                        setIsDraggingScriptFile(true);
                      }}
                      onDragLeave={(e) => {
                        e.preventDefault();
                        setIsDraggingScriptFile(false);
                      }}
                      onDrop={handleScriptFileDrop}
                    >
                      <div className="add-script-heading">
                        <Icon name="file" size={17} />
                        <div>
                          <strong>
                            {editingScriptId ? "Редактировать сценарий" : "Добавить сценарий"}
                          </strong>
                          <small>
                            Укажите путь вручную, через «Обзор» или перетащите .ps1 сюда
                          </small>
                        </div>
                      </div>

                      <div className={editingScriptId ? "form-grid-2" : "form-grid-1"}>
                        <div>
                          <label htmlFor="scriptTitle">Название</label>
                          <div className="settings-path-input">
                            <input
                              id="scriptTitle"
                              value={formTitle}
                              onChange={(event) => setFormTitle(event.target.value)}
                              placeholder="Привет, Мир!"
                            />
                          </div>
                        </div>
                        {editingScriptId && (
                          <div>
                            <label htmlFor="scriptGroup">Группа</label>
                            <div className="settings-select-wrap">
                              <select
                                id="scriptGroup"
                                value={formGroupId}
                                onChange={(event) => setFormGroupId(event.target.value)}
                              >
                                <option value="">Без группы</option>
                                {existingGroups.map((g, idx) => (
                                  <option key={g.groupId} value={g.groupId}>
                                    {g.name || `Без названия #${idx + 1}`}
                                  </option>
                                ))}
                              </select>
                            </div>
                          </div>
                        )}
                      </div>

                      <div className="icon-picker-section field-top-gap">
                        <label>Иконка</label>
                        <div className="icon-picker-grid" role="radiogroup" aria-label="Выбор иконки">
                          {SCRIPT_ICON_OPTIONS.map((opt) => (
                            <button
                              key={opt.id}
                              type="button"
                              role="radio"
                              aria-checked={formIcon === opt.id}
                              title={opt.label}
                              className={`icon-picker-btn ${formIcon === opt.id ? "active" : ""}`}
                              onClick={() => setFormIcon(opt.id)}
                            >
                              <Icon name={opt.id} size={16} />
                            </button>
                          ))}
                        </div>
                      </div>

                      <label htmlFor="scriptPath" className="field-top-gap">
                        Абсолютный путь к .ps1 файлу
                      </label>
                      <div className="settings-path-row">
                        <div className={`settings-path-input ${formError ? "invalid" : ""}`}>
                          <input
                            id="scriptPath"
                            value={formPath}
                            onChange={(event) => {
                              setFormPath(event.target.value);
                              setFormError("");
                            }}
                            onKeyDown={(event) => {
                              if (event.key === "Enter") void handleSaveScript();
                            }}
                            placeholder={phantomHelloPath}
                          />
                        </div>
                        <button
                          type="button"
                          className="settings-browse-btn"
                          onClick={() => void handlePickScriptFile()}
                        >
                          Обзор
                        </button>
                      </div>

                      <label htmlFor="scriptDesc" className="field-top-gap">
                        Описание
                      </label>
                      <div className="settings-path-input">
                        <input
                          id="scriptDesc"
                          value={formDescription}
                          onChange={(event) => setFormDescription(event.target.value)}
                          placeholder='Выводит на экран "Hello, World!"'
                        />
                      </div>

                      <label className="inline-checkbox field-top-gap">
                        <input
                          type="checkbox"
                          checked={formHidden}
                          onChange={(event) => setFormHidden(event.target.checked)}
                        />
                        <span>Скрыть сценарий из боковой панели</span>
                      </label>

                      {formError && <span className="path-error">{formError}</span>}

                      <div className="form-actions">
                        <button
                          className="add-script-button"
                          onClick={() => void handleSaveScript()}
                          disabled={isParsing}
                        >
                          {isParsing
                            ? "Чтение флагов..."
                            : editingScriptId
                              ? "Сохранить изменения"
                              : "+ Добавить в программу"}
                        </button>
                        {editingScriptId && (
                          <button className="cancel-edit-button" onClick={resetScriptForm}>
                            Отмена
                          </button>
                        )}
                      </div>
                    </div>
                  </>
                ) : settingsSection === "terminal" ? (
                  <>
                    <div className="settings-title-row">
                      <div>
                        <h3>Приветственное сообщение терминала</h3>
                        <p>
                          Выберите текст, который отображается в строке приглашения терминала{" "}
                          <code>PS {"{Приветственное сообщение}"}&gt;</code>.
                        </p>
                      </div>
                    </div>

                    <div className="prompt-options">
                      <button
                        type="button"
                        className={`prompt-option-card ${promptMode === "name" ? "active" : ""}`}
                        onClick={() => setPromptMode("name")}
                      >
                        <span className="radio-dot" />
                        <div>
                          <strong>Название проекта</strong>
                          <small>Отображает название приложения</small>
                          <code>
                            PS{" "}
                            {(shellInfo.projectName || "PS Workbench").replace(/^PS\s+/i, "")}&gt;
                          </code>
                        </div>
                      </button>

                      <button
                        type="button"
                        className={`prompt-option-card ${promptMode === "path" ? "active" : ""}`}
                        onClick={() => setPromptMode("path")}
                      >
                        <span className="radio-dot" />
                        <div>
                          <strong>Абсолютный путь к корню проекта</strong>
                          <small>Показывает полное расположение программы</small>
                          <code>PS {projectRootDisplay}&gt;</code>
                        </div>
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="settings-title-row">
                      <div>
                        <h3>Цвета интерфейса</h3>
                        <p>Настройте каждый семантический цвет приложения.</p>
                      </div>
                      <button className="reset-colors" onClick={() => setColors(defaultColors)}>
                        Сбросить цвета
                      </button>
                    </div>
                    <div className="color-grid">
                      {(Object.keys(colors) as Array<keyof ThemeColors>).map((key) => (
                        <label className="color-setting" key={key}>
                          <span>{colorLabels[key]}</span>
                          <div>
                            <input
                              type="color"
                              value={colors[key]}
                              onChange={(event) =>
                                setColors((current) => ({
                                  ...current,
                                  [key]: event.target.value,
                                }))
                              }
                            />
                            <code>{colors[key].toUpperCase()}</code>
                          </div>
                        </label>
                      ))}
                    </div>
                    <div className="palette-preview">
                      <div className="gradient-bar gradient-bw" title="От чёрного до белого" />
                      <div
                        className="gradient-bar gradient-rgb"
                        title="От красного к зелёному, к синему и к красному"
                      />
                    </div>
                  </>
                )}
              </div>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
