#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETHICAL AI TERMINAL - Public Edition
A sleek, AI-integrated orchestrator for Termux and Linux.
"""

import os
import sys
import subprocess
import httpx
from pathlib import Path

# UI Dependencies
try:
    from rich.console import Console, Group
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.markdown import Markdown
except ImportError:
    print("Installing dependencies...")
    os.system("pip install rich httpx")
    from rich.console import Console, Group, Panel, Table, Text, Markdown

console = Console()

class Orchestrator:
    def __init__(self):
        # API Configuration
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        
        if self.groq_key:
            self.api_key = self.groq_key
            self.base_url = "https://api.groq.com/openai/v1/chat/completions"
            self.model = "llama-3.3-70b-versatile"
        else:
            self.api_key = self.openai_key
            self.base_url = "https://api.openai.com/v1/chat/completions"
            self.model = "gpt-4o-mini"

    def get_banner(self):
        logo = Text("""
    ████████╗███████╗██████╗ ███╗   ███╗██╗   ██╗██╗  ██╗
    ╚══██╔══╝██╔════╝██╔══██╗████╗ ████║██║   ██║╚██╗██╔╝
       ██║   █████╗  ██████╔╝██╔████╔██║██║   ██║ ╚███╔╝ 
       ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║██║   ██║ ██╔██╗ 
       ██║   ███████╗██║  ██║██║ ╚═╝ ██║╚██████╔╝██╔╝ ██╗
       ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝""", style="bold green")
        return Panel(Group(logo, Text("PUBLIC EDITION | KEYWORD: 'ai'", justify="center", style="dim cyan")), border_style="green")

    def ask_ai(self, query):
        if not self.api_key:
            console.print("[bold red]Key Error:[/bold red] Export GROQ_API_KEY or OPENAI_API_KEY.")
            return

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a terminal assistant expert. Provide concise, accurate commands."},
                {"role": "user", "content": query}
            ]
        }

        with console.status("[bold green]Querying AI..."):
            try:
                # Direct HTTP call bypasses local proxy issues (Orbot/VPN)
                with httpx.Client(proxies=None) as client:
                    r = client.post(self.base_url, headers=headers, json=payload, timeout=20.0)
                    resp = r.json()
                    if "choices" in resp:
                        content = resp['choices'][0]['message']['content']
                        console.print(Panel(Markdown(content), title="AI Response", border_style="magenta"))
                    else:
                        console.print(Panel(f"[red]Error:[/red]\n{resp}", title="Server Response"))
            except Exception as e:
                console.print(f"[red]Connection Failure: {e}[/red]")

    def run(self):
        if "--banner" in sys.argv:
            console.print(self.get_banner())
            return

        os.system('clear')
        console.print(self.get_banner())
        
        while True:
            try:
                # Dynamic CWD for clean prompt
                cwd = os.getcwd().replace(str(Path.home()), "~")
                cmd = console.input(f"[bold green]➜[/bold green] [bold cyan]{cwd}[/bold cyan] ").strip()
                
                if not cmd: continue
                if cmd.lower() in ['q', 'exit', 'quit']: break
                
                if cmd.lower().startswith("ai "):
                    self.ask_ai(cmd[3:])
                elif cmd.lower() == "clear":
                    os.system('clear')
                    console.print(self.get_banner())
                else:
                    # Execute standard shell commands
                    subprocess.run(cmd, shell=True)
            except KeyboardInterrupt:
                print("")
                continue

if __name__ == "__main__":
    Orchestrator().run()
