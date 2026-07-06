"""
app/ui/terminal.py
───────────────────
Terminal UI using the Rich library.
This is the interface the student uses — running in their terminal, beside their IDE.

Rich gives you:
  - Coloured panels and boxes
  - Syntax-highlighted code
  - Progress bars
  - Tables
  - Markdown rendering

This file handles ALL display logic — the agent logic stays in agent/.
Keep these two concerns completely separate.

Docs: https://rich.readthedocs.io/en/stable/
"""

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich import print as rprint
import sys

console = Console()


def display_welcome():
    """
    Shows the welcome screen with app name and instructions.
    """
    console.print(Panel.fit(
        "[bold cyan]Welcome to code.teach[/bold cyan]\n"
        "Your AI-powered coding tutor.\n\n"
        "Instructions:\n"
        "- Type your code when prompted.\n"
        "- Use Ctrl+Z (Windows) or Ctrl+D (Unix) then Enter to submit code.\n"
        "- Use the signal menu to adjust the lesson.",
        title="code.teach"
    ))


def display_task(response):
    """
    Displays a new task to the student.
    """
    console.print(Panel(response.message, title="Teacher"))
    
    if response.task:
        console.print(Panel(response.task, title="Your Task", border_style="green"))
        
    if response.starter_code:
        console.print("[bold]Starter Code:[/bold]")
        syntax = Syntax(response.starter_code, "python", theme="monokai", line_numbers=True)
        console.print(syntax)
        
    if response.concept_tested:
        console.print(f"[dim]Concept: {response.concept_tested}[/dim]")


def display_feedback(response):
    """
    Displays rich feedback after code submission.
    """
    style = "green" if response.mode == "correct" else "yellow"
    console.print(Panel(response.message, title=f"Feedback [{response.mode.upper()}]", border_style=style))
    
    if response.rich_feedback:
        fb = response.rich_feedback
        if fb.what_worked:
            console.print(f"[green]✓ {fb.what_worked}[/green]")
        if fb.what_to_fix:
            console.print(f"[yellow]! {fb.what_to_fix}[/yellow]")
        if fb.concept_gap:
            console.print(f"[purple]? {fb.concept_gap}[/purple]")
        if fb.pattern_name:
            console.print(f"[blue]◈ Pattern: {fb.pattern_name}[/blue]")


def display_session_summary(summary):
    """
    Displays the end-of-session summary.
    """
    if not summary:
        console.print("[yellow]No summary available.[/yellow]")
        return
        
    table = Table(title="Session Summary")
    table.add_column("Covered", style="cyan")
    table.add_column("Mastered", style="green")
    table.add_column("Struggling", style="red")
    
    # Just show first few to avoid clutter
    table.add_row(
        ", ".join(summary.covered[:5]),
        ", ".join(summary.mastered[:5]),
        ", ".join(summary.struggling[:5])
    )
    
    console.print(table)
    console.print(Panel(f"[bold]Next Focus:[/bold] {summary.next_focus}"))


def display_level_suggestion(suggestion: str, current_level: str) -> bool:
    """
    Shows a level change suggestion.
    """
    next_level = "intermediate" if current_level == "beginner" else "advanced"
    if suggestion == "down":
        next_level = "beginner" if current_level == "intermediate" else "intermediate"
        
    choice = Prompt.ask(f"Teacher suggests moving {suggestion} to {next_level}. Accept?", choices=["y", "n"], default="y")
    return choice == "y"


def get_code_input() -> str:
    """
    Opens a multi-line code input.
    """
    console.print("\n[bold cyan]Enter your code (Ctrl+Z/D then Enter to submit):[/bold cyan]")
    code_lines = sys.stdin.readlines()
    return "".join(code_lines)


def get_signal_input() -> tuple[str, str]:
    """
    Shows signal menu and gets student input.
    """
    console.print("\n[bold]Signals:[/bold] [1] Too Hard | [2] Too Easy | [3] Lost | [4] More Practice | [5] Missing Concept | [0] Submit Code")
    choice = Prompt.ask("Action", choices=["0", "1", "2", "3", "4", "5", "end"], default="0")
    
    signals = {
        "1": "too_hard",
        "2": "too_easy",
        "3": "lost_concept",
        "4": "more_practice",
        "5": "missing_concept",
        "end": "end"
    }
    
    if choice == "0":
        return None, None
        
    signal = signals.get(choice)
    detail = None
    if signal == "missing_concept":
        detail = Prompt.ask("What concept do you need help with?")
        
    return signal, detail

