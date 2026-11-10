"""Machine settings for the pipeline. Every path the scripts touch outside the working folder comes from here.

Defaults follow the layout the v2.0 and v2.1 runs used; override any of them with environment variables:
  SG_ROOT          folder that holds new_corpus/ (inputs, answers, judge prompts, judgments, run records)
  SG_SET           judge prompt set used for judging, scoring and costs (default 8way, the v2.1 set; 7way is v2.0)
  SG_CWD           folder the dispatchers of the early 7-tools reference run started in (default SG_ROOT); its
                   spelling names that run's transcript folder. Later runs start each dispatcher in its own workspace.
  SG_WS_ROOT       parent of the per-attempt empty workspaces (default ~/ws)
  SG_AGENTS        folder with the subagent definitions (default code/agents next to this file)
  SG_TEMPLATES     folder with judge_prompt_template.md (default code/templates)
  CLAUDE_PROJECTS  Claude Code transcript folder (default ~/.claude/projects)
  CODEX_SESSIONS   Codex transcript folder (default ~/.codex/sessions)
  CODEX_BIN        codex executable (default: the one on PATH)
  CLAUDE_BIN       claude executable (default: the one on PATH, else ~/.local/bin/claude.exe)
  SG_GPT_ORIGINALS folder of the original GPT subagent runs (token_cost reads their usage; default ../bench-codex)
  SG_CPUQ          optional script that blocks until the CPU is free (`python <it> wait`); skipped when unset
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get('SG_ROOT', HERE.parent.parent))
CWD = os.environ.get('SG_CWD', str(ROOT))
WS_ROOT = Path(os.environ.get('SG_WS_ROOT', Path.home() / 'ws'))
AGENTS = Path(os.environ.get('SG_AGENTS', HERE.parent / 'agents'))
TEMPLATES = Path(os.environ.get('SG_TEMPLATES', HERE.parent / 'templates'))
CLAUDE_PROJECTS = Path(os.environ.get('CLAUDE_PROJECTS', Path.home() / '.claude' / 'projects'))
CODEX_SESSIONS = Path(os.environ.get('CODEX_SESSIONS', Path.home() / '.codex' / 'sessions'))
CODEX_BIN = os.environ.get('CODEX_BIN') or shutil.which('codex') or 'codex'
CLAUDE_BIN = (os.environ.get('CLAUDE_BIN') or shutil.which('claude')
              or str(Path.home() / '.local' / 'bin' / 'claude.exe'))
CPUQ = os.environ.get('SG_CPUQ')
GPT_ORIGINALS = Path(os.environ.get('SG_GPT_ORIGINALS', ROOT.parent / 'bench-codex'))
SET = os.environ.get('SG_SET', '8way')
SUFFIX = '' if SET == '7way' else '_' + SET   # v2.0 (7way) file and folder names carry no suffix


def project_dir_name(path):
    """Claude Code names a session's transcript folder after its working folder, every non-alphanumeric as '-'."""
    return re.sub(r'[^A-Za-z0-9]', '-', str(path))


def cpu_wait():
    if CPUQ:
        subprocess.run([sys.executable, CPUQ, 'wait'], check=False)


def home_pattern():
    """Regex for a bare reference to the home folder, in Windows and Git Bash spelling."""
    home = Path.home()
    parts = [re.escape(p) for p in home.parts[1:]]
    drive = re.escape(home.drive.rstrip(':')) if home.drive else ''
    win = (drive + r':[\\/]+' if drive else r'[\\/]') + r'[\\/]+'.join(parts) + r'[\\/]*(?=["\'\s]|$)'
    bash = (r'/' + drive.lower() if drive else '') + '/' + '/'.join(parts) + r'/?(?=["\'\s]|$)'
    return win + '|' + bash


def allowed_system_dirs():
    """Lower-case path prefixes a respondent may legitimately name (OS, programs, the Python install)."""
    windows = os.environ.get('SystemRoot', r'C:\Windows').lower().rstrip('\\') + '\\'
    programs = os.environ.get('ProgramFiles', r'C:\Program Files').lower().rstrip('\\')  # also matches "(x86)"
    python = sys.prefix.lower().rstrip('\\') + '\\'
    local = str(Path.home() / 'AppData' / 'Local' / 'Programs').lower() + '\\'
    return windows, programs, python, local


def home_deny_globs():
    """Claude Code deny-rule paths for the user's desktop, in both spellings Claude Code may use."""
    home = Path.home()
    rest = '/'.join(home.parts[1:])
    drive = home.drive.rstrip(':')
    return [f'//{drive.lower()}/{rest}/Desktop/**', f'//{drive}:/{rest}/Desktop/**'] if drive else [f'/{rest}/Desktop/**']
