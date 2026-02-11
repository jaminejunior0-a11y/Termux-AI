#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TERMUX AI ORCHESTRATOR v7.2.1.1
Vibe Coding Terminal for Android/Termux
Enhanced with AI Screen Reading (Look/See commands)
"""

import os
import sys
import io
import re
import json
import time
import select
import termios
import tty
import pty
import fcntl
import struct
import signal
import subprocess
import atexit
import readline
import shutil
import platform
import uuid
import base64
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from collections import deque, defaultdict
from enum import Enum
import textwrap
import inspect

# UTF-8 encoding fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
else:
    os.environ.setdefault('LC_ALL', 'en_US.UTF-8')
    os.environ.setdefault('LANG', 'en_US.UTF-8')

# Try to import required packages
REQUIRED_PACKAGES = ['openai', 'rich', 'pygments', 'requests', 'colorama', 'pillow']
MISSING_PACKAGES = []

for package in REQUIRED_PACKAGES:
    try:
        __import__(package.replace('-', '_'))
    except ImportError:
        MISSING_PACKAGES.append(package)

if MISSING_PACKAGES:
    print(f"Installing missing packages: {MISSING_PACKAGES}")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install"] + MISSING_PACKAGES, check=True)
        print("Installation complete!")
    except subprocess.CalledProcessError:
        print("Warning: Could not install all packages. Some features may be limited.")

# Now import
import openai
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.table import Table
from rich.spinner import Spinner
from rich.live import Live
from rich.prompt import Prompt, Confirm
from rich.status import Status
from rich.syntax import Syntax
from rich.layout import Layout
from rich.columns import Columns
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn
import requests
import colorama

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

colorama.init()


class TermuxContext:
    """Maintains awareness of Termux environment state"""
    
    def __init__(self):
        self.is_termux = self._detect_termux()
        self.home = Path(os.environ.get('HOME', '/data/data/com.termux/files/home'))
        self.prefix = Path(os.environ.get('PREFIX', '/data/data/com.termux/files/usr'))
        self.storage = self.home / "storage"
        self.installed_packages: set = set()
        self.available_editors: List[str] = []
        self.python_packages: set = set()
        self.node_packages: set = set()
        self.project_root: Optional[Path] = None
        self.current_context: Dict[str, Any] = {}
        self.system_info: Dict[str, str] = {}
        self.is_rooted = self._check_root()
        self.scan_environment()
    
    def _detect_termux(self) -> bool:
        """Detect if running in Termux"""
        checks = [
            os.path.exists('/data/data/com.termux'),
            'TERMUX_VERSION' in os.environ,
            'TERMUX_APP_PID' in os.environ,
            shutil.which('termux-info') is not None,
            '/data/data/com.termux' in str(Path.home())
        ]
        return any(checks)
    
    def _check_root(self) -> bool:
        """Check if device is rooted"""
        try:
            result = subprocess.run(['su', '-c', 'echo', 'root'], 
                                  capture_output=True, text=True, timeout=2)
            return result.returncode == 0 and 'root' in result.stdout
        except:
            return False
    
    def scan_environment(self):
        """Scan current Termux environment"""
        self.system_info = {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'processor': platform.processor() or 'Unknown'
        }
        
        if not self.is_termux:
            return
        
        try:
            # Scan installed packages with better parsing
            result = subprocess.run(['pkg', 'list-installed'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if '/' in line:
                        pkg = line.split('/')[0].strip()
                        if pkg and not pkg.startswith('WARNING'):
                            self.installed_packages.add(pkg)
            else:
                # Alternative method
                try:
                    pkgs = subprocess.run(['apt', 'list', '--installed'], 
                                        capture_output=True, text=True, timeout=10)
                    for line in pkgs.stdout.split('\n')[1:]:
                        if '/' in line:
                            self.installed_packages.add(line.split('/')[0])
                except:
                    pass
        except:
            pass
        
        # Scan available editors
        editors = ['nano', 'vim', 'vi', 'micro', 'nvim', 'emacs', 'code', 'sublime']
        for editor in editors:
            if shutil.which(editor):
                self.available_editors.append(editor)
        
        # Scan Python packages
        try:
            result = subprocess.run([sys.executable, '-m', 'pip', 'list', '--format=freeze'],
                                  capture_output=True, text=True, timeout=15)
            for line in result.stdout.split('\n'):
                if line and '==' in line:
                    pkg_name = line.split('==')[0].lower()
                    self.python_packages.add(pkg_name)
        except:
            pass
        
        # Scan Node packages if npm exists
        if shutil.which('npm'):
            try:
                result = subprocess.run(['npm', 'list', '-g', '--depth=0', '--json'],
                                      capture_output=True, text=True, timeout=15)
                data = json.loads(result.stdout)
                deps = data.get('dependencies', {})
                self.node_packages = set(deps.keys())
            except:
                pass
    
    def ensure_package(self, pkg_name: str, pkg_type: str = 'pkg') -> bool:
        """Ensure a package is installed, install if missing"""
        if pkg_type == 'pkg' and pkg_name in self.installed_packages:
            return True
        if pkg_type == 'pip' and pkg_name.lower() in self.python_packages:
            return True
        if pkg_type == 'npm' and pkg_name in self.node_packages:
            return True
        
        # Installation logic would go here
        return False
    
    def get_context_summary(self) -> str:
        """Get summary of current environment for AI context"""
        ctx = []
        ctx.append(f"=== Termux Environment ===")
        ctx.append(f"Detected: {'✓ YES' if self.is_termux else '✗ NO'}")
        ctx.append(f"Rooted: {'✓ YES' if self.is_rooted else '✗ NO'}")
        ctx.append(f"Home: {self.home}")
        ctx.append(f"Storage: {self.storage}")
        ctx.append(f"System: {self.system_info['platform']}")
        ctx.append(f"Python: {self.system_info['python_version']}")
        ctx.append(f"\n=== Packages ===")
        ctx.append(f"System packages: {len(self.installed_packages)}")
        ctx.append(f"Python packages: {len(self.python_packages)}")
        ctx.append(f"Node packages: {len(self.node_packages)}")
        ctx.append(f"\n=== Tools ===")
        ctx.append(f"Editors: {', '.join(self.available_editors) or 'None (install nano)'}")
        ctx.append(f"\n=== Current Directory ===")
        ctx.append(f"Path: {os.getcwd()}")
        try:
            files = len(os.listdir('.'))
            ctx.append(f"Files: {files}")
        except:
            pass
        return "\n".join(ctx)


@dataclass
class VibeTask:
    """Represents a vibe coding task"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    detected_language: Optional[str] = None
    required_packages: List[Tuple[str, str]] = field(default_factory=list)  # (type, name)
    files_to_create: List[Tuple[str, str]] = field(default_factory=list)  # (path, content)
    commands_to_run: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def summary(self) -> str:
        lines = [f"[bold]Task {self.id}: {self.description}[/bold]"]
        if self.detected_language:
            lines.append(f"📝 Language: {self.detected_language}")
        if self.required_packages:
            lines.append(f"📦 Packages needed:")
            for pkg_type, pkg_name in self.required_packages:
                lines.append(f"  - {pkg_name} ({pkg_type})")
        if self.files_to_create:
            lines.append(f"📄 Files to create:")
            for filename, _ in self.files_to_create:
                lines.append(f"  - {filename}")
        if self.commands_to_run:
            lines.append(f"⚡ Commands to run:")
            for cmd in self.commands_to_run:
                lines.append(f"  $ {cmd}")
        return "\n".join(lines)


class CodeTemplates:
    """Collection of code templates for common tasks"""
    
    @staticmethod
    def get_template(name: str, **kwargs) -> str:
        templates = {
            'python_web_server': '''#!/usr/bin/env python3
"""
Simple Python Web Server
"""
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socket
import os

class CustomHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = '/index.html'
        return SimpleHTTPRequestHandler.do_GET(self)

def get_available_port(start_port=8080, max_port=9000):
    """Find an available port"""
    for port in range(start_port, max_port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    return start_port

def main():
    port = get_available_port(8080)
    server_address = ('0.0.0.0', port)
    
    print(f"Starting server on http://0.0.0.0:{port}")
    print(f"Local: http://localhost:{port}")
    print("Press Ctrl+C to stop")
    
    # Create default index.html if not exists
    if not os.path.exists('index.html'):
        with open('index.html', 'w') as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <title>Termux Server</title>
    <style>
        body { font-family: Arial; margin: 40px; }
        h1 { color: #333; }
    </style>
</head>
<body>
    <h1>🚀 Server Running!</h1>
    <p>Powered by Termux & Python</p>
</body>
</html>""")
    
    httpd = HTTPServer(server_address, CustomHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\\nServer stopped.")

if __name__ == '__main__':
    main()''',

            'bash_backup_script': '''#!/bin/bash
# Backup Script for Termux
# Created: $(date)

BACKUP_DIR="$HOME/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="backup_$TIMESTAMP.tar.gz"

# Colors for output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m' # No Color

echo -e "${YELLOW}📦 Starting backup...${NC}"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Files/directories to backup (customize this)
BACKUP_PATHS=(
    "$HOME/.termux"
    "$HOME/storage/shared/Documents"
    "$HOME/.bashrc"
    "$HOME/.bash_profile"
    "$HOME/.config"
)

echo -e "${YELLOW}Backing up:${NC}"
for path in "${BACKUP_PATHS[@]}"; do
    if [ -e "$path" ]; then
        echo "  ✓ $path"
    else
        echo -e "  ${RED}✗ $path (not found)${NC}"
    fi
done

# Create backup
echo -e "\\n${YELLOW}Creating archive...${NC}"
if tar -czf "$BACKUP_DIR/$BACKUP_NAME" "${BACKUP_PATHS[@]}" 2>/dev/null; then
    SIZE=$(du -h "$BACKUP_DIR/$BACKUP_NAME" | cut -f1)
    echo -e "${GREEN}✓ Backup created: $BACKUP_NAME ($SIZE)${NC}"
    
    # List recent backups
    echo -e "\\n${YELLOW}Recent backups:${NC}"
    ls -lh "$BACKUP_DIR"/*.tar.gz 2>/dev/null | tail -5
else
    echo -e "${RED}✗ Backup failed${NC}"
    exit 1
fi

echo -e "\\n${GREEN}✅ Backup completed successfully!${NC}"
echo "Location: $BACKUP_DIR/$BACKUP_NAME"''',

            'python_quick_script': '''#!/usr/bin/env python3
"""
Quick Python Script Template
"""
import sys
import os
from pathlib import Path

def main():
    print("🚀 Python Script Running!")
    print(f"Python: {sys.version}")
    print(f"Directory: {os.getcwd()}")
    print(f"Files here: {len(os.listdir('.'))}")
    
    # Your code here
    print("\\n✅ Done!")

if __name__ == '__main__':
    main()'''
        }
        
        template = templates.get(name)
        if template and kwargs:
            return template.format(**kwargs)
        return template or ""


class WebSearchTool:
    """Tool for AI to search web for current information"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def search_termux_package(self, query: str) -> str:
        """Search for Termux package information"""
        # In a real implementation, this would use actual web search
        # For now, provide helpful static info
        common_info = {
            'python': '• python - Python 3 interpreter\n• python-dev - Development headers\n• pip - Python package manager',
            'node': '• nodejs - Node.js JavaScript runtime\n• npm - Node package manager\n• yarn - Alternative package manager',
            'git': '• git - Version control system\n• gh - GitHub CLI tool',
            'editor': '• nano - Simple text editor\n• vim - Advanced text editor\n• micro - Modern terminal editor',
            'dev': '• clang - C/C++ compiler\n• make - Build automation\n• cmake - Cross-platform build system',
            'web': '• curl - Command line HTTP client\n• wget - File downloader\n• httpie - User-friendly HTTP client',
        }
        
        results = []
        for category, info in common_info.items():
            if query.lower() in category:
                results.append(f"📦 {category.upper()} PACKAGES:\n{info}")
        
        if results:
            return "\n\n".join(results)
        else:
            return f"💡 For '{query}', try: 'pkg search {query}' or check https://wiki.termux.com"


class ScreenReader:
    """Handles screen capture and AI vision analysis for Termux"""
    
    def __init__(self, console: Console, ai_client=None):
        self.console = console
        self.ai = ai_client
        self.screenshot_dir = Path('/sdcard/DCIM') if os.path.exists('/sdcard/DCIM') else Path.home() / 'screenshots'
        self.screenshot_dir.mkdir(exist_ok=True)
        self.last_screenshot: Optional[Path] = None
        self.is_rooted = self._check_root()
        
    def _check_root(self) -> bool:
        """Check if device has root access"""
        try:
            result = subprocess.run(['su', '-c', 'echo', 'root'], 
                                  capture_output=True, text=True, timeout=2)
            return result.returncode == 0
        except:
            return False
    
    def capture_screen(self, filename: Optional[str] = None) -> Optional[Path]:
        """
        Capture screen using available methods:
        1. screencap command (rooted devices)
        2. termux-api (if available)
        3. Terminal buffer capture (fallback)
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"termux_screen_{timestamp}.png"
        
        filepath = self.screenshot_dir / filename
        
        # Method 1: Try screencap (requires root)
        if self.is_rooted:
            try:
                result = subprocess.run(
                    ['su', '-c', f'/system/bin/screencap -p {filepath}'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0 and filepath.exists():
                    self.last_screenshot = filepath
                    return filepath
            except Exception as e:
                self.console.print(f"[yellow]Root screencap failed: {e}[/yellow]")
        
        # Method 2: Try termux-api screenshot
        if shutil.which('termux-camera-photo'):
            try:
                # Use camera as fallback (point at screen)
                result = subprocess.run(
                    ['termux-camera-photo', '-c', '0', str(filepath)],
                    capture_output=True, text=True, timeout=15
                )
                if result.returncode == 0 and filepath.exists():
                    self.last_screenshot = filepath
                    return filepath
            except:
                pass
        
        # Method 3: Capture terminal buffer (text-based)
        return self._capture_terminal_buffer(filepath)
    
    def _capture_terminal_buffer(self, filepath: Path) -> Optional[Path]:
        """Capture terminal content as text and convert to image"""
        try:
            # Get terminal size
            rows, cols = self._get_terminal_size()
            
            # Capture scrollback buffer using script or screen
            buffer_content = self._get_terminal_content()
            
            # Save as text first
            text_path = filepath.with_suffix('.txt')
            text_path.write_text(buffer_content, encoding='utf-8')
            
            # If PIL is available, create an image representation
            if PIL_AVAILABLE:
                return self._text_to_image(buffer_content, filepath)
            else:
                # Return text file path
                self.console.print("[yellow]PIL not available. Saving as text.[/yellow]")
                return text_path
                
        except Exception as e:
            self.console.print(f"[red]Terminal buffer capture failed: {e}[/red]")
            return None
    
    def _get_terminal_size(self) -> Tuple[int, int]:
        """Get current terminal dimensions"""
        try:
            import fcntl
            import termios
            import struct
            
            # Get terminal size
            h, w, hp, wp = struct.unpack('HHHH',
                fcntl.ioctl(0, termios.TIOCGWINSZ,
                struct.pack('HHHH', 0, 0, 0, 0)))
            return h, w
        except:
            return 24, 80  # Default fallback
    
    def _get_terminal_content(self) -> str:
        """Get current terminal screen content"""
        content = []
        
        # Try to get scrollback from screen/tmux if available
        if os.environ.get('TMUX'):
            try:
                result = subprocess.run(['tmux', 'capture-pane', '-p'],
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return result.stdout
            except:
                pass
        
        # Try screen
        if os.environ.get('STY'):
            try:
                result = subprocess.run(['screen', '-X', 'hardcopy', '-h', '/tmp/screen_capture.txt'],
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return Path('/tmp/screen_capture.txt').read_text()
            except:
                pass
        
        # Fallback: Get last commands from history and current directory listing
        content.append(f"=== Terminal Capture at {datetime.now()} ===\n")
        content.append(f"Directory: {os.getcwd()}\n")
        content.append(f"User: {os.getenv('USER', 'unknown')}\n")
        content.append(f"=== Recent Commands ===\n")
        
        # Get command history
        try:
            histfile = Path.home() / ".termux_ai_history"
            if histfile.exists():
                history = histfile.read_text().split('\n')[-20:]
                content.append('\n'.join(history))
        except:
            pass
        
        content.append(f"\n=== Current Directory Files ===\n")
        try:
            files = os.listdir('.')
            content.append('\n'.join(files[:30]))
        except:
            pass
        
        return ''.join(content)
    
    def _text_to_image(self, text: str, output_path: Path) -> Path:
        """Convert text to image representation"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create image with terminal-like appearance
            lines = text.split('\n')[:50]  # Limit to 50 lines
            line_height = 16
            padding = 20
            
            img_width = 800
            img_height = min(len(lines) * line_height + 2 * padding, 1200)
            
            # Create image with dark background (terminal style)
            img = Image.new('RGB', (img_width, img_height), color=(30, 30, 30))
            draw = ImageDraw.Draw(img)
            
            # Try to load a monospace font, fallback to default
            try:
                font = ImageFont.truetype("/system/fonts/DroidSansMono.ttf", 14)
            except:
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 14)
                except:
                    font = ImageFont.load_default()
            
            # Draw text
            y = padding
            for line in lines:
                # Truncate long lines
                if len(line) > 100:
                    line = line[:97] + "..."
                draw.text((padding, y), line, fill=(200, 200, 200), font=font)
                y += line_height
            
            # Save image
            img.save(output_path)
            return output_path
            
        except Exception as e:
            self.console.print(f"[red]Text to image conversion failed: {e}[/red]")
            # Fallback to text file
            text_path = output_path.with_suffix('.txt')
            text_path.write_text(text, encoding='utf-8')
            return text_path
    
    def analyze_with_ai(self, image_path: Path, query: str = "Describe what you see on this screen") -> str:
        """Send captured screen to AI for analysis"""
        if not self.ai:
            return "AI client not available"
        
        try:
            # Read image and encode to base64
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Determine MIME type
            mime_type = "image/png" if image_path.suffix == '.png' else "image/jpeg"
            if image_path.suffix == '.txt':
                # For text files, just read the content
                content = image_path.read_text()
                return self._analyze_text_with_ai(content, query)
            
            # Call AI vision API
            response = self.ai.chat.completions.create(
                model="llama-3.3-70b-versatile",  # Vision-capable model
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": query},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error analyzing screen: {e}"
    
    def _analyze_text_with_ai(self, content: str, query: str) -> str:
        """Analyze text content with AI"""
        try:
            response = self.ai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are analyzing terminal screen content."},
                    {"role": "user", "content": f"{query}\n\nScreen content:\n{content[:4000]}"}
                ],
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error analyzing text: {e}"
    
    def get_last_screenshot_info(self) -> str:
        """Get information about last screenshot"""
        if not self.last_screenshot or not self.last_screenshot.exists():
            return "No screenshot available"
        
        try:
            stat = self.last_screenshot.stat()
            size = stat.st_size
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            return f"Screenshot: {self.last_screenshot.name}\nSize: {size} bytes\nTime: {mtime}"
        except:
            return "Screenshot info unavailable"


class VibeCoder:
    """Handles natural language coding requests"""
    
    def __init__(self, console: Console, termux: TermuxContext, ai_client=None):
        self.console = console
        self.termux = termux
        self.ai = ai_client
        self.web = WebSearchTool()
        self.templates = CodeTemplates()
        self.project_history: List[VibeTask] = []
    
    def process_request(self, description: str) -> VibeTask:
        """Process a natural language coding request"""
        task = VibeTask(description=description)
        
        # Detect language from description
        desc_lower = description.lower()
        lang_patterns = {
            'python': ['python', 'django', 'flask', 'script', '.py', 'automation', 'data'],
            'javascript': ['javascript', 'node', 'js ', 'express', 'react', 'website'],
            'typescript': ['typescript', 'ts ', 'angular'],
            'bash': ['bash', 'shell', '.sh', 'script', 'automate', 'backup'],
            'html': ['html', 'website', 'web page', 'landing'],
            'go': ['golang', 'go ', 'go program'],
            'rust': ['rust', 'cargo', 'rust program'],
            'c': ['c program', 'c ', 'c code'],
            'cpp': ['c++', 'cpp', 'c plus'],
        }
        
        for lang, patterns in lang_patterns.items():
            if any(pattern in desc_lower for pattern in patterns):
                task.detected_language = lang
                break
        
        # Check for template matches
        if 'web server' in desc_lower and task.detected_language == 'python':
            template = self.templates.get_template('python_web_server')
            task.files_to_create.append(('server.py', template))
            task.commands_to_run.append('python server.py')
            task.required_packages.append(('pkg', 'python'))
            
        elif 'backup' in desc_lower and task.detected_language == 'bash':
            template = self.templates.get_template('bash_backup_script')
            task.files_to_create.append(('backup.sh', template))
            task.commands_to_run.append('chmod +x backup.sh')
            task.commands_to_run.append('./backup.sh')
            
        elif 'quick script' in desc_lower and task.detected_language == 'python':
            template = self.templates.get_template('python_quick_script')
            task.files_to_create.append(('script.py', template))
            task.commands_to_run.append('chmod +x script.py')
            task.commands_to_run.append('./script.py')
        
        # Add common packages based on language
        if task.detected_language == 'python':
            task.required_packages.append(('pkg', 'python'))
            if 'web' in desc_lower or 'server' in desc_lower:
                task.required_packages.append(('pip', 'flask'))
                
        elif task.detected_language == 'javascript':
            task.required_packages.append(('pkg', 'nodejs'))
            
        elif task.detected_language == 'bash':
            # Bash is usually available
            pass
        
        # Ensure an editor is available
        if not self.termux.available_editors:
            task.required_packages.append(('pkg', 'nano'))
        
        self.project_history.append(task)
        return task
    
    def execute_task(self, task: VibeTask, auto_confirm: bool = False) -> bool:
        """Execute a vibe coding task"""
        self.console.print(Panel.fit(
            Text(task.summary(), style="cyan"),
            title="🎯 Vibe Coding Plan",
            border_style="cyan"
        ))
        
        if not auto_confirm:
            if not Confirm.ask("🚀 Proceed with this plan?", default=True):
                return False
        
        # Install missing packages
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            install_task = progress.add_task("[yellow]Checking packages...", total=len(task.required_packages))
            
            for pkg_type, pkg_name in task.required_packages:
                progress.update(install_task, description=f"[yellow]Checking {pkg_name}...")
                
                if pkg_type == 'pkg' and pkg_name not in self.termux.installed_packages:
                    progress.update(install_task, description=f"[green]Installing {pkg_name}...")
                    result = subprocess.run(['pkg', 'install', '-y', pkg_name],
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        self.termux.installed_packages.add(pkg_name)
                        progress.update(install_task, advance=1)
                    else:
                        self.console.print(f"[red]Failed to install {pkg_name}[/red]")
                        if Confirm.ask("Continue anyway?"):
                            progress.update(install_task, advance=1)
                            continue
                        return False
                elif pkg_type == 'pip' and pkg_name.lower() not in self.termux.python_packages:
                    progress.update(install_task, description=f"[green]Installing {pkg_name}...")
                    subprocess.run([sys.executable, '-m', 'pip', 'install', pkg_name])
                    self.termux.python_packages.add(pkg_name.lower())
                    progress.update(install_task, advance=1)
                else:
                    progress.update(install_task, advance=1)
        
        # Create files
        for filepath, content in task.files_to_create:
            full_path = Path(filepath)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                full_path.write_text(content, encoding='utf-8')
                self.console.print(f"[green]✓ Created: {filepath}[/green]")
                
                # Make executable if it's a script
                if filepath.endswith(('.sh', '.py')):
                    full_path.chmod(0o755)
                    self.console.print(f"  [dim]Made executable[/dim]")
                    
            except Exception as e:
                self.console.print(f"[red]Failed to create {filepath}: {e}[/red]")
                return False
        
        # Run commands
        if task.commands_to_run:
            self.console.print("\n[cyan]⚡ Running commands:[/cyan]")
            for cmd in task.commands_to_run:
                self.console.print(f"  $ [yellow]{cmd}[/yellow]")
                if not Confirm.ask("Run this command?", default=True):
                    continue
                
                try:
                    result = subprocess.run(cmd, shell=True, check=False)
                    if result.returncode != 0:
                        self.console.print(f"[yellow]Command returned non-zero: {result.returncode}[/yellow]")
                except Exception as e:
                    self.console.print(f"[red]Error: {e}[/red]")
        
        return True
    
    def generate_code_with_ai(self, description: str, language: Optional[str] = None) -> Tuple[str, str]:
        """Use AI to generate code based on description"""
        if not self.ai:
            # Fallback to templates or simple generation
            if language == 'python':
                return "ai_generated.py", self.templates.get_template('python_quick_script')
            return "", "AI not available"
        
        # Try multiple models
        models_to_try = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "gpt-3.5-turbo",
            "gpt-4"
        ]
        
        lang_hint = f" in {language}" if language else ""
        
        prompt = f"""Generate {lang_hint} code for: {description}

IMPORTANT REQUIREMENTS:
1. Provide COMPLETE, WORKING code only
2. NO markdown formatting (no ``` ```)
3. Include necessary imports
4. Add helpful comments
5. For web servers: use host='0.0.0.0' and dynamic port finding
6. Termux-compatible (Android/Linux)
7. Handle errors gracefully
8. Include a main() function if applicable

Code:"""
        
        for model in models_to_try:
            try:
                response = self.ai.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You generate clean, working code. No explanations, just code with comments."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000
                )
                
                code = response.choices[0].message.content.strip()
                
                # Clean markdown if present
                code = re.sub(r'^```[\w\s]*\n', '', code)
                code = re.sub(r'\n```$', '', code)
                code = re.sub(r'^\s*Here(?:[\'"]?s)?.*code:?\s*\n', '', code, flags=re.IGNORECASE)
                
                # Generate filename
                if language:
                    ext_map = {
                        'python': 'py', 'javascript': 'js', 'typescript': 'ts',
                        'go': 'go', 'rust': 'rs', 'c': 'c', 'cpp': 'cpp',
                        'bash': 'sh', 'html': 'html', 'css': 'css'
                    }
                    ext = ext_map.get(language, 'txt')
                else:
                    ext = 'txt'
                
                # Create safe filename
                words = re.findall(r'\w+', description.lower()[:50])
                base_name = '_'.join(words[:3]) or 'code'
                filename = f"{base_name}.{ext}"
                
                return filename, code
                
            except Exception as e:
                self.console.print(f"[yellow]Model {model} failed: {e}[/yellow]")
                continue
        
        return "", "All AI models failed"


class TermuxOrchestrator:
    """Main orchestrator with full Termux and vibe coding support"""
    
    def __init__(self):
        self.console = Console()
        self.termux = TermuxContext()
        self.history = deque(maxlen=100)
        self.vibe_coder = None
        self.ai_client = self._init_ai_client()
        self.ai_enabled = self.ai_client is not None
        self.screen_reader: Optional[ScreenReader] = None
        
        if self.ai_enabled:
            self.vibe_coder = VibeCoder(self.console, self.termux, self.ai_client)
            self.screen_reader = ScreenReader(self.console, self.ai_client)
        else:
            self.vibe_coder = VibeCoder(self.console, self.termux)
            self.screen_reader = ScreenReader(self.console)
        
        # Built-in commands
        self.builtins = {
            'vibe': self.cmd_vibe,
            'code': self.cmd_vibe,
            'make': self.cmd_vibe,
            'create': self.cmd_vibe,
            'pkg': self.cmd_pkg,
            'apt': self.cmd_pkg,
            'tools': self.cmd_tools,
            'ai': self.cmd_ai,
            'ask': self.cmd_ai,
            'search': self.cmd_search,
            'web': self.cmd_web,
            'files': self.cmd_files,
            'edit': self.cmd_edit,
            'paste': self.cmd_paste,
            'cat': self.cmd_cat,
            'view': self.cmd_cat,
            'cd': self.cmd_cd,
            'ls': lambda _: self._run_external('ls -la --color=auto'),
            'll': lambda _: self._run_external('ls -la --color=auto'),
            'history': self.cmd_history,
            'clear': self.cmd_clear,
            'help': self.cmd_help,
            'exit': self.cmd_exit,
            'quit': self.cmd_exit,
            'pwd': lambda _: self.console.print(f"📁 {os.getcwd()}"),
            'stats': self.cmd_stats,
            'context': self.cmd_context,
            'update': self.cmd_update,
            'projects': self.cmd_projects,
            'look': self.cmd_look,
            'see': self.cmd_look,
            'screen': self.cmd_look,
        }
        
        self.aliases = {
            'v': 'vibe',
            'c': 'code',
            '?': 'help',
            'h': 'help',
            'q': 'exit',
            'cls': 'clear',
            '..': 'cd ..',
        }
        
        self._setup_readline()
        atexit.register(self.cleanup)
    
    def _init_ai_client(self):
        """Initialize AI client with multiple API key sources"""
        api_keys = {
            'GROQ_API_KEY': "https://api.groq.com/openai/v1",
            'OPENAI_API_KEY': "https://api.openai.com/v1",
            'ANTHROPIC_API_KEY': None,  # Would need different client
            'LOCALAI_BASE': "http://localhost:8080/v1",
        }
        
        for env_var, base_url in api_keys.items():
            api_key = os.getenv(env_var)
            if api_key:
                try:
                    if env_var == 'LOCALAI_BASE':
                        client = openai.OpenAI(
                            base_url=base_url,
                            api_key="not-needed"
                        )
                    else:
                        client = openai.OpenAI(
                            api_key=api_key.strip(),
                            base_url=base_url if base_url else None
                        )
                    
                    # Test connection
                    client.models.list()
                    self.console.print(f"[green]✓ Connected to {env_var}[/green]")
                    return client
                except Exception as e:
                    self.console.print(f"[yellow]Failed {env_var}: {e}[/yellow]")
        
        self.console.print("[yellow]⚠ No AI API key found. Set GROQ_API_KEY or OPENAI_API_KEY[/yellow]")
        return None
    
    def _setup_readline(self):
        """Setup readline with better completion"""
        try:
            histfile = self.termux.home / ".termux_ai_history"
            try:
                readline.read_history_file(str(histfile))
                readline.set_history_length(1000)
            except FileNotFoundError:
                pass
            
            readline.set_completer(self._completer)
            readline.parse_and_bind("tab: complete")
            
            # Improve completion
            readline.parse_and_bind('set show-all-if-ambiguous on')
            readline.parse_and_bind('set completion-ignore-case on')
            
            def save_history():
                try:
                    readline.write_history_file(str(histfile))
                except:
                    pass
            atexit.register(save_history)
        except ImportError:
            pass
    
    def _completer(self, text, state):
        """Tab completion with categories"""
        options = []
        
        # Commands
        for cmd in list(self.builtins.keys()) + list(self.aliases.keys()):
            if cmd.startswith(text):
                options.append(cmd)
        
        # Packages
        for pkg in self.termux.installed_packages:
            if pkg.startswith(text):
                options.append(pkg)
        
        # Files
        try:
            for f in os.listdir('.'):
                if f.startswith(text):
                    options.append(f)
        except:
            pass
        
        if state < len(options):
            return options[state]
        return None
    
    def banner(self):
        """Display enhanced banner"""
        termux_status = "✓ Termux" if self.termux.is_termux else "✗ Termux"
        ai_status = "✓ AI" if self.ai_enabled else "✗ AI"
        editor = self.termux.available_editors[0] if self.termux.available_editors else "no-editor"
        vision_status = "✓ Vision" if self.screen_reader and (self.screen_reader.is_rooted or PIL_AVAILABLE) else "✗ Vision"
        
        banner_text = f"""[bold cyan]
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   ████████╗███████╗██████╗ ███╗   ███╗██╗   ██╗██╗  ██╗          ║
║   ╚══██╔══╝██╔════╝██╔══██╗████╗ ████║██║   ██║╚██╗██╔╝          ║
║      ██║   █████╗  ██████╔╝██╔████╔██║██║   ██║ ╚███╔╝           ║
║      ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║██║   ██║ ██╔██╗           ║
║      ██║   ███████╗██║  ██║██║ ╚═╝ ██║╚██████╔╝██╔╝ ██╗          ║
║      ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝          ║
║                                                                  ║
║           AI ORCHESTRATOR v7.2.1.1 - With AI Vision                  ║
╚══════════════════════════════════════════════════════════════════╝
[/bold cyan]
[dim]{termux_status} | {ai_status} | {vision_status} | {len(self.termux.installed_packages)} pkgs | {editor}[/dim]

[bold green]Examples:[/bold green]
  [cyan]vibe[/cyan] "create a python web server on port 8080"
  [cyan]look[/cyan] "What do you see on my screen?"
  [cyan]see[/cyan] "Explain this error message"
  [cyan]ai[/cyan] "how to install packages in termux"
        """
        self.console.print(banner_text)
    
    def run(self):
        """Main loop"""
        self.cmd_clear(None)
        
        while True:
            try:
                self._prompt_loop()
            except KeyboardInterrupt:
                self.console.print("\n[yellow]^C - Use 'exit' to quit[/yellow]")
            except EOFError:
                break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
                import traceback
                traceback.print_exc()
    
    def _prompt_loop(self):
        """Handle input with enhanced prompt"""
        try:
            cwd = os.getcwd().replace(str(self.termux.home), '~')
            if len(cwd) > 30:
                cwd = "..." + cwd[-27:]
            
            user = os.getenv('USER', 'user')
            hostname = os.getenv('HOSTNAME', 'termux')
            
            # Git branch if available
            git_branch = ""
            if shutil.which('git'):
                try:
                    result = subprocess.run(['git', 'branch', '--show-current'],
                                          capture_output=True, text=True, timeout=2)
                    if result.stdout.strip():
                        git_branch = f"[magenta] git:({result.stdout.strip()})[/magenta]"
                except:
                    pass
            
            prompt_line = f"[bold green]{user}@{hostname}[/bold green]:[bold blue]{cwd}[/bold blue]{git_branch}"
            if self.ai_enabled:
                prompt_line += "[yellow] ⚡[/yellow]"
            
            cmd = self.console.input(f"{prompt_line} $ ").strip()
            if not cmd:
                return
            
            # Handle special aliases
            if cmd in ['..', '../']:
                self.cmd_cd('cd ..')
                return
            
            # Handle other aliases
            if cmd in self.aliases:
                if cmd in ['..']:
                    self.cmd_cd('cd ..')
                    return
                cmd = self.aliases[cmd]
            
            parts = cmd.split(maxsplit=1)
            base_cmd = parts[0]
            args = parts[1] if len(parts) > 1 else ""
            
            # Check builtins
            if base_cmd in self.builtins:
                self.builtins[base_cmd](cmd if args else base_cmd)
                return
            
            # External command
            self.history.append(cmd)
            self._run_external(cmd, capture=False)
            
        except KeyboardInterrupt:
            raise
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def _run_external(self, cmd: str, capture: bool = True) -> Tuple[int, str]:
        """Run external command with better handling"""
        try:
            if capture:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
                if result.stdout:
                    self.console.print(result.stdout.rstrip())
                if result.stderr:
                    self.console.print(f"[yellow]{result.stderr.rstrip()}[/yellow]")
                return result.returncode, result.stdout
            else:
                # Interactive mode - use system for proper tty
                returncode = os.system(cmd)
                return returncode >> 8, ""
        except subprocess.TimeoutExpired:
            self.console.print("[red]Command timed out after 60 seconds[/red]")
            return 1, ""
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
            return 1, str(e)
    
    # ==================== AI SCREEN READING ====================
    
    def cmd_look(self, args: str):
        """AI screen reading - capture and analyze screen"""
        if not self.screen_reader:
            self.console.print("[red]❌ Screen reader not available[/red]")
            return
        
        # Extract query from args
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            query = "Describe what you see on this screen in detail"
        else:
            query = parts[1]
        
        self.console.print("[bold cyan]📸 Capturing screen...[/bold cyan]")
        
        # Capture screen
        with self.console.status("[bold green]Taking screenshot...[/bold green]"):
            screenshot_path = self.screen_reader.capture_screen()
        
        if not screenshot_path:
            self.console.print("[red]❌ Failed to capture screen[/red]")
            self.console.print("[yellow]Tips:[/yellow]")
            self.console.print("  • For full screen capture, root access is required")
            self.console.print("  • Terminal buffer capture works without root")
            return
        
        # Show capture info
        info = self.screen_reader.get_last_screenshot_info()
        self.console.print(Panel(info, title="📸 Screenshot Info", border_style="green"))
        
        # Analyze with AI if available
        if self.ai_enabled:
            self.console.print(f"[cyan]🤔 Asking AI: {query}...[/cyan]")
            
            with self.console.status("[bold cyan]AI is analyzing...[/bold cyan]"):
                analysis = self.screen_reader.analyze_with_ai(screenshot_path, query)
            
            self.console.print(Panel(
                Markdown(analysis),
                title="🤖 AI Vision Analysis",
                border_style="cyan",
                padding=(1, 2)
            ))
        else:
            self.console.print("[yellow]⚠ AI not available. Screenshot saved but not analyzed.[/yellow]")
            self.console.print(f"[dim]Location: {screenshot_path}[/dim]")

    def cmd_search(self, args: str):
        """Search for Termux packages and web information"""
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            self.console.print("[cyan]🔍 Search for packages, commands, or info[/cyan]")
            self.console.print("[dim]Examples:[/dim]")
            self.console.print("  • 'search python packages'")
            self.console.print("  • 'search how to install git'")
            self.console.print("  • 'search web server tutorial'")
            query = self.console.input("\n[cyan]Search: [/cyan]").strip()
        else:
            query = parts[1]
        
        if not query:
            return
        
        # First try package search
        if any(word in query.lower() for word in ['package', 'pkg', 'install', 'apt']):
            self.console.print(f"[cyan]🔍 Searching packages for: {query}[/cyan]")
            result = subprocess.run(['pkg', 'search', query], 
                                  capture_output=True, text=True, timeout=15)
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    table = Table(title=f"📦 Package Search Results", border_style="blue")
                    table.add_column("Package", style="cyan")
                    table.add_column("Description", style="dim")
                    
                    for line in lines[:15]:  # Limit results
                        if '/' in line:
                            pkg, desc = line.split('/', 1)
                            table.add_row(pkg.strip(), desc.strip()[:80])
                    
                    self.console.print(table)
                    if len(lines) > 15:
                        self.console.print(f"[dim]... and {len(lines)-15} more results[/dim]")
                    return
        
        # If AI is available, use it for broader search
        if self.ai_enabled:
            self.console.print(f"[cyan]🔍 Searching with AI: {query}[/cyan]")
            
            # Build context for better AI search
            context = self.termux.get_context_summary()
            prompt = f"""User is searching for: {query}
            
Current environment:
{context}

Provide helpful information about this topic in Termux/Android context.
If it's about packages, mention specific package names.
If it's about commands, provide examples.
Be concise and practical."""
            
            try:
                with self.console.status("[bold cyan]🤔 Searching...[/bold cyan]"):
                    response = self.ai_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": "You are a Termux/Android terminal expert helping users find information."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                        max_tokens=800
                    )
                    
                    answer = response.choices[0].message.content.strip()
                    
                    self.console.print(Panel(
                        Markdown(answer),
                        title=f"🔍 Search Results: {query}",
                        border_style="cyan",
                        padding=(1, 2)
                    ))
                    
            except Exception as e:
                self.console.print(f"[red]❌ Search error: {e}[/red]")
                # Fallback to web tool
                result = self.vibe_coder.web.search_termux_package(query)
                self.console.print(Panel(result, title=f"Search: {query}", border_style="blue"))
        else:
            # Use web search tool as fallback
            result = self.vibe_coder.web.search_termux_package(query)
            self.console.print(Panel(result, title=f"Search: {query}", border_style="blue"))
        
        # Also show relevant commands
        self.console.print("[cyan]💡 Related commands:[/cyan]")
        if 'install' in query.lower():
            self.console.print("  [dim]pkg install <package>[/dim] - Install a package")
        if 'web' in query.lower() or 'server' in query.lower():
            self.console.print("  [dim]vibe 'create web server'[/dim] - Generate web server code")    

    # ==================== VIBE CODING ====================
    
    def cmd_vibe(self, args: str):
        """Vibe coding - natural language to working code"""
        # Extract description
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            self.console.print("[bold cyan]💡 Vibe Coding - Turn ideas into code[/bold cyan]")
            self.console.print("[dim]Examples:[/dim]")
            self.console.print("  • 'create a python web server'")
            self.console.print("  • 'make a bash backup script'")
            self.console.print("  • 'javascript countdown timer'")
            self.console.print("  • 'python todo list app'")
            description = self.console.input("\n[cyan]What do you want to build? [/cyan]").strip()
        else:
            description = parts[1]
        
        if not description:
            return
        
        # Check if we should use AI or templates
        use_ai = self.ai_enabled and len(description) > 10
        if use_ai:
            self.console.print("[dim]Using AI code generation...[/dim]")
        
        # Process the request
        with self.console.status("[bold cyan]Analyzing your request...[/bold cyan]"):
            task = self.vibe_coder.process_request(description)
            
            if use_ai and not task.files_to_create:
                # Generate code with AI
                filename, code = self.vibe_coder.generate_code_with_ai(
                    description, task.detected_language
                )
                
                if code and "AI not available" not in code:
                    task.files_to_create.append((filename, code))
                    self.console.print(f"[green]✓ AI generated {filename}[/green]")
                else:
                    self.console.print("[yellow]Using template instead[/yellow]")
                    # Fallback to quick script
                    if task.detected_language == 'python':
                        task.files_to_create.append(('app.py', self.vibe_coder.templates.get_template('python_quick_script')))
        
        if not task.files_to_create:
            self.console.print("[red]Could not generate code for this request[/red]")
            return
        
        # Show preview
        for filename, content in task.files_to_create:
            if len(content) < 1000:  # Only show preview for reasonable sizes
                try:
                    ext = Path(filename).suffix[1:] or 'text'
                    syntax = Syntax(content, ext, theme="monokai", line_numbers=True, word_wrap=True)
                    self.console.print(Panel(syntax, title=f"📄 {filename}", border_style="green"))
                except:
                    self.console.print(Panel(content[:500] + ("..." if len(content) > 500 else ""), 
                                           title=f"📄 {filename}", border_style="green"))
        
        # Execute task
        if self.vibe_coder.execute_task(task, auto_confirm=False):
            self.console.print(f"\n[bold green]✅ Project created successfully![/bold green]")
            
            # Show next steps
            for filename, _ in task.files_to_create:
                full_path = os.path.abspath(filename)
                self.console.print(f"  📍 [dim]{full_path}[/dim]")
                
                # Suggest actions based on file type
                if filename.endswith('.py'):
                    self.console.print(f"  [cyan]Run it:[/cyan] [dim]python {filename}[/dim]")
                    if not self.termux.available_editors:
                        self.console.print(f"  [cyan]Edit it:[/cyan] [dim]nano {filename}[/dim]")
                elif filename.endswith('.sh'):
                    self.console.print(f"  [cyan]Run it:[/cyan] [dim]bash {filename}[/dim] or [dim]./{filename}[/dim]")
    
    # ==================== PACKAGE MANAGEMENT ====================
    
    def cmd_pkg(self, args: str):
        """Enhanced package management"""
        parts = args.split()
        if len(parts) < 2:
            # Show installed packages with categories
            table = Table(title=f"📦 Installed Packages ({len(self.termux.installed_packages)})", 
                         border_style="blue")
            table.add_column("Package", style="cyan", no_wrap=True)
            table.add_column("Type", style="dim")
            table.add_column("Status", style="green")
            
            categories = {
                'dev': ['python', 'nodejs', 'clang', 'golang', 'rust', 'make'],
                'editor': ['nano', 'vim', 'micro', 'neovim'],
                'tools': ['git', 'curl', 'wget', 'tmux', 'htop'],
                'lang': ['python', 'nodejs', 'ruby', 'php'],
            }
            
            sorted_pkgs = sorted(self.termux.installed_packages)
            for pkg in sorted_pkgs[:25]:  # Limit display
                pkg_type = "other"
                for cat, pkgs in categories.items():
                    if pkg in pkgs:
                        pkg_type = cat
                        break
                table.add_row(pkg, pkg_type, "installed")
            
            if len(sorted_pkgs) > 25:
                table.add_row(f"... and {len(sorted_pkgs)-25} more", "", "")
            
            self.console.print(table)
            self.console.print("[dim]Usage: pkg install|search|remove <name>[/dim]")
            return
        
        subcmd = parts[1]
        
        if subcmd == 'search' and len(parts) > 2:
            term = parts[2]
            self.console.print(f"[cyan]🔍 Searching for '{term}'...[/cyan]")
            result = subprocess.run(['pkg', 'search', term], capture_output=True, text=True)
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines[:15]:
                    if '/' in line:
                        pkg, desc = line.split('/', 1)
                        self.console.print(f"  [green]{pkg.strip()}[/green] - [dim]{desc.strip()}[/dim]")
                if len(lines) > 15:
                    self.console.print(f"  [dim]... and {len(lines)-15} more[/dim]")
            else:
                self.console.print(result.stderr)
                
        elif subcmd == 'install' and len(parts) > 2:
            pkg = parts[2]
            self.console.print(f"[yellow]📦 Installing {pkg}...[/yellow]")
            result = subprocess.run(['pkg', 'install', '-y', pkg], capture_output=True, text=True)
            if result.returncode == 0:
                self.termux.installed_packages.add(pkg)
                self.console.print(f"[green]✅ {pkg} installed successfully[/green]")
                # Rescan environment
                self.termux.scan_environment()
            else:
                self.console.print(f"[red]❌ Failed to install {pkg}[/red]")
                self.console.print(f"[dim]{result.stderr}[/dim]")
                
        elif subcmd == 'remove' and len(parts) > 2:
            pkg = parts[2]
            if Confirm.ask(f"[yellow]Remove package {pkg}?[/yellow]"):
                subprocess.run(['pkg', 'remove', '-y', pkg])
                self.termux.installed_packages.discard(pkg)
                
        elif subcmd == 'update':
            self.console.print("[yellow]🔄 Updating package lists...[/yellow]")
            subprocess.run(['pkg', 'update'])
            self.termux.scan_environment()
        else:
            # Pass through to pkg
            os.system(f"pkg {' '.join(parts[1:])}")
    
    # ==================== AI COMMANDS ====================
    
    def cmd_ai(self, args: str):
        """AI chat with Termux context"""
        if not self.ai_enabled:
            self.console.print("[red]❌ AI not available[/red]")
            self.console.print("[yellow]Set GROQ_API_KEY or OPENAI_API_KEY environment variable[/yellow]")
            return
        
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            self.console.print("[bold cyan]💭 AI Assistant - Ask me anything about Termux[/bold cyan]")
            self.console.print("[dim]Examples:[/dim]")
            self.console.print("  • 'how to set up git in termux'")
            self.console.print("  • 'python web server example'")
            self.console.print("  • 'best practices for termux scripts'")
            query = self.console.input("\n[cyan]Your question: [/cyan]").strip()
        else:
            query = parts[1]
        
        if not query:
            return
        
        # Build context-aware prompt
        context = self.termux.get_context_summary()
        full_prompt = f"""You are a Termux/Android terminal expert. Help the user with their question.

CURRENT ENVIRONMENT:
{context}

USER QUESTION: {query}

Provide a helpful, accurate answer. If suggesting commands, make sure they work in Termux/Android environment.
If code is requested, provide complete working code with comments.
Be concise but thorough."""
        
        try:
            with self.console.status("[bold cyan]🤔 Thinking...[/bold cyan]"):
                response = self.ai_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "You are an expert in Termux, Android development, Linux command line, and programming."},
                        {"role": "user", "content": full_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1200
                )
                
                answer = response.choices[0].message.content.strip()
                
                # Format the response
                self.console.print(Panel(
                    Markdown(answer),
                    title="🤖 AI Response",
                    border_style="cyan",
                    padding=(1, 2)
                ))
                
        except Exception as e:
            self.console.print(f"[red]❌ AI error: {e}[/red]")
    
    def cmd_web(self, args: str):
        """Web search for Termux info"""
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            query = self.console.input("[cyan]🔍 Search web for: [/cyan]").strip()
        else:
            query = parts[1]
        
        if not query:
            return
        
        # Use web search tool
        result = self.vibe_coder.web.search_termux_package(query)
        self.console.print(Panel(result, title=f"Web Search: {query}", border_style="blue"))
    
    # ==================== FILE OPERATIONS ====================
    
    def cmd_files(self, args: str):
        """Show file tree of current directory"""
        show_all = '-a' in args
        
        try:
            items = sorted(os.listdir('.'))
            
            tree = Tree(f"📁 [bold]{os.getcwd()}[/bold]")
            
            # Count by type
            dirs = []
            files = []
            
            for item in items:
                if not show_all and item.startswith('.'):
                    continue
                    
                path = Path(item)
                try:
                    if path.is_dir():
                        dirs.append(item)
                    else:
                        files.append(item)
                except PermissionError:
                    files.append(f"{item} [red][Permission denied][/red]")
            
            # Add directories first
            if dirs:
                dir_branch = tree.add("📂 [cyan]Directories[/cyan]")
                for d in sorted(dirs)[:20]:
                    try:
                        count = len(os.listdir(d))
                        dir_branch.add(f"📂 {d} [dim]({count} items)[/dim]")
                    except:
                        dir_branch.add(f"📂 {d} [red][error][/red]")
            
            # Add files
            if files:
                file_branch = tree.add("📄 [cyan]Files[/cyan]")
                for f in sorted(files)[:30]:
                    try:
                        size = Path(f).stat().st_size
                        size_str = self._format_size(size)
                        file_branch.add(f"📄 {f} [dim]({size_str})[/dim]")
                    except:
                        file_branch.add(f"📄 {f}")
            
            self.console.print(tree)
            
            # Show summary
            total = len(items)
            visible = len(dirs) + len(files)
            if not show_all and total > visible:
                self.console.print(f"[dim]{total - visible} hidden files/directories (use -a to show all)[/dim]")
                
        except PermissionError:
            self.console.print("[red]Permission denied to list directory[/red]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    def _format_size(self, size_bytes):
        """Format size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f}TB"
    
    def cmd_edit(self, args: str):
        """Edit file with best available editor"""
        parts = args.split()
        if len(parts) < 2:
            self.console.print("[red]❌ Usage: edit <filename>[/red]")
            return
        
        filename = parts[1]
        
        # Choose editor
        if len(parts) > 2 and parts[2] in self.termux.available_editors:
            editor = parts[2]
        else:
            editor = self.termux.available_editors[0] if self.termux.available_editors else 'nano'
        
        # Ensure file exists
        if not os.path.exists(filename):
            if Confirm.ask(f"[yellow]📝 Create new file '{filename}'?[/yellow]"):
                Path(filename).touch()
                self.console.print(f"[green]✓ Created {filename}[/green]")
            else:
                return
        
        self.console.print(f"[cyan]📝 Opening {filename} with {editor}...[/cyan]")
        self.console.print("[dim]Press Ctrl+X in nano, :q in vim to exit[/dim]")
        
        try:
            # Use subprocess for proper terminal handling
            subprocess.run([editor, filename])
            self.console.print(f"[green]✅ Done editing {filename}[/green]")
        except KeyboardInterrupt:
            self.console.print("[yellow]Editor closed[/yellow]")
        except FileNotFoundError:
            self.console.print(f"[red]Editor '{editor}' not found. Install with: pkg install {editor}[/red]")
    
    def cmd_paste(self, args: str):
        """Paste mode for code"""
        parts = args.split()
        if len(parts) < 2:
            self.console.print("[red]❌ Usage: paste <filename>[/red]")
            return
        
        filename = parts[1]
        
        self.console.print(Panel.fit(
            f"[bold yellow]📥 Paste Mode: {filename}[/bold yellow]\\n"
            "[dim]Paste your content (Ctrl+Shift+V in Termux)\\n"
            "Type 'END' on a new line when done[/dim]",
            border_style="yellow"
        ))
        
        lines = []
        line_num = 1
        
        try:
            while True:
                try:
                    prompt = f"[dim]{line_num:3d} | [/dim]"
                    line = input(prompt)
                    if line.strip().upper() == "END":
                        break
                    lines.append(line)
                    line_num += 1
                except EOFError:
                    self.console.print("\\n[yellow]EOF detected, saving...[/yellow]")
                    break
        except KeyboardInterrupt:
            self.console.print("\\n[yellow]Cancelled[/yellow]")
            return
        
        if lines:
            Path(filename).write_text("\\n".join(lines), encoding='utf-8')
            self.console.print(f"[green]✅ Saved {len(lines)} lines to {filename}[/green]")
            
            # Show quick stats
            chars = sum(len(line) for line in lines)
            self.console.print(f"[dim]Characters: {chars}, Lines: {len(lines)}[/dim]")
            
            # Offer to edit
            if Confirm.ask("[cyan]Open file in editor?[/cyan]"):
                self.cmd_edit(f"edit {filename}")
    
    def cmd_cat(self, args: str):
        """View file with syntax highlighting"""
        parts = args.split()
        if len(parts) < 2:
            self.console.print("[red]❌ Usage: cat <filename>[/red]")
            return
        
        filename = parts[1]
        if not os.path.exists(filename):
            self.console.print(f"[red]❌ File not found: {filename}[/red]")
            return
        
        try:
            content = Path(filename).read_text(encoding='utf-8', errors='replace')
            
            if len(content) > 10000:
                self.console.print(f"[yellow]⚠ File is large ({len(content)} chars). Showing first 10KB[/yellow]")
                content = content[:10000] + "\\n... [truncated]"
            
            # Try to detect language from extension
            ext = Path(filename).suffix.lower()
            lang_map = {
                '.py': 'python',
                '.js': 'javascript',
                '.ts': 'typescript',
                '.html': 'html',
                '.css': 'css',
                '.json': 'json',
                '.yml': 'yaml', '.yaml': 'yaml',
                '.md': 'markdown',
                '.sh': 'bash',
                '.bash': 'bash',
                '.txt': 'text',
                '.xml': 'xml',
                '.c': 'c',
                '.cpp': 'cpp', '.cc': 'cpp',
                '.java': 'java',
                '.go': 'go',
                '.rs': 'rust',
                '.php': 'php',
                '.sql': 'sql',
                '.toml': 'toml',
                '.ini': 'ini',
                '.cfg': 'ini',
            }
            
            lang = lang_map.get(ext, 'text')
            
            syntax = Syntax(content, lang, theme="monokai", line_numbers=True, word_wrap=True)
            self.console.print(Panel(syntax, title=f"📄 {filename}", border_style="green"))
            
            # Show file stats
            stat = os.stat(filename)
            size = self._format_size(stat.st_size)
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            self.console.print(f"[dim]Size: {size}, Modified: {mtime}, Lines: {len(content.splitlines())}[/dim]")
            
        except PermissionError:
            self.console.print(f"[red]❌ Permission denied reading {filename}[/red]")
        except Exception as e:
            self.console.print(f"[red]❌ Error reading file: {e}[/red]")
            # Fallback to simple cat
            subprocess.run(['cat', filename])
    
    def cmd_cd(self, args: str):
        """Change directory with completion"""
        parts = args.split(maxsplit=1)
        target = parts[1] if len(parts) > 1 else str(self.termux.home)
        
        # Handle special paths
        if target == "~":
            target = str(self.termux.home)
        elif target.startswith("~/"):
            target = str(self.termux.home / target[2:])
        
        try:
            os.chdir(target)
            self.console.print(f"[green]📁 {os.getcwd()}[/green]")
        except FileNotFoundError:
            self.console.print(f"[red]❌ Directory not found: {target}[/red]")
        except PermissionError:
            self.console.print(f"[red]❌ Permission denied: {target}[/red]")
        except Exception as e:
            self.console.print(f"[red]❌ Error: {e}[/red]")
    
    # ==================== UTILITY COMMANDS ====================
    
    def cmd_history(self, args: str):
        """Show command history"""
        lines = args.split()
        n = 20
        if len(lines) > 1 and lines[1].isdigit():
            n = int(lines[1])
        
        self.console.print(Panel.fit(
            "\n".join(f"[dim]{i+1:3d}[/dim] {cmd}" 
                     for i, cmd in enumerate(list(self.history)[-n:])),
            title=f"📜 Command History (last {n})",
            border_style="blue"
        ))
    
    def cmd_clear(self, args: str):
        """Clear screen"""
        self.console.clear()
        self.banner()
    
    def cmd_help(self, args: str):
        """Show help"""
        help_text = """
[bold cyan]🎯 VIBE CODING[/bold cyan]
  [green]vibe[/green] [cyan]<description>[/cyan]   - Create code from natural language
  [green]code[/green] [cyan]<description>[/cyan]   - Alias for vibe
  [green]make[/green] [cyan]<description>[/cyan]   - Alias for vibe
  [green]create[/green] [cyan]<description>[/cyan] - Alias for vibe

[bold cyan]🤖 AI & VISION[/bold cyan]
  [green]ai[/green] [cyan]<question>[/cyan]       - Ask AI anything about Termux
  [green]ask[/green] [cyan]<question>[/cyan]      - Alias for ai
  [green]look[/green] [cyan][question][/cyan]     - Capture & analyze screen with AI
  [green]see[/green] [cyan][question][/cyan]      - Alias for look
  [green]screen[/green] [cyan][question][/cyan]   - Alias for look
  [green]search[/green] [cyan]<term>[/cyan]       - Web search for Termux info

[bold cyan]📦 PACKAGE MANAGEMENT[/bold cyan]
  [green]pkg[/green] [cyan]install|search|remove <name>[/cyan]
  [green]apt[/green]                           - Alias for pkg
  [green]tools[/green]                         - Show available tools

[bold cyan]📁 FILE OPERATIONS[/bold cyan]
  [green]files[/green] [cyan][-a][/cyan]           - Show file tree (-a for all)
  [green]edit[/green] [cyan]<file> [editor][/cyan] - Edit file with best editor
  [green]paste[/green] [cyan]<file>[/cyan]         - Interactive paste mode
  [green]cat[/green] [cyan]<file>[/cyan]           - View file with syntax highlight
  [green]view[/green] [cyan]<file>[/cyan]          - Alias for cat

[bold cyan]🛠️ UTILITIES[/bold cyan]
  [green]ls[/green], [green]ll[/green]               - List files (external)
  [green]cd[/green] [cyan]<dir>[/cyan]             - Change directory
  [green]pwd[/green]                             - Print working directory
  [green]history[/green] [cyan][n][/cyan]          - Show command history
  [green]clear[/green], [green]cls[/green]           - Clear screen
  [green]stats[/green]                           - Show system stats
  [green]context[/green]                         - Show environment context
  [green]update[/green]                          - Update orchestrator
  [green]projects[/green]                        - List vibe coding projects

[bold cyan]⚡ ALIASES[/bold cyan]
  [green]v[/green] = vibe, [green]c[/green] = code, [green]?[/green] = help
  [green]h[/green] = help, [green]q[/green] = exit, [green]..[/green] = cd ..

[dim]Type any external command to run it normally[/dim]
"""
        
        self.console.print(Panel(help_text, title="📖 Termux AI Orchestrator Help", border_style="cyan"))
    
    def cmd_exit(self, args: str):
        """Exit the orchestrator"""
        self.console.print("[yellow]👋 Goodbye![/yellow]")
        sys.exit(0)
    
    def cmd_stats(self, args: str):
        """Show system statistics"""
        # Get memory info
        mem_info = {}
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        mem_info[key.strip()] = value.strip()
        except:
            mem_info = {}
        
        # Get disk usage
        disk_usage = {}
        try:
            import shutil
            total, used, free = shutil.disk_usage('/data')
            disk_usage = {
                'total': self._format_size(total),
                'used': self._format_size(used),
                'free': self._format_size(free),
                'percent': (used / total) * 100
            }
        except:
            pass
        
        # Get CPU info
        cpu_info = {}
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        cpu_info[key.strip()] = value.strip()
        except:
            pass
        
        # Build stats table
        table = Table(title="📊 System Statistics", border_style="green")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Termux Detected", "✓ YES" if self.termux.is_termux else "✗ NO")
        table.add_row("Root Access", "✓ YES" if self.termux.is_rooted else "✗ NO")
        table.add_row("AI Available", "✓ YES" if self.ai_enabled else "✗ NO")
        table.add_row("Vision Capable", "✓ YES" if self.screen_reader and (self.screen_reader.is_rooted or PIL_AVAILABLE) else "✗ NO")
        
        table.add_row("Python Version", platform.python_version())
        table.add_row("Current Directory", os.getcwd())
        
        if mem_info.get('MemTotal'):
            table.add_row("Memory Total", mem_info['MemTotal'])
        if mem_info.get('MemAvailable'):
            table.add_row("Memory Available", mem_info['MemAvailable'])
        
        if disk_usage:
            table.add_row("Disk Usage", f"{disk_usage['used']} / {disk_usage['total']} ({disk_usage['percent']:.1f}%)")
        
        if cpu_info.get('model name'):
            table.add_row("CPU Model", cpu_info['model name'].strip())
        
        table.add_row("Installed Packages", str(len(self.termux.installed_packages)))
        table.add_row("Python Packages", str(len(self.termux.python_packages)))
        table.add_row("Command History", str(len(self.history)))
        
        self.console.print(table)
    
    def cmd_context(self, args: str):
        """Show detailed environment context"""
        context = self.termux.get_context_summary()
        self.console.print(Panel(context, title="🌍 Environment Context", border_style="cyan"))
    
    def cmd_update(self, args: str):
        """Update the orchestrator"""
        self.console.print("[bold yellow]🔄 Checking for updates...[/bold yellow]")
        
        # Check if running from git
        script_dir = Path(__file__).parent
        if (script_dir / '.git').exists():
            try:
                result = subprocess.run(['git', 'pull'], cwd=script_dir, 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    self.console.print(f"[green]✅ Updated successfully![/green]")
                    self.console.print(f"[dim]{result.stdout}[/dim]")
                    return
                else:
                    self.console.print(f"[red]❌ Update failed[/red]")
                    self.console.print(f"[dim]{result.stderr}[/dim]")
            except:
                pass
        
        # If not git, offer to reinstall
        if Confirm.ask("[yellow]Update via pip install?[/yellow]"):
            try:
                subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'termux-ai-orchestrator'],
                             capture_output=True, text=True, timeout=60)
                self.console.print("[green]✅ Update initiated. Restart may be required.[/green]")
            except:
                self.console.print("[red]❌ Update failed[/red]")
        
        self.console.print("[dim]Manual update: Visit https://github.com/example/termux-ai-orchestrator[/dim]")
    
    def cmd_projects(self, args: str):
        """List vibe coding projects"""
        if not self.vibe_coder.project_history:
            self.console.print("[yellow]📭 No vibe coding projects yet[/yellow]")
            self.console.print("[dim]Use 'vibe <description>' to create your first project[/dim]")
            return
        
        table = Table(title="📂 Vibe Coding Projects", border_style="cyan")
        table.add_column("ID", style="yellow")
        table.add_column("Description", style="green")
        table.add_column("Language", style="cyan")
        table.add_column("Created", style="dim")
        table.add_column("Files", style="dim")
        
        for task in reversed(self.vibe_coder.project_history[-10:]):  # Last 10
            files = len(task.files_to_create)
            time_ago = self._relative_time(task.created_at)
            
            table.add_row(
                task.id,
                task.description[:40] + ("..." if len(task.description) > 40 else ""),
                task.detected_language or "N/A",
                time_ago,
                str(files)
            )
        
        self.console.print(table)
        
        # Show recent files
        recent_files = []
        for task in self.vibe_coder.project_history[-3:]:
            for filename, _ in task.files_to_create:
                if os.path.exists(filename):
                    recent_files.append(filename)
        
        if recent_files:
            self.console.print("[cyan]📄 Recent files:[/cyan]")
            for file in recent_files[:5]:
                self.console.print(f"  [dim]{file}[/dim]")
    
    def _relative_time(self, dt: datetime) -> str:
        """Convert datetime to relative time string"""
        now = datetime.now()
        diff = now - dt
        
        if diff.days > 365:
            years = diff.days // 365
            return f"{years}y ago"
        elif diff.days > 30:
            months = diff.days // 30
            return f"{months}mo ago"
        elif diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}h ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}m ago"
        else:
            return "just now"
    
    def cmd_tools(self, args: str):
        """Show available tools and installers"""
        # Build tools table
        table = Table(title="🛠️ Available Tools", border_style="blue")
        table.add_column("Tool", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Install Command", style="dim")
        table.add_column("Purpose", style="dim")
        
        tools = [
            ("nano", "Simple editor", "pkg install nano"),
            ("vim", "Advanced editor", "pkg install vim"),
            ("micro", "Modern editor", "pkg install micro"),
            ("git", "Version control", "pkg install git"),
            ("nodejs", "JavaScript runtime", "pkg install nodejs"),
            ("python", "Python 3", "pkg install python"),
            ("clang", "C/C++ compiler", "pkg install clang"),
            ("make", "Build tool", "pkg install make"),
            ("curl", "HTTP client", "pkg install curl"),
            ("wget", "Downloader", "pkg install wget"),
            ("tmux", "Terminal multiplexer", "pkg install tmux"),
            ("htop", "Process viewer", "pkg install htop"),
            ("ffmpeg", "Media tools", "pkg install ffmpeg"),
            ("termux-api", "Android API", "pkg install termux-api"),
        ]
        
        for tool, purpose, install_cmd in tools:
            installed = tool in self.termux.installed_packages
            status = "✓ installed" if installed else "✗ not installed"
            status_style = "green" if installed else "yellow"
            
            table.add_row(
                tool,
                f"[{status_style}]{status}[/{status_style}]",
                install_cmd,
                purpose
            )
        
        self.console.print(table)
        
        # Quick install suggestions
        missing_editors = [tool for tool, _, _ in tools[:3] if tool not in self.termux.installed_packages]
        if missing_editors and not self.termux.available_editors:
            self.console.print(f"\n[cyan]💡 Suggestion: Install an editor:[/cyan]")
            self.console.print(f"  [dim]pkg install {missing_editors[0]}[/dim]")
    
    def cleanup(self):
        """Cleanup before exit"""
        if self.screen_reader:
            # Clean up temporary screenshots older than 1 day
            try:
                for file in self.screen_reader.screenshot_dir.glob("termux_screen_*.png"):
                    if file.stat().st_mtime < time.time() - 86400:
                        file.unlink()
            except:
                pass
        
        self.console.print("[dim]Cleaning up...[/dim]")


def main():
    """Main entry point"""
    try:
        orchestrator = TermuxOrchestrator()
        orchestrator.run()
    except KeyboardInterrupt:
        print("\n[yellow]Interrupted[/yellow]")
        sys.exit(0)
    except Exception as e:
        print(f"[red]Fatal error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
