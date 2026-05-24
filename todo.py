import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()
app = typer.Typer()

# Store DB in the standard Linux user data directory
DB_PATH = Path.home() / ".local" / "share" / "todo_app"
DB_PATH.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_db():
    # setup the connection and ensure table exists whenever we access the db
    con = sqlite3.connect(DB_PATH / "tasks.db")
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            due TEXT,
            done INTEGER DEFAULT 0
        )
    """)
    try:
        # yield lets the command run its logic using this connection
        yield con
        con.commit()
    finally:
        # always close the connection when finished, even if errors occur
        con.close()


@app.command()
def add(task: str, due: str = None):
    # Validate date format if the user provided one
    if due:
        try:
            datetime.strptime(due, "%Y-%m-%d")
        except ValueError:
            console.print(
                "[red]Invalid date format. Use YYYY-MM-DD (e.g. 2026-05-25)[/red]"
            )
            return

    # Default to today if no date provided
    if not due:
        due = datetime.now().strftime("%Y-%m-%d")

    # use the context manager to handle the connection lifecycle
    with get_db() as con:
        cur = con.cursor()
        cur.execute("INSERT INTO tasks (task, due) VALUES (?, ?)", (task, due))
    typer.echo(f"Added: {task}")


@app.command(name="list")
def list_tasks(filter: str = None):
    with get_db() as con:
        cur = con.cursor()

        # Handle different view filters
        if filter == "done":
            cur.execute("SELECT * FROM tasks WHERE done = 1")
        elif filter == "pending":
            cur.execute("SELECT * FROM tasks WHERE done = 0")
        elif filter == "overdue":
            cur.execute(
                "SELECT * FROM tasks WHERE done = 0 AND due < ?",
                (datetime.now().strftime("%Y-%m-%d"),),
            )
        elif filter is None:
            cur.execute("SELECT * FROM tasks")
        else:
            console.print("[red]Invalid filter. Use: done, pending, overdue[/red]")
            return

        tasks = cur.fetchall()

    if not tasks:
        console.print("No tasks yet.")
        return

    # Build the Rich UI table
    table = Table(title="Tasks")
    table.add_column("ID")
    table.add_column("Status")
    table.add_column("Task")
    table.add_column("Due")

    for t in tasks:
        id, task, due, done = t
        due_text = "-"

        if due:
            # Highlight overdue tasks in red
            if not done and due < datetime.now().strftime("%Y-%m-%d"):
                due_text = f"[red]{due}[/red]"
            else:
                due_text = due

        status = "[green]✓[/green]" if done else "[yellow]○[/yellow]"
        task_text = (
            f"[green][strike]{task}[/strike][/green]"
            if done
            else f"[yellow]{task}[/yellow]"
        )
        table.add_row(str(id), status, task_text, due_text)

    console.print(table)


@app.command()
def delete(id: int):
    with get_db() as con:
        cur = con.cursor()
        cur.execute("DELETE FROM tasks WHERE id = ?", (id,))

        if cur.rowcount == 0:
            console.print("[red]Task not found.[/red]")
        else:
            typer.echo(f"Deleted task {id}.")


@app.command()
def purge():
    with get_db() as con:
        cur = con.cursor()
        cur.execute("DELETE FROM tasks WHERE done = 1")

        if cur.rowcount == 0:
            console.print("[yellow]No completed tasks to clean up.[/yellow]")
        else:
            console.print(f"[green]Purged {cur.rowcount} completed tasks![/green]")


@app.command()
def edit(id: int, task: str = None, due: str = None):
    with get_db() as con:
        cur = con.cursor()

        # Check if task exists
        cur.execute("SELECT id FROM tasks WHERE id = ?", (id,))
        if not cur.fetchone():
            console.print(f"[red]Task {id} not found.[/red]")
            return

        # Ensure user passed something to update
        if not task and not due:
            console.print(
                "[yellow]Nothing to update. Provide --task or --due.[/yellow]"
            )
            return

        # Validate new date
        if due:
            try:
                datetime.strptime(due, "%Y-%m-%d")
            except ValueError:
                console.print(
                    "[red]Invalid date format. Use YYYY-MM-DD (e.g. 2026-05-25)[/red]"
                )
                return

        # Apply updates dynamically
        if task:
            cur.execute("UPDATE tasks SET task = ? WHERE id = ?", (task, id))
        if due:
            cur.execute("UPDATE tasks SET due = ? WHERE id = ?", (due, id))

        typer.echo(f"Updated task {id}.")


@app.command()
def complete(id: int):
    with get_db() as con:
        cur = con.cursor()
        cur.execute("UPDATE tasks SET done = 1 WHERE id = ?", (id,))

        # rowcount is 0 if the ID didn't exist in the DB
        if cur.rowcount == 0:
            console.print("[red]Task not found.[/red]")
        else:
            typer.echo(f"Completed task {id}.")


if __name__ == "__main__":
    app()
