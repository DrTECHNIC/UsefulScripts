const fs = require("fs");
const { execFile } = require("child_process");

const PATH_PARAM_REGEX =
  /^(path|literalpath|filepath|file|folder|folderpath|dir|directory|target|targetpath|source|sourcepath|input|inputpath|root|rootpath)$/i;

const FILE_HINT_REGEX = /^(filepath|file|inputfile|targetfile)$/i;
const DIR_HINT_REGEX = /^(folder|folderpath|dir|directory|root|rootpath)$/i;
const FILE_FLAG_REGEX = /(log|file|output|input|report|config|json|csv|txt)path$/i;

function stripDefaultHints(text) {
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

function normalizeDefault(raw, type) {
  if (raw === null || raw === undefined) return type === "toggle" ? false : "";
  const trimmed = String(raw).trim();
  if (!trimmed) return type === "toggle" ? false : "";
  if (type === "toggle") {
    return /^\$true$/i.test(trimmed);
  }
  if (/^\$null$/i.test(trimmed)) return "";
  if (
    (trimmed.startsWith("'") && trimmed.endsWith("'")) ||
    (trimmed.startsWith('"') && trimmed.endsWith('"'))
  ) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
}

function mapTypeAndOptions(typeName, validateSet) {
  if (Array.isArray(validateSet) && validateSet.length > 0) {
    return { type: "select", options: validateSet, isBoolParam: false };
  }
  const t = (typeName || "").toLowerCase();
  if (t.includes("switch")) {
    return { type: "toggle", isBoolParam: false };
  }
  if (t === "bool" || t === "boolean") {
    return { type: "toggle", isBoolParam: true };
  }
  if (
    t === "int" ||
    t === "int32" ||
    t === "int64" ||
    t === "long" ||
    t === "double" ||
    t === "decimal" ||
    t === "float" ||
    t === "single" ||
    t === "uint32" ||
    t === "byte"
  ) {
    return { type: "number", isBoolParam: false };
  }
  return { type: "text", isBoolParam: false };
}

function parseBoundNumber(val) {
  if (val === null || val === undefined) return undefined;
  const s = String(val).trim();
  if (!s || /MaxValue|MinValue/i.test(s)) return undefined;
  const n = Number(s);
  return Number.isFinite(n) ? n : undefined;
}

function buildResultFromRaw(raw) {
  const params = Array.isArray(raw.Parameters) ? raw.Parameters : [];
  const synopsis = typeof raw.Synopsis === "string" ? stripDefaultHints(raw.Synopsis.trim()) : "";
  const customTitle = typeof raw.Title === "string" ? raw.Title.trim() : "";
  const customTarget = typeof raw.Target === "string" ? raw.Target.trim().toLowerCase() : "";
  const bodyTargetHint = typeof raw.BodyTargetHint === "string" ? raw.BodyTargetHint.trim().toLowerCase() : "";
  const defaultParameterSet =
    typeof raw.DefaultParameterSet === "string" && raw.DefaultParameterSet.trim()
      ? raw.DefaultParameterSet.trim()
      : "";
  const supportsShouldProcess = Boolean(raw.SupportsShouldProcess);
  const whatIfHelp = typeof raw.WhatIfHelp === "string" ? stripDefaultHints(raw.WhatIfHelp.trim()) : "";

  let inferredKind;
  if (customTarget === "file" || customTarget === "inspect") {
    inferredKind = "inspect";
  } else if (customTarget === "directory" || customTarget === "folder" || customTarget === "rename") {
    inferredKind = "rename";
  }

  let primaryPathAssigned = false;
  const flags = [];

  for (let i = 0; i < params.length; i++) {
    const p = params[i];
    const name = p.Name;
    if (!name) continue;
    const aliases = Array.isArray(p.Aliases) ? p.Aliases : [];

    const mapped = mapTypeAndOptions(p.Type, p.ValidateSet);
    let type = mapped.type;
    const options = mapped.options;
    const isBoolParam = mapped.isBoolParam;
    let isPrimaryPath = false;
    let pathKind;

    if (type === "text" && !primaryPathAssigned && PATH_PARAM_REGEX.test(name)) {
      type = "path";
      isPrimaryPath = true;
      primaryPathAssigned = true;
      const isFileParam =
        FILE_HINT_REGEX.test(name) || aliases.some((a) => FILE_HINT_REGEX.test(String(a)));
      const isDirParam =
        DIR_HINT_REGEX.test(name) || aliases.some((a) => DIR_HINT_REGEX.test(String(a)));
      if (!inferredKind) {
        if (isFileParam) {
          inferredKind = "inspect";
        } else if (isDirParam) {
          inferredKind = "rename";
        } else if (bodyTargetHint === "file") {
          inferredKind = "inspect";
        } else {
          inferredKind = "rename";
        }
      }
      pathKind = inferredKind === "inspect" ? "file" : "directory";
    } else if (type === "text" && FILE_FLAG_REGEX.test(name)) {
      type = "path";
      pathKind = "saveFile";
    }

    let defaultValue = normalizeDefault(p.DefaultValue, type === "path" ? "text" : type);
    if (isPrimaryPath && defaultValue === ".") {
      defaultValue = "";
    }

    const cleanedDesc = stripDefaultHints(p.Description ? String(p.Description).trim() : "");
    const description =
      cleanedDesc ||
      (type === "path"
        ? isPrimaryPath
          ? pathKind === "file"
            ? "Путь к целевому файлу"
            : "Путь к целевой директории"
          : "Путь к файлу"
        : type === "toggle"
          ? "Флаг без значения"
          : type === "number"
            ? "Числовое значение параметра"
            : type === "select"
              ? "Значение из списка"
              : "Текстовое значение параметра");

    const parameterSets = Array.isArray(p.ParameterSets) ? p.ParameterSets : [];
    const mandatoryInSets = Array.isArray(p.MandatoryInSets) ? p.MandatoryInSets : [];

    flags.push({
      id: name.toLowerCase(),
      name: `-${name}`,
      label: name,
      description,
      type,
      placeholder:
        type === "number"
          ? "Введите число"
          : type === "path"
            ? "C:\\path\\to\\target"
            : "Введите значение",
      defaultValue:
        type === "select"
          ? defaultValue || (options && options[0]) || ""
          : defaultValue,
      options,
      min: parseBoundNumber(p.MinRange),
      max: parseBoundNumber(p.MaxRange),
      mandatory: Boolean(p.Mandatory),
      isBoolParam,
      isPrimaryPath,
      pathKind,
      parameterSets,
      mandatoryInSets,
    });
  }

  if (supportsShouldProcess && !flags.some((f) => f.id === "whatif")) {
    flags.push({
      id: "whatif",
      name: "-WhatIf",
      label: "WhatIf",
      description:
        whatIfHelp || "Предпросмотр планируемых изменений без фактического выполнения",
      type: "toggle",
      defaultValue: false,
      mandatory: false,
      isBoolParam: false,
      parameterSets: [],
      mandatoryInSets: [],
    });
  }

  return {
    ok: true,
    title: customTitle || undefined,
    description: synopsis || undefined,
    defaultParameterSet: defaultParameterSet || undefined,
    inferredKind,
    flags,
  };
}

function parseWithRegexFallback(content) {
  const clean = content.replace(/^\uFEFF/, "");
  const titleMatch = clean.match(/^#\s*PSWorkbench:Title\s*=\s*(.+)$/im);
  const targetMatch = clean.match(/^#\s*PSWorkbench:Target\s*=\s*(\w+)$/im);
  const synopsisMatch = clean.match(/\.SYNOPSIS\s*[\r\n]+([^\r\n#]+)/i);
  const hasLeafCheck = /-PathType\s+Leaf\b/i.test(clean);
  const hasContainerCheck = /-PathType\s+Container\b/i.test(clean);
  const bodyTargetHint = hasLeafCheck && !hasContainerCheck ? "file" : hasContainerCheck ? "directory" : "";

  const paramHelp = {};
  const helpRegex = /\.PARAMETER\s+(\w+)\s*[\r\n]+([\s\S]*?)(?=\r?\n\s*\.[A-Z]+|\r?\n\s*#>|$)/gi;
  let hm;
  while ((hm = helpRegex.exec(clean)) !== null) {
    paramHelp[hm[1].toLowerCase()] = hm[2].replace(/\s+/g, " ").trim();
  }

  const cbMatch = clean.match(/\[CmdletBinding\s*\(([^)]*)\)\]/i);
  let supportsShouldProcess = false;
  let defaultParameterSet = "";
  if (cbMatch) {
    supportsShouldProcess = /SupportsShouldProcess\s*=\s*\$true/i.test(cbMatch[1]);
    const dps = cbMatch[1].match(/DefaultParameterSetName\s*=\s*['"]([^'"]+)['"]/i);
    if (dps) defaultParameterSet = dps[1];
  }

  const paramBlockMatch = clean.match(/\bparam\s*\(([\s\S]*?)\)\s*(?:\r?\n|$)/i);
  if (!paramBlockMatch) {
    return buildResultFromRaw({
      Title: titleMatch ? titleMatch[1].trim() : "",
      Target: targetMatch ? targetMatch[1].trim() : "",
      BodyTargetHint: bodyTargetHint,
      Synopsis: synopsisMatch ? synopsisMatch[1].trim() : "",
      SupportsShouldProcess: supportsShouldProcess,
      DefaultParameterSet: defaultParameterSet,
      WhatIfHelp: paramHelp["whatif"] || "",
      Parameters: [],
    });
  }

  const block = paramBlockMatch[1];
  const lines = block.split(/\r?\n/);
  const parameters = [];
  let pendingComment = "";
  let pendingAttrs = "";

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) continue;
    if (line.startsWith("#")) {
      pendingComment = line.replace(/^#+\s*/, "").trim();
      continue;
    }

    const varMatch = line.match(/\$([A-Za-z_][A-Za-z0-9_]*)\s*(?:=\s*([^,#]+))?/);
    if (!varMatch) {
      pendingAttrs += " " + line;
      continue;
    }

    const fullChunk = pendingAttrs + " " + line;
    const name = varMatch[1];
    const defaultVal = varMatch[2] ? varMatch[2].trim().replace(/,$/, "") : "";
    const inlineCommentMatch = line.match(/#\s*(.+)$/);
    const inlineComment = inlineCommentMatch ? inlineCommentMatch[1].trim() : "";

    let validateSet = [];
    const vsMatch = fullChunk.match(/ValidateSet\s*\(([^)]+)\)/i);
    if (vsMatch) {
      validateSet = vsMatch[1]
        .split(",")
        .map((s) => s.trim().replace(/^['"]|['"]$/g, ""))
        .filter(Boolean);
    }

    let minRange = null;
    let maxRange = null;
    const vrMatch = fullChunk.match(/ValidateRange\s*\(([^,]+),([^)]+)\)/i);
    if (vrMatch) {
      minRange = vrMatch[1].trim();
      maxRange = vrMatch[2].trim();
    }

    let typeName = "string";
    const typeMatches = [...fullChunk.matchAll(/\[([A-Za-z0-9_.]+(?:\[\])?)\]/g)];
    for (const m of typeMatches) {
      const candidate = m[1];
      if (!/^(Parameter|Validate|Alias|CmdletBinding)/i.test(candidate)) {
        typeName = candidate;
      }
    }

    const aliases = [];
    const aliasMatch = fullChunk.match(/Alias\s*\(([^)]+)\)/i);
    if (aliasMatch) {
      for (const a of aliasMatch[1].split(",")) {
        const cleaned = a.trim().replace(/^['"]|['"]$/g, "");
        if (cleaned) aliases.push(cleaned);
      }
    }

    const parameterSets = [];
    const mandatoryInSets = [];
    let mandatory = false;
    const paramAttrs = [...fullChunk.matchAll(/\[Parameter\s*\(([^)]*)\)\]/gi)];
    for (const pa of paramAttrs) {
      const body = pa[1];
      const ps = body.match(/ParameterSetName\s*=\s*['"]([^'"]+)['"]/i);
      const isMand = /Mandatory(?:\s*=\s*\$true)?(?=,|\s|$)/i.test(body);
      if (ps) {
        if (!parameterSets.includes(ps[1])) parameterSets.push(ps[1]);
        if (isMand && !mandatoryInSets.includes(ps[1])) mandatoryInSets.push(ps[1]);
      } else if (isMand) {
        mandatory = true;
      }
    }

    const helpMsgMatch = fullChunk.match(/HelpMessage\s*=\s*['"]([^'"]+)['"]/i);

    parameters.push({
      Name: name,
      Type: typeName,
      ValidateSet: validateSet,
      MinRange: minRange,
      MaxRange: maxRange,
      DefaultValue: defaultVal,
      Mandatory: mandatory,
      ParameterSets: parameterSets,
      MandatoryInSets: mandatoryInSets,
      Aliases: aliases,
      Description:
        paramHelp[name.toLowerCase()] ||
        (helpMsgMatch ? helpMsgMatch[1] : "") ||
        inlineComment ||
        pendingComment,
    });

    pendingComment = "";
    pendingAttrs = "";
  }

  return buildResultFromRaw({
    Title: titleMatch ? titleMatch[1].trim() : "",
    Target: targetMatch ? targetMatch[1].trim() : "",
      BodyTargetHint: bodyTargetHint,
    Synopsis: synopsisMatch ? synopsisMatch[1].trim() : "",
    SupportsShouldProcess: supportsShouldProcess,
    DefaultParameterSet: defaultParameterSet,
    WhatIfHelp: paramHelp["whatif"] || "",
    Parameters: parameters,
  });
}

function parseScriptFile(scriptPath, shellExe) {
  return new Promise((resolve) => {
    if (!scriptPath || !fs.existsSync(scriptPath)) {
      resolve({
        ok: false,
        error: "Файл скрипта не найден по указанному пути",
        flags: [],
      });
      return;
    }

    const psCode = `
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'
$scriptFile = $env:PSW_PARSE_TARGET
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($scriptFile, [ref]$tokens, [ref]$errors)
$rawContent = Get-Content -LiteralPath $scriptFile -Raw -Encoding UTF8

$customTitle = ''
if ($rawContent -match '(?im)^#\\s*PSWorkbench:Title\\s*=\\s*(.+)$') {
  $customTitle = $Matches[1].Trim()
}

$customTarget = ''
if ($rawContent -match '(?im)^#\\s*PSWorkbench:Target\\s*=\\s*(\\w+)$') {
  $customTarget = $Matches[1].Trim()
}

$bodyTargetHint = ''
$hasLeafCheck = $rawContent -match '(?i)-PathType\s+Leaf\b'
$hasContainerCheck = $rawContent -match '(?i)-PathType\s+Container\b'
if ($hasLeafCheck -and -not $hasContainerCheck) {
  $bodyTargetHint = 'file'
} elseif ($hasContainerCheck) {
  $bodyTargetHint = 'directory'
}

$synopsis = ''
if ($rawContent -match '(?is)\\.SYNOPSIS\\s*[\\r\\n]+([^\\r\\n#]+)') {
  $synopsis = $Matches[1].Trim()
}

$paramHelp = @{}
$helpMatches = [regex]::Matches($rawContent, '(?is)\\.PARAMETER\\s+(\\w+)\\s*[\\r\\n]+(.*?)(?=\\r?\\n\\s*\\.[A-Z]+|\\r?\\n\\s*#>|$)')
foreach ($m in $helpMatches) {
  $paramHelp[$m.Groups[1].Value.ToLower()] = ($m.Groups[2].Value -replace '\\s+', ' ').Trim()
}

$supportsShouldProcess = $false
$defaultParameterSet = ''
if ($ast.ParamBlock -and $ast.ParamBlock.Attributes) {
  foreach ($attr in $ast.ParamBlock.Attributes) {
    if ($attr -is [System.Management.Automation.Language.AttributeAst] -and $attr.TypeName.Name -eq 'CmdletBinding') {
      foreach ($named in $attr.NamedArguments) {
        if ($named.ArgumentName -eq 'SupportsShouldProcess') {
          if (-not $named.Argument -or $named.Argument.Extent.Text -match '(?i)\\$true|1') {
            $supportsShouldProcess = $true
          }
        } elseif ($named.ArgumentName -eq 'DefaultParameterSetName' -and $named.Argument) {
          $defaultParameterSet = [string]$named.Argument.Value
        }
      }
    }
  }
}

$lines = $rawContent -split '\\r?\\n'
$resultParams = @()

if ($ast.ParamBlock -and $ast.ParamBlock.Parameters) {
  foreach ($p in $ast.ParamBlock.Parameters) {
    $name = $p.Name.VariablePath.UserPath
    $typeName = 'string'
    $validateSet = @()
    $minRange = $null
    $maxRange = $null
    $mandatory = $false
    $helpMessage = ''
    $parameterSets = @()
    $mandatoryInSets = @()
    $aliases = @()

    foreach ($attr in $p.Attributes) {
      if ($attr -is [System.Management.Automation.Language.TypeConstraintAst]) {
        $typeName = $attr.TypeName.Name
      } elseif ($attr -is [System.Management.Automation.Language.AttributeAst]) {
        $attrName = $attr.TypeName.Name
        if ($attrName -eq 'ValidateSet') {
          foreach ($arg in $attr.PositionalArguments) {
            if ($arg.Value) { $validateSet += [string]$arg.Value }
          }
        } elseif ($attrName -eq 'ValidateRange') {
          if ($attr.PositionalArguments.Count -ge 1) { $minRange = $attr.PositionalArguments[0].Extent.Text }
          if ($attr.PositionalArguments.Count -ge 2) { $maxRange = $attr.PositionalArguments[1].Extent.Text }
        } elseif ($attrName -eq 'Alias') {
          foreach ($arg in $attr.PositionalArguments) {
            if ($arg.Value) { $aliases += [string]$arg.Value }
          }
        } elseif ($attrName -eq 'Parameter') {
          $thisSet = ''
          $thisMandatory = $false
          foreach ($named in $attr.NamedArguments) {
            if ($named.ArgumentName -eq 'ParameterSetName' -and $named.Argument) {
              $thisSet = [string]$named.Argument.Value
            } elseif ($named.ArgumentName -eq 'Mandatory') {
              if (-not $named.Argument -or $named.Argument.Extent.Text -match '(?i)\\$true|1') {
                $thisMandatory = $true
              }
            } elseif ($named.ArgumentName -eq 'HelpMessage' -and $named.Argument) {
              $helpMessage = [string]$named.Argument.Value
            }
          }
          if ($thisSet) {
            if ($parameterSets -notcontains $thisSet) { $parameterSets += $thisSet }
            if ($thisMandatory -and ($mandatoryInSets -notcontains $thisSet)) { $mandatoryInSets += $thisSet }
          } elseif ($thisMandatory) {
            $mandatory = $true
          }
        }
      }
    }

    $desc = ''
    if ($paramHelp.ContainsKey($name.ToLower())) {
      $desc = $paramHelp[$name.ToLower()]
    } elseif ($helpMessage) {
      $desc = $helpMessage
    } else {
      $lineIdx = $p.Extent.StartLineNumber - 1
      if ($lineIdx -ge 0 -and $lineIdx -lt $lines.Length) {
        if ($lines[$lineIdx] -match '#\\s*(.+)$') {
          $desc = $Matches[1].Trim()
        } elseif ($lineIdx -gt 0 -and $lines[$lineIdx - 1] -match '^\\s*#\\s*(.+)$') {
          $desc = $Matches[1].Trim()
        }
      }
    }

    $defVal = ''
    if ($p.DefaultValue) {
      $defVal = $p.DefaultValue.Extent.Text
    }

    $resultParams += [PSCustomObject]@{
      Name            = $name
      Type            = $typeName
      ValidateSet     = $validateSet
      MinRange        = $minRange
      MaxRange        = $maxRange
      DefaultValue    = $defVal
      Mandatory       = $mandatory
      ParameterSets   = $parameterSets
      MandatoryInSets = $mandatoryInSets
      Aliases         = $aliases
      Description     = $desc
    }
  }
}

$whatIfHelp = ''
if ($paramHelp.ContainsKey('whatif')) { $whatIfHelp = $paramHelp['whatif'] }

[PSCustomObject]@{
  Title                 = $customTitle
  Target                = $customTarget
  BodyTargetHint        = $bodyTargetHint
  Synopsis              = $synopsis
  SupportsShouldProcess = $supportsShouldProcess
  DefaultParameterSet   = $defaultParameterSet
  WhatIfHelp            = $whatIfHelp
  Parameters            = $resultParams
} | ConvertTo-Json -Depth 6 -Compress
`;

    execFile(
      shellExe || "powershell.exe",
      ["-NoLogo", "-NoProfile", "-NonInteractive", "-Command", psCode],
      {
        env: { ...process.env, PSW_PARSE_TARGET: scriptPath },
        timeout: 8000,
        maxBuffer: 1024 * 1024,
        windowsHide: true,
      },
      (err, stdout) => {
        if (!err && stdout && stdout.trim()) {
          try {
            const parsed = JSON.parse(stdout.trim());
            resolve(buildResultFromRaw(parsed));
            return;
          } catch (_) {
            // Fall through to regex fallback
          }
        }

        try {
          const content = fs.readFileSync(scriptPath, "utf8");
          resolve(parseWithRegexFallback(content));
        } catch (readErr) {
          resolve({
            ok: false,
            error: `Не удалось прочитать файл: ${readErr.message}`,
            flags: [],
          });
        }
      },
    );
  });
}

module.exports = { parseScriptFile, parseWithRegexFallback };
