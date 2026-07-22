"""
Ask Your Data — a local, private natural-language database analyst.

Type a question in plain English; three local AI models each write SQL, the
queries run against YOUR database on YOUR machine (nothing leaves it), and a
critic model cross-checks their real results to give you a trustworthy answer
with a confidence rating.

Run:  python analyst.py

Commands inside the prompt:
  /sql      show the SQL + raw results behind the last answer
  /schema   show the database tables
  /help     show commands
  /quit     exit
"""

import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import MODELS, DB_FILENAME
from sql_tool import db_exists, DB_PATH
from debate_engine import answer_question

GREEN, YELLOW, RED, BOLD, DIM, RESET = "\033[92m", "\033[93m", "\033[91m", "\033[1m", "\033[2m", "\033[0m"


def doctor() -> bool:
    """Check the environment and guide the user through anything missing,
    in plain language, instead of crashing with a stack trace later."""
    print(f"{BOLD}Ask Your Data — startup check{RESET}\n")
    ok = True

    # 1. database present?
    if db_exists():
        print(f"{GREEN}✓{RESET} Database found: {DB_FILENAME}")
    else:
        print(f"{RED}✗{RESET} Database '{DB_FILENAME}' not found in this folder.")
        print(f"  {DIM}Place your SQLite database here and name it {DB_FILENAME},")
        print(f"  or edit DB_FILENAME in config.py to point at your file.{RESET}")
        ok = False

    # 2. ollama installed?
    try:
        subprocess.run(["ollama", "--version"], capture_output=True, check=True)
        print(f"{GREEN}✓{RESET} Ollama is installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"{RED}✗{RESET} Ollama not found.")
        print(f"  {DIM}Install it from https://ollama.com, then re-run this.{RESET}")
        return False  # nothing else works without it

    # 3. ollama running + models pulled?
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
        installed = result.stdout
        missing = [m for m in MODELS if m.split(":")[0] not in installed]
        if missing:
            print(f"{YELLOW}!{RESET} Missing models: {', '.join(missing)}")
            for m in missing:
                print(f"  {DIM}Run: ollama pull {m}{RESET}")
            ok = False
        else:
            print(f"{GREEN}✓{RESET} All {len(MODELS)} models available: {', '.join(MODELS)}")
    except subprocess.CalledProcessError:
        print(f"{RED}✗{RESET} Ollama is installed but not running. Start it, then re-run.")
        return False

    print()
    return ok


def show_schema():
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    print(f"\n{BOLD}Tables:{RESET}")
    for t in tables:
        cur.execute(f'SELECT COUNT(*) FROM "{t}"')
        print(f"  {t} ({cur.fetchone()[0]} rows)")
    conn.close()
    print()


def confidence_badge(conf: str, agreement: str) -> str:
    color = {"high": GREEN, "medium": YELLOW, "low": RED}.get(conf, RESET)
    return f"{color}[confidence: {conf} · models {agreement}]{RESET}"


def show_last_sql(result):
    if result is None:
        print(f"{DIM}No query run yet.{RESET}\n")
        return
    print(f"\n{BOLD}Behind the last answer:{RESET}")
    if result.healed:
        print(f"{YELLOW}(a self-healing retry ran — first attempt's queries all failed){RESET}")
    for p in result.proposals:
        print(f"\n{BOLD}{p.model}{RESET}")
        if p.failed_to_generate:
            print(f"  {RED}failed to produce a query{RESET}")
        else:
            print(f"  SQL: {p.sql}")
            if p.ran_ok:
                from sql_tool import format_rows
                print(f"  {GREEN}result:{RESET} {format_rows(p.rows)}")
            else:
                print(f"  {RED}{p.message}{RESET}")
    print()


def main():
    if not doctor():
        print(f"{YELLOW}Fix the items above, then run again.{RESET}")
        sys.exit(1)

    print(f"{BOLD}Ready.{RESET} Ask a question about your data in plain English.")
    print(f"{DIM}Your data never leaves this machine. Type /help for commands.{RESET}\n")

    last_result = None
    while True:
        try:
            user_input = input(f"{BOLD}ask ▸{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not user_input:
            continue
        if user_input == "/quit":
            print("Bye.")
            break
        if user_input == "/help":
            print("  /sql — show SQL behind last answer\n  /schema — list tables\n  /quit — exit\n")
            continue
        if user_input == "/schema":
            show_schema()
            continue
        if user_input == "/sql":
            show_last_sql(last_result)
            continue

        print(f"{DIM}Consulting {len(MODELS)} models + critic…{RESET}")
        last_result = answer_question(user_input)
        print(f"\n{last_result.final_answer}")
        print(confidence_badge(last_result.confidence, last_result.agreement_level))
        print(f"{DIM}(/sql to see the queries behind this){RESET}\n")


if __name__ == "__main__":
    main()
