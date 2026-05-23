import sqlite3
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()
app = typer.Typer()

DB_PATH = Path.home() / ".local" / "share" / "todo_app"
DB_PATH.mkdir(parents=True, exist_ok=True)


def init_db():
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
    con.commit()
    return con


@app.command()
def add(task: str, due: str = None):
    if due:
        try:
            datetime.strptime(due, "%Y-%m-%d")
        except ValueError:
            console.print(
                "[red]Invalid date format. Use YYYY-MM-DD (e.g. 2026-05-25)[/red]"
            )
            return
    if not due:
        due = datetime.now().strftime("%Y-%m-%d")

    con = init_db()
    cur = con.cursor()
    cur.execute("INSERT INTO tasks (task, due) VALUES (?, ?)", (task, due))
    con.commit()
    con.close()
    typer.echo(f"Added: {task}")


@app.command(name="list")
def list_tasks(filter: str = None):
    con = init_db()
    cur = con.cursor()

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
        con.close()
        return

    tasks = cur.fetchall()
    con.close()

    if not tasks:
        console.print("No tasks yet.")
        return

    table = Table(title="Tasks")
    table.add_column("ID")
    table.add_column("Status")
    table.add_column("Task")
    table.add_column("Due")

    for t in tasks:
        id, task, due, done = t
        due_text = "-"
        if due:
            if not done and due < datetime.now().strftime("%Y-%m-%d"):
                due_text = f"[red]{due}[/red]"
            else:
                due_text = due
        status = "[green]✓[/green]" if done else "[yellow]○[/yellow]"
        task_text = f"[green]{task}[/green]" if done else f"[yellow]{task}[/yellow]"
        table.add_row(str(id), status, task_text, due_text)

    console.print(table)


@app.command()
def delete(id: int):
    con = init_db()
    cur = con.cursor()
    cur.execute("DELETE FROM tasks WHERE id = ?", (id,))
    con.commit()
    con.close()
    typer.echo(f"Deleted task {id}.")


@app.command()
def complete(id: int):
    con = init_db()
    cur = con.cursor()
    cur.execute("UPDATE tasks SET done = 1 WHERE id = ?", (id,))
    if cur.rowcount == 0:
        console.print("[red]Task not found.[/red]")
    else:
        con.commit()
        typer.echo(f"Completed task {id}.")
    con.close()


if __name__ == "__main__":
    app()
