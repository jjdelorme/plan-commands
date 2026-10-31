#!/usr/bin/env python3
"""Generic, zero-dependency repository size & complexity analyzer.

Computes file/line counts, language & directory breakdowns, AST/branch
complexity, and a 0..5 Complexity Factor (overall + per-hotspot) with a visual
HTML dashboard.

Usage:
  python3 repo_stats.py [ /path/to/repo ] [--html report.html] [--serve] [--port
  8765]
"""

import argparse
import ast
from collections import defaultdict
import html
import http.server
import math
import os
from pathlib import Path
import re
import socketserver
import subprocess

IGNORE_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "coverage",
    "target",
    "vendor",
    ".idea",
    ".vscode",
    ".gradle",
    ".terraform",
    "out",
    "bin",
    "obj",
}

CODE_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".kts",
    ".c",
    ".cpp",
    ".cc",
    ".h",
    ".hpp",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".scala",
    ".sql",
    ".sh",
    ".bash",
    ".zsh",
    ".css",
    ".scss",
    ".less",
    ".vue",
    ".svelte",
    ".lua",
    ".r",
    ".dart",
    ".ex",
    ".exs",
}

CATEGORY_COLORS = {
    "Tests & QA": "var(--emerald)",
    "Frontend / UI Source": "var(--indigo)",
    "Backend / Core Source": "var(--blue)",
    "Documentation & Specs": "var(--amber)",
    "Database & Migrations": "var(--rose)",
    "Tooling, CI/CD & Scripts": "var(--purple)",
    "Other / Config / Assets": "var(--slate)",
}

COMPLEXITY_SCALE = [
    (
        0,
        "0.0 – 0.9",
        "Trivial",
        "var(--teal)",
        "cc-0",
        "Minimal logic, flat scripts/configs, tiny scope (<2k LOC, CC 1–3).",
    ),
    (
        1,
        "1.0 – 1.9",
        "Simple",
        "var(--emerald)",
        "cc-1",
        "Small, straightforward codebase (2k–10k LOC, avg CC < 4, low branching).",
    ),
    (
        2,
        "2.0 – 2.9",
        "Moderate",
        "var(--blue)",
        "cc-2",
        "Medium application (10k–35k LOC, avg CC 4–6, well-bounded modules).",
    ),
    (
        3,
        "3.0 – 3.9",
        "Complex",
        "var(--amber)",
        "cc-3",
        "Multi-subsystem codebase (35k–100k LOC, avg CC 6–10, dense hotspots CC > 25).",
    ),
    (
        4,
        "4.0 – 4.4",
        "High",
        "#fb923c",
        "cc-4",
        "Large or deeply branched system (100k–250k LOC, many functions CC > 30).",
    ),
    (
        5,
        "4.5 – 5.0",
        "Extreme",
        "var(--rose)",
        "cc-5",
        "Massive scale or heavy cyclomatic tangling (>250k LOC or hotspots CC > 80).",
    ),
]


def score_to_tier(score: float) -> dict:
  """Maps a 0.0..5.0 score to its complexity scale tier metadata."""
  s = max(0.0, min(5.0, score))
  if s < 1.0:
    idx = 0
  elif s < 2.0:
    idx = 1
  elif s < 3.0:
    idx = 2
  elif s < 4.0:
    idx = 3
  elif s < 4.5:
    idx = 4
  else:
    idx = 5
  level, rng, label, color, css_cls, desc = COMPLEXITY_SCALE[idx]
  return {
      "level": level,
      "score": round(s, 1),
      "range": rng,
      "label": label,
      "color": color,
      "css_cls": css_cls,
      "desc": desc,
  }


def func_cc_to_score(cc: int, length: int = 0) -> float:
  """Maps a single function's cyclomatic complexity & length to a 0..5 score."""
  cc_part = min(5.0, math.log2(max(1, cc)) * 0.78)
  len_part = min(5.0, (length / 80.0)) if length > 0 else cc_part
  return round(min(5.0, cc_part * 0.75 + len_part * 0.25), 1)


def file_branch_to_score(branches: int, code_loc: int) -> float:
  """Maps a file's branch count and code lines to a 0..5 score."""
  b_score = min(5.0, math.log2(max(1, branches)) * 0.62)
  loc_score = min(5.0, code_loc / 250.0)
  return round(min(5.0, b_score * 0.65 + loc_score * 0.35), 1)


def get_repo_files(repo_root: Path) -> list[Path]:
  """Uses `git ls-files` if inside a git repo, otherwise walks the directory."""
  try:
    res = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files"],
        capture_output=True,
        text=True,
        check=True,
    )
    files = [
        repo_root / line.strip()
        for line in res.stdout.splitlines()
        if line.strip()
    ]
    if files:
      return [f for f in files if f.is_file()]
  except Exception:
    pass

  files = []
  for root, dirs, filenames in os.walk(repo_root):
    dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
    for name in filenames:
      p = Path(root) / name
      if p.is_file():
        files.append(p)
  return files


def classify_category(rel_path: Path) -> str:
  parts = [p.lower() for p in rel_path.parts]
  name = rel_path.name.lower()
  ext = rel_path.suffix.lower()

  if parts[0] in (
      "docs",
      "doc",
      "plans",
      "user-guide",
      "wiki",
      "documentation",
  ) or ext in (
      ".md",
      ".rst",
      ".adoc",
      ".txt",
  ):
    if name not in ("requirements.txt", "cmakelists.txt"):
      return "Documentation & Specs"

  if (
      any(
          p in ("test", "tests", "__tests__", "spec", "specs", "e2e", "testing")
          for p in parts
      )
      or name.startswith("test_")
      or name.endswith(("_test.py", "_test.go", "_test.rs", "test.java"))
      or ".test." in name
      or ".spec." in name
  ):
    return "Tests & QA"

  if (
      any(
          p
          in (
              "migrations",
              "migration",
              "data_migrations",
              "alembic",
              "prisma",
              "sql",
              "schema",
          )
          for p in parts
      )
      or ext == ".sql"
  ):
    return "Database & Migrations"

  if (
      parts[0]
      in ("scripts", ".github", ".agents", ".circleci", "ci", "ops", "deploy")
      or ext in (".sh", ".bash", ".zsh", ".dockerfile")
      or name in ("dockerfile", "makefile", "justfile", "vagrantfile")
  ):
    return "Tooling, CI/CD & Scripts"

  if parts[0] in ("frontend", "client", "web", "ui") or ext in (
      ".tsx",
      ".jsx",
      ".vue",
      ".svelte",
      ".css",
      ".scss",
      ".less",
      ".html",
  ):
    return "Frontend / UI Source"

  if ext in CODE_EXTENSIONS or parts[0] in (
      "server",
      "backend",
      "src",
      "app",
      "pkg",
      "cmd",
      "internal",
      "lib",
      "core",
      "api",
      "services",
  ):
    return "Backend / Core Source"

  return "Other / Config / Assets"


def count_lines(filepath: Path, ext: str) -> tuple[int, int, int, int]:
  """Returns (total_lines, code_lines, comment_lines, blank_lines)."""
  try:
    content = filepath.read_text(encoding="utf-8")
  except (UnicodeDecodeError, OSError):
    return (0, 0, 0, 0)

  lines = content.splitlines()
  total = len(lines)
  blank = comment = code = 0
  in_block_comment = False

  c_style = ext in (
      ".ts",
      ".tsx",
      ".js",
      ".jsx",
      ".mjs",
      ".cjs",
      ".css",
      ".scss",
      ".go",
      ".rs",
      ".java",
      ".kt",
      ".c",
      ".cpp",
      ".cc",
      ".h",
      ".hpp",
      ".cs",
      ".swift",
      ".php",
      ".scala",
      ".dart",
  )
  hash_style = ext in (
      ".py",
      ".sh",
      ".bash",
      ".zsh",
      ".rb",
      ".yml",
      ".yaml",
      ".toml",
      ".r",
      ".ex",
      ".exs",
  )

  for line in lines:
    s = line.strip()
    if not s:
      blank += 1
      continue
    if c_style:
      if in_block_comment:
        comment += 1
        if "*/" in s:
          in_block_comment = False
        continue
      if s.startswith("//"):
        comment += 1
        continue
      if s.startswith("/*"):
        comment += 1
        if "*/" not in s[2:]:
          in_block_comment = True
        continue
    elif hash_style and s.startswith("#"):
      comment += 1
      continue
    elif ext in (".sql", ".lua") and s.startswith("--"):
      comment += 1
      continue
    code += 1

  return total, code, comment, blank


class PythonComplexityVisitor(ast.NodeVisitor):

  def __init__(self):
    self.classes = 0
    self.functions = 0
    self.async_functions = 0
    self.routes = 0
    self.func_lengths = []
    self.func_complexities = []

  def _calc_cyclomatic(self, node: ast.AST) -> int:
    complexity = 1
    for child in ast.walk(node):
      if isinstance(
          child,
          (
              ast.If,
              ast.For,
              ast.AsyncFor,
              ast.While,
              ast.ExceptHandler,
              ast.With,
              ast.AsyncWith,
              ast.Assert,
              ast.IfExp,
          ),
      ):
        complexity += 1
      elif isinstance(child, ast.BoolOp):
        complexity += len(child.values) - 1
      elif isinstance(child, ast.comprehension):
        complexity += 1 + len(child.ifs)
    return complexity

  def _handle_func(self, node, is_async=False):
    if is_async:
      self.async_functions += 1
    else:
      self.functions += 1
    for dec in node.decorator_list:
      dec_str = ast.unparse(dec) if hasattr(ast, "unparse") else ""
      if any(
          m in dec_str
          for m in (
              ".get(",
              ".post(",
              ".put(",
              ".delete(",
              ".patch(",
              ".api_route(",
              ".route(",
          )
      ):
        self.routes += 1
    length = getattr(node, "end_lineno", node.lineno) - node.lineno + 1
    cc = self._calc_cyclomatic(node)
    self.func_lengths.append((length, node.name))
    self.func_complexities.append((cc, length, node.name))
    self.generic_visit(node)

  def visit_ClassDef(self, node):
    self.classes += 1
    self.generic_visit(node)

  def visit_FunctionDef(self, node):
    self._handle_func(node, is_async=False)

  def visit_AsyncFunctionDef(self, node):
    self._handle_func(node, is_async=True)


def analyze_python_ast(files: list[Path], repo_root: Path):
  total_classes = total_funcs = total_async_funcs = total_routes = 0
  all_lengths = []
  all_cc = []

  for f in files:
    try:
      tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
      v = PythonComplexityVisitor()
      v.visit(tree)
      total_classes += v.classes
      total_funcs += v.functions
      total_async_funcs += v.async_functions
      total_routes += v.routes
      rel = f.relative_to(repo_root)
      all_lengths.extend((l, f"{rel} : {name}") for l, name in v.func_lengths)
      all_cc.extend(
          (c, l, f"{rel} : {name}") for c, l, name in v.func_complexities
      )
    except Exception:
      pass

  return {
      "files": len(files),
      "classes": total_classes,
      "sync_funcs": total_funcs,
      "async_funcs": total_async_funcs,
      "total_funcs": total_funcs + total_async_funcs,
      "routes": total_routes,
      "all_lengths": sorted(all_lengths, reverse=True),
      "all_cc": sorted(all_cc, reverse=True),
  }


def analyze_generic_code_files(files: list[Path], repo_root: Path):
  """Analyzes branch density, functions, hooks, types, and test cases across any code files."""
  funcs_count = hooks = types_count = test_cases = 0
  branch_keywords = re.compile(
      r"\b(if|else\s+if|elif|for|while|case|catch|except|match)\b|\?\s*[^:?]+\s*:|&&|\|\|"
  )
  func_def_re = re.compile(
      r"\b(?:function|def|func|fn)\s+[A-Za-z_]\w*|\bconst\s+[A-Za-z_]\w*\s*=\s*(?:async\s*)?\("
  )
  type_def_re = re.compile(
      r"\b(?:interface|type|struct|class|enum|trait)\s+[A-Z]\w*"
  )
  test_case_re = re.compile(
      r"\b(?:it|test)\s*\(|\bdef\s+test_\w+|\bfunc\s+Test[A-Z]\w*|\#\[test\]"
  )
  file_cc = []

  for f in files:
    try:
      src = f.read_text(encoding="utf-8")
    except Exception:
      continue
    rel = f.relative_to(repo_root)
    _, code_loc, _, _ = count_lines(f, f.suffix.lower())
    hooks += len(
        re.findall(r"\bfunction\s+use[A-Z]\w*|\bconst\s+use[A-Z]\w*\s*=", src)
    )
    funcs_count += len(func_def_re.findall(src))
    types_count += len(type_def_re.findall(src))
    test_cases += len(test_case_re.findall(src))
    cc = 1 + len(branch_keywords.findall(src))
    file_cc.append((cc, code_loc, str(rel)))

  return {
      "files": len(files),
      "funcs_and_components": funcs_count,
      "custom_hooks": hooks,
      "interfaces_types": types_count,
      "test_cases": test_cases,
      "all_files_cc": sorted(file_cc, reverse=True),
      "top_complex_files": sorted(file_cc, reverse=True)[:10],
  }


def compute_repo_complexity_factor(
    cat_stats: dict,
    py_prod: dict,
    other_prod: dict,
    all_prod_files_cc: list,
    largest_files: list,
) -> dict:
  """Computes a composite 0.0..5.0 Complexity Factor with 4 transparent sub-scores."""
  prod_code = (
      cat_stats.get("Backend / Core Source", {}).get("code", 0)
      + cat_stats.get("Frontend / UI Source", {}).get("code", 0)
      + cat_stats.get("Database & Migrations", {}).get("code", 0)
  )
  tot_code = sum(v["code"] for v in cat_stats.values())

  # 1. Volume Score (0..5): piecewise-linear aligned with scale legend thresholds
  if prod_code < 2_000:
    vol_score = (prod_code / 2_000.0) * 1.0
  elif prod_code < 10_000:
    vol_score = 1.0 + ((prod_code - 2_000) / 8_000.0) * 1.0
  elif prod_code < 35_000:
    vol_score = 2.0 + ((prod_code - 10_000) / 25_000.0) * 1.0
  elif prod_code < 100_000:
    vol_score = 3.0 + ((prod_code - 35_000) / 65_000.0) * 1.0
  elif prod_code < 250_000:
    vol_score = 4.0 + ((prod_code - 100_000) / 150_000.0) * 0.5
  else:
    vol_score = min(5.0, 4.5 + ((prod_code - 250_000) / 250_000.0) * 0.5)

  # 2. Control-Flow / Branch Density Score (0..5)
  if py_prod["all_cc"]:
    avg_cc = sum(c for c, _, _ in py_prod["all_cc"]) / len(py_prod["all_cc"])
    high_ratio = sum(1 for c, _, _ in py_prod["all_cc"] if c > 10) / max(
        1, len(py_prod["all_cc"])
    )
    flow_score = min(5.0, (avg_cc / 3.0) + (high_ratio * 5.0))
  elif all_prod_files_cc:
    tot_branches = sum(b for b, _, _ in all_prod_files_cc)
    branches_per_100 = (tot_branches / max(1, prod_code)) * 100.0
    flow_score = min(5.0, branches_per_100 / 3.5)
  else:
    flow_score = 0.5

  # 3. Hotspot Concentration Score (0..5): top function CC, top file branches, files >= 500 LOC
  max_func_cc = py_prod["all_cc"][0][0] if py_prod["all_cc"] else 0
  max_file_branches = all_prod_files_cc[0][0] if all_prod_files_cc else 0
  large_files_count = sum(
      1
      for code, _, _, cat in largest_files
      if code >= 500 and cat != "Tests & QA"
  )
  hotspot_score = min(
      5.0,
      (
          min(2.0, math.log2(max(1, max_func_cc)) * 0.27)
          if max_func_cc
          else min(2.0, max_file_branches / 140.0)
      )
      + min(1.5, max_file_branches / 180.0)
      + min(1.5, large_files_count * 0.08),
  )

  # 4. Architectural Breadth Score (0..5): active categories, APIs, classes/types
  active_cats = sum(1 for v in cat_stats.values() if v["code"] >= 100)
  breadth_score = min(
      5.0,
      active_cats * 0.38
      + min(1.0, py_prod["routes"] / 120.0)
      + min(1.0, (py_prod["classes"] + other_prod["interfaces_types"]) / 300.0),
  )

  overall = round(
      vol_score * 0.25
      + flow_score * 0.30
      + hotspot_score * 0.30
      + breadth_score * 0.15,
      1,
  )
  tier = score_to_tier(overall)
  return {
      "overall": overall,
      "tier": tier,
      "subscores": [
          ("Codebase Volume", round(vol_score, 1), f"{prod_code:,} prod LOC ({tot_code:,} total)"),
          ("Control-Flow Density", round(flow_score, 1), "Branching & cyclomatic density"),
          ("Hotspot Severity", round(hotspot_score, 1), f"{large_files_count} prod files ≥500 LOC"),
          ("Architectural Breadth", round(breadth_score, 1), f"{active_cats} active subsystems"),
      ],
  }


def analyze_repo(repo_root: Path) -> dict:
  files = get_repo_files(repo_root)

  ext_stats = defaultdict(
      lambda: {"files": 0, "total": 0, "code": 0, "comment": 0, "blank": 0, "bytes": 0}
  )
  cat_stats = defaultdict(
      lambda: {"files": 0, "total": 0, "code": 0, "comment": 0, "blank": 0, "bytes": 0}
  )
  dir_stats = defaultdict(lambda: {"files": 0, "total": 0, "code": 0, "bytes": 0})

  file_lines_list = []
  py_prod_files, py_test_files = [], []
  non_py_prod_files, non_py_test_files = [], []
  all_prod_code_files = []

  for f in files:
    rel = f.relative_to(repo_root)
    ext = f.suffix.lower() or f.name
    try:
      size = f.stat().st_size
    except OSError:
      continue
    total, code, comment, blank = count_lines(f, ext)
    cat = classify_category(rel)
    top_dir = f"{rel.parts[0]}/" if len(rel.parts) > 1 else "(root)"

    for d in (ext_stats[ext], cat_stats[cat]):
      d["files"] += 1
      d["total"] += total
      d["code"] += code
      d["comment"] += comment
      d["blank"] += blank
      d["bytes"] += size

    dir_stats[top_dir]["files"] += 1
    dir_stats[top_dir]["total"] += total
    dir_stats[top_dir]["code"] += code
    dir_stats[top_dir]["bytes"] += size

    if code > 0 and ext in CODE_EXTENSIONS:
      file_lines_list.append((code, total, str(rel), cat))
      if cat != "Tests & QA":
        all_prod_code_files.append(f)

    if ext == ".py":
      (py_test_files if cat == "Tests & QA" else py_prod_files).append(f)
    elif ext in CODE_EXTENSIONS:
      (non_py_test_files if cat == "Tests & QA" else non_py_prod_files).append(f)

  git_info = {"commits": "N/A", "tags": 0}
  try:
    git_info["commits"] = subprocess.run(
        ["git", "-C", str(repo_root), "rev-list", "--count", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    git_info["tags"] = len(
        subprocess.run(
            ["git", "-C", str(repo_root), "tag"],
            capture_output=True,
            text=True,
            check=True,
        )
        .stdout.strip()
        .splitlines()
    )
  except Exception:
    pass

  py_prod = analyze_python_ast(py_prod_files, repo_root)
  py_test = analyze_python_ast(py_test_files, repo_root)
  other_prod = analyze_generic_code_files(non_py_prod_files, repo_root)
  other_test = analyze_generic_code_files(non_py_test_files, repo_root)
  all_prod_generic = analyze_generic_code_files(all_prod_code_files, repo_root)

  sorted_files = sorted(file_lines_list, reverse=True)
  complexity = compute_repo_complexity_factor(
      dict(cat_stats),
      py_prod,
      other_prod,
      all_prod_generic["all_files_cc"],
      sorted_files,
  )

  return {
      "repo_name": repo_root.resolve().name,
      "repo_path": str(repo_root.resolve()),
      "ext_stats": dict(ext_stats),
      "cat_stats": dict(cat_stats),
      "dir_stats": dict(dir_stats),
      "largest_files": sorted_files[:15],
      "py_prod": py_prod,
      "py_test": py_test,
      "other_prod": other_prod,
      "other_test": other_test,
      "all_prod_generic": all_prod_generic,
      "complexity": complexity,
      "git": git_info,
  }


def generate_html(data: dict, template_path: Path | None = None) -> str:
  cat_stats = data["cat_stats"]
  tot_files = sum(v["files"] for v in cat_stats.values())
  tot_lines = sum(v["total"] for v in cat_stats.values())
  tot_code = sum(v["code"] for v in cat_stats.values()) or 1
  tot_comment = sum(v["comment"] for v in cat_stats.values())
  tot_blank = sum(v["blank"] for v in cat_stats.values())
  tot_mb = sum(v["bytes"] for v in cat_stats.values()) / (1024 * 1024)

  prod_code = (
      cat_stats.get("Backend / Core Source", {}).get("code", 0)
      + cat_stats.get("Frontend / UI Source", {}).get("code", 0)
  )
  test_code = cat_stats.get("Tests & QA", {}).get("code", 0)
  ratio_str = f"{test_code / prod_code:.2f} : 1" if prod_code > 0 else "N/A"
  total_test_cases = data["py_test"]["total_funcs"] + data["other_test"]["test_cases"]

  comp = data["complexity"]
  tier = comp["tier"]

  code_exts = [
      (ext, s["code"])
      for ext, s in sorted(
          data["ext_stats"].items(), key=lambda x: x[1]["code"], reverse=True
      )
      if ext in CODE_EXTENSIONS and s["code"] > 0
  ]
  top_lang_title = " / ".join(ext for ext, _ in code_exts[:3]) or "Code"
  top_lang_sub = ", ".join(f"{ext}: {loc:,}" for ext, loc in code_exts[:3]) or "No code files"

  sorted_cats = sorted(cat_stats.items(), key=lambda x: x[1]["code"], reverse=True)
  max_cat_code = sorted_cats[0][1]["code"] if sorted_cats else 1

  stacked_segments = []
  legend_items = []
  cat_rows = []
  for cat, s in sorted_cats:
    pct = (s["code"] / tot_code) * 100
    bar_w = (s["code"] / max_cat_code) * 100 if max_cat_code else 0
    color = CATEGORY_COLORS.get(cat, "var(--slate)")
    stacked_segments.append(
        f'<div class="stacked-segment" style="width:{pct:.1f}%;background:{color};"'
        f' title="{html.escape(cat)}: {s["code"]:,} lines ({pct:.1f}%)"></div>'
    )
    legend_items.append(
        f'<div class="legend-item"><span class="dot" style="background:{color};"></span>'
        f"{html.escape(cat)} ({pct:.1f}%)</div>"
    )
    cat_rows.append(f"""
      <tr>
        <td><span class="dot" style="background:{color};margin-right:8px;"></span><strong>{html.escape(cat)}</strong></td>
        <td class="num">{s['files']:,}</td>
        <td class="num">{s['total']:,}</td>
        <td class="num">{s['code']:,}</td>
        <td class="bar-cell"><div class="mini-bar-bg"><div class="mini-bar-fill" style="width:{bar_w:.0f}%;background:{color};"></div></div></td>
        <td class="num">{s['comment']:,}</td>
        <td class="num">{s['blank']:,}</td>
        <td class="num">{s['bytes']/1024:,.1f}</td>
      </tr>""")

  subscore_cards = []
  for name, val, sub in comp["subscores"]:
    st = score_to_tier(val)
    pct = (val / 5.0) * 100
    subscore_cards.append(f"""
      <div class="subscore-box">
        <div class="subscore-head">
          <span>{html.escape(name)}</span>
          <span class="cc-badge {st['css_cls']}">{val:.1f} / 5</span>
        </div>
        <div class="mini-bar-bg" style="height:6px;margin:0.45rem 0;">
          <div class="mini-bar-fill" style="width:{pct:.0f}%;background:{st['color']};"></div>
        </div>
        <div class="subscore-note">{html.escape(sub)}</div>
      </div>""")

  scale_legend_rows = []
  for lvl, rng, label, color, css_cls, desc in COMPLEXITY_SCALE:
    active_style = (
        f"outline: 2px solid {color}; background: rgba(255,255,255,0.04);"
        if lvl == tier["level"]
        else ""
    )
    scale_legend_rows.append(f"""
      <div class="scale-item" style="{active_style}">
        <div class="scale-item-top">
          <span class="cc-badge {css_cls}">Level {lvl} ({rng})</span>
          <strong style="color:{color};font-size:0.86rem;">{html.escape(label)}</strong>
        </div>
        <div class="scale-item-desc">{html.escape(desc)}</div>
      </div>""")

  sorted_exts = sorted(
      data["ext_stats"].items(), key=lambda x: x[1]["code"], reverse=True
  )[:10]
  max_ext_code = sorted_exts[0][1]["code"] if sorted_exts else 1
  ext_rows = []
  for ext, s in sorted_exts:
    bar_w = (s["code"] / max_ext_code) * 100 if max_ext_code else 0
    ext_rows.append(f"""
      <tr>
        <td><code>{html.escape(ext)}</code></td>
        <td class="num">{s['files']:,}</td>
        <td class="num">{s['total']:,}</td>
        <td class="num">{s['code']:,}</td>
        <td class="bar-cell"><div class="mini-bar-bg"><div class="mini-bar-fill" style="width:{bar_w:.0f}%;background:var(--blue);"></div></div></td>
      </tr>""")

  sorted_dirs = sorted(
      data["dir_stats"].items(), key=lambda x: x[1]["code"], reverse=True
  )[:10]
  dir_rows = []
  for d, s in sorted_dirs:
    dir_rows.append(f"""
      <tr>
        <td><code>{html.escape(d)}</code></td>
        <td class="num">{s['files']:,}</td>
        <td class="num">{s['total']:,}</td>
        <td class="num">{s['code']:,}</td>
        <td class="num">{s['bytes']/1024:,.1f}</td>
      </tr>""")

  py = data["py_prod"]
  py_avg_cc = (
      sum(c for c, _, _ in py["all_cc"]) / len(py["all_cc"])
      if py["all_cc"]
      else 0
  )
  py_avg_len = (
      sum(l for l, _ in py["all_lengths"]) / len(py["all_lengths"])
      if py["all_lengths"]
      else 0
  )
  py_high_cc = sum(1 for c, _, _ in py["all_cc"] if c > 10)
  py_very_high = sum(1 for c, _, _ in py["all_cc"] if c > 20)
  py_rows = []
  for cc, length, name in py["all_cc"][:8]:
    fscore = func_cc_to_score(cc, length)
    ftier = score_to_tier(fscore)
    py_rows.append(f"""
      <tr>
        <td><code>{html.escape(name)}</code></td>
        <td class="num"><span class="cc-badge {ftier['css_cls']}">{fscore:.1f} / 5</span></td>
        <td class="num">CC {cc}</td>
        <td class="num">{length}</td>
      </tr>""")

  other = (
      data["other_prod"]
      if data["other_prod"]["files"] > 0
      else data["all_prod_generic"]
  )
  other_rows = []
  for cc, code_loc, name in other["top_complex_files"][:8]:
    fscore = file_branch_to_score(cc, code_loc)
    ftier = score_to_tier(fscore)
    other_rows.append(f"""
      <tr>
        <td><code>{html.escape(name)}</code></td>
        <td class="num"><span class="cc-badge {ftier['css_cls']}">{fscore:.1f} / 5</span></td>
        <td class="num">{cc}</td>
        <td class="num">{code_loc:,}</td>
      </tr>""")

  largest = data["largest_files"]
  max_file_code = largest[0][0] if largest else 1
  file_rows = []
  for idx, (code, total, rel, cat) in enumerate(largest[:12], 1):
    bar_w = (code / max_file_code) * 100 if max_file_code else 0
    color = CATEGORY_COLORS.get(cat, "var(--blue)")
    file_rows.append(f"""
      <tr>
        <td>{idx}</td>
        <td><code>{html.escape(rel)}</code></td>
        <td><span class="tag-cat">{html.escape(cat)}</span></td>
        <td class="num"><strong>{code:,}</strong></td>
        <td class="num">{total:,}</td>
        <td class="bar-cell"><div class="mini-bar-bg"><div class="mini-bar-fill" style="width:{bar_w:.0f}%;background:{color};"></div></div></td>
      </tr>""")

  default_tpl = (
      Path(__file__).resolve().parent.parent / "resources" / "report_template.html"
  )
  if not default_tpl.is_file():
    default_tpl = Path(
        "/home/workspace/cycling-coach/.agents/skills/repo-stats/resources/report_template.html"
    )
  tpl_file = template_path or default_tpl
  template_str = tpl_file.read_text(encoding="utf-8")

  replacements = {
      "{{repo_name}}": html.escape(data["repo_name"]),
      "{{repo_path}}": html.escape(data["repo_path"]),
      "{{git_commits}}": str(data["git"]["commits"]),
      "{{git_tags}}": str(data["git"]["tags"]),
      "{{tot_mb}}": f"{tot_mb:.2f}",
      "{{tot_kb}}": f"{tot_mb * 1024:,.1f}",
      "{{tier_color}}": tier["color"],
      "{{comp_overall}}": f"{comp['overall']:.1f}",
      "{{tier_level}}": str(tier["level"]),
      "{{tier_label}}": html.escape(tier["label"]),
      "{{tot_files}}": f"{tot_files:,}",
      "{{dir_count}}": str(len(data["dir_stats"])),
      "{{tot_lines}}": f"{tot_lines:,}",
      "{{tot_blank}}": f"{tot_blank:,}",
      "{{tot_comment}}": f"{tot_comment:,}",
      "{{tot_code}}": f"{tot_code:,}",
      "{{prod_code}}": f"{prod_code:,}",
      "{{test_code}}": f"{test_code:,}",
      "{{ratio_str}}": ratio_str,
      "{{total_test_cases}}": f"{total_test_cases:,}",
      "{{top_lang_title}}": html.escape(top_lang_title),
      "{{prod_files_count}}": f"{py['files'] + data['other_prod']['files']:,}",
      "{{top_lang_sub}}": html.escape(top_lang_sub),
      "{{subscore_cards}}": "".join(subscore_cards),
      "{{scale_legend_rows}}": "".join(scale_legend_rows),
      "{{stacked_segments}}": "".join(stacked_segments),
      "{{legend_items}}": "".join(legend_items),
      "{{cat_rows}}": "".join(cat_rows),
      "{{ext_rows}}": "".join(ext_rows),
      "{{dir_rows}}": "".join(dir_rows),
      "{{py_total_funcs}}": f"{py['total_funcs']:,}",
      "{{py_avg_len}}": f"{py_avg_len:.1f}",
      "{{py_avg_cc}}": f"{py_avg_cc:.2f}",
      "{{py_high_cc}}": f"{py_high_cc:,}",
      "{{py_very_high}}": f"{py_very_high:,}",
      "{{py_rows}}": "".join(py_rows)
      or '<tr><td colspan="4">No Python AST functions found in repo</td></tr>',
      "{{other_funcs}}": f"{other['funcs_and_components']:,}",
      "{{other_hooks}}": f"{other['custom_hooks']:,}",
      "{{other_types}}": f"{other['interfaces_types']:,}",
      "{{other_test_cases}}": f"{data['other_test']['test_cases']:,}",
      "{{other_rows}}": "".join(other_rows)
      or '<tr><td colspan="4">No code files found</td></tr>',
      "{{file_rows}}": "".join(file_rows),
  }

  for key, val in replacements.items():
    template_str = template_str.replace(key, val)
  return template_str


def print_cli_summary(data: dict):
  cat_stats = data["cat_stats"]
  tot_files = sum(v["files"] for v in cat_stats.values())
  tot_lines = sum(v["total"] for v in cat_stats.values())
  tot_code = sum(v["code"] for v in cat_stats.values())
  tot_mb = sum(v["bytes"] for v in cat_stats.values()) / (1024 * 1024)
  comp = data["complexity"]
  tier = comp["tier"]

  print("=" * 80)
  print(f"REPO SCOPE & COMPLEXITY REPORT: {data['repo_name']} ({data['repo_path']})")
  print("=" * 80)
  print(
      f"SUMMARY: {tot_files:,} files | {tot_lines:,} total lines"
      f" ({tot_code:,} code/content) | {tot_mb:.2f} MB"
  )
  print(
      f"COMPLEXITY FACTOR (0..5): {comp['overall']:.1f} / 5.0 — Tier"
      f" {tier['level']} ({tier['label']})"
  )
  for name, val, sub in comp["subscores"]:
    print(f"  - {name:<24}: {val:.1f} / 5.0  ({sub})")
  print("-" * 80)
  print(f"{'Category':<30} {'Files':>8} {'Total LOC':>12} {'Code/Content':>14}")
  print("-" * 80)
  for cat, s in sorted(
      cat_stats.items(), key=lambda x: x[1]["code"], reverse=True
  ):
    print(f"{cat:<30} {s['files']:>8,} {s['total']:>12,} {s['code']:>14,}")


def main():
  parser = argparse.ArgumentParser(
      description="Analyze repository size, 0..5 complexity factor, and generate an HTML dashboard."
  )
  parser.add_argument(
      "repo",
      nargs="?",
      default=".",
      help="Path to the repository (default: current directory '.')",
  )
  parser.add_argument(
      "--html",
      default=None,
      help="Path to write HTML report (e.g. --html report.html)",
  )
  parser.add_argument(
      "--template",
      default=None,
      help="Optional custom HTML template path with {{placeholder}} tokens",
  )
  parser.add_argument(
      "--serve",
      action="store_true",
      help="Serve the HTML report via a lightweight local HTTP server",
  )
  parser.add_argument(
      "--port",
      type=int,
      default=8765,
      help="Port for --serve (default: 8765)",
  )
  args = parser.parse_args()

  repo_root = Path(args.repo).resolve()
  data = analyze_repo(repo_root)
  print_cli_summary(data)

  html_out = args.html
  if html_out is None and args.serve:
    html_out = str(Path(__file__).resolve().parent / "index.html")

  if html_out:
    out_path = Path(html_out).resolve()
    tpl_path = Path(args.template).resolve() if args.template else None
    out_path.write_text(generate_html(data, tpl_path), encoding="utf-8")
    print(f"\n[+] Wrote zero-dependency HTML report to: {out_path}")

    if args.serve:
      os.chdir(out_path.parent)
      handler = http.server.SimpleHTTPRequestHandler
      socketserver.TCPServer.allow_reuse_address = True
      port = args.port
      while True:
        try:
          with socketserver.TCPServer(("0.0.0.0", port), handler) as httpd:
            print(f"[+] Serving at http://localhost:{port}/{out_path.name}")
            httpd.serve_forever()
          break
        except OSError:
          port += 1


if __name__ == "__main__":
  main()
