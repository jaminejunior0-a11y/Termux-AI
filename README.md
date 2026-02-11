
# 🤖 Termux AI Orchestrator

**An AI-powered terminal assistant for Android/Termux with vibe coding, package management, and experimental screen reading capabilities.**

![Version](https://img.shields.io/badge/version-7.2-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Platform](https://img.shields.io/badge/platform-Termux%2FAndroid-orange.svg)

---

## 🌟 Features

### ✅ Current Features

| Feature | Description | Command |
|---------|-------------|---------|
| **🚀 Vibe Coding** | Natural language to working code | `vibe "create a python web server"` |
| **📦 Package Management** | Install/search/remove packages | `pkg install <name>` |
| **🤖 AI Chat** | Ask AI with Termux context | `ai "how to set up git"` |
| **📁 File Operations** | Tree view, edit, paste mode | `files`, `edit <file>`, `paste <file>` |
| **🔍 Smart Search** | Search history & packages | `search <term>` |
| **📊 System Stats** | Disk usage, packages, tools | `stats`, `context` |
| **📝 Code Templates** | Pre-built templates for common tasks | Built into vibe command |
| **🌐 Web Search** | Search Termux packages/info | `web <query>` |

### 🔬 Experimental Features (In Development)

| Feature | Status | Description |
|---------|--------|-------------|
| **👁️ Screen Reading** | 🚧 Beta | AI analyzes your terminal screen |
| **📸 Screenshot Capture** | 🚧 Beta | Capture and analyze screen content |

---

## 📥 Installation

### Prerequisites

- Android device with [Termux](https://termux.dev/) installed
- Python 3.8 or higher
- Internet connection (for AI features)

### Step-by-Step Setup

#### 1. Install Termux
Download from [F-Droid](https://f-droid.org/packages/com.termux/) (recommended) or [GitHub](https://github.com/termux/termux-app/releases).

#### 2. Update Termux Packages
```bash
pkg update && pkg upgrade
```

3. Install Required Packages

```bash
pkg install python python-pip git -y
```

4. Clone the Repository

```bash
git clone https://github.com/jaminejunior0-a11y/Termux-AI.git
cd Termux-AI
```

5. Install Python Dependencies

```bash
pip install openai rich pygments requests colorama pillow
```

Or let the script auto-install:

```bash
python termux_ai.py
```

6. Set Up AI API Key (Required for AI features)

Choose one of the following:

Option A: Groq (Recommended - Free tier available)

```bash
export GROQ_API_KEY="your_groq_api_key_here"
```

Option B: OpenAI

```bash
export OPENAI_API_KEY="your_openai_api_key_here"
```

To make permanent, add to `~/.bashrc`:

```bash
echo 'export GROQ_API_KEY="your_key_here"' >> ~/.bashrc
source ~/.bashrc
```

7. Run Termux AI

```bash
python termux_ai.py
```

---

🎮 Usage

Quick Start Commands

```bash
# Start the orchestrator
python termux_ai.py

# Get help
help

# Create code from natural language
vibe "create a python web server on port 8080"
code "make a bash backup script"
make "flask todo app"

# Ask AI for help
ai "how to install nodejs in termux"
ask "best practices for termux scripts"

# File operations
files                    # Show file tree
edit myscript.py        # Edit with best available editor
cat myscript.py         # View with syntax highlighting
paste newfile.py        # Paste mode for code

# Package management
pkg install python
pkg search editor
tools                   # List available tools

# System info
stats                   # Show system statistics
context                 # Show environment context

# Exit
exit or quit
```

---

👁️ Screen Reading Feature (Experimental)

> ⚠️ This feature is in active development and may not work on all devices.

What It Does

The `look` / `see` / `screen` commands allow the AI to "see" your terminal screen and provide assistance based on what's currently displayed.

How It Works

1. Capture Method: Uses multiple fallback strategies:
   - Rooted devices: Direct screenshot via `screencap`
   - Non-rooted: Terminal buffer capture + text-to-image conversion
   - Fallback: Text-based terminal content analysis

2. AI Analysis: Sends captured content to vision-capable AI models (GPT-4o)

3. Response: AI describes what it sees and answers your questions

Usage

```bash
# Basic screen analysis
look

# Ask specific question about screen
look "What error do you see?"
see "Explain this code"
screen "How do I fix this?"
```

Current Limitations

Issue	Status	Workaround	
Requires GPT-4o access	🔴	Use OpenAI API key with vision access	
Root needed for full screenshots	🟡	Terminal buffer capture works without root	
PIL required for image conversion	🟡	Install with `pip install pillow`	
Limited to terminal content	🟡	External apps not visible without root	

Development Roadmap

- Better non-root screenshot capture
- Support for more AI vision providers (Claude, Gemini)
- OCR for image-based terminal content
- Screen recording for dynamic analysis
- Integration with Android accessibility services

Help Wanted! 🤝

We're looking for contributors to help with:

1. Non-root screenshot solutions - Exploring ADB, accessibility APIs, or Termux:API integration
2. OCR improvements - Better text recognition from terminal screenshots
3. Vision model support - Adding Claude, Gemini, and local vision models
4. Testing - Feedback on different Android versions and devices

If you have ideas or solutions, please open an issue or PR!

---

🏗️ Architecture

```
Termux AI Orchestrator
├── TermuxContext          # Environment detection & package management
├── VibeCoder             # Natural language → code generation
├── ScreenReader          # 📸 Screen capture & AI vision (NEW)
├── WebSearchTool         # Package search & web info
├── CodeTemplates         # Pre-built code templates
└── TermuxOrchestrator    # Main command loop & UI
```

---

🛠️ Requirements

Package	Purpose	Auto-install	
`openai`	AI API client	✅ Yes	
`rich`	Beautiful terminal UI	✅ Yes	
`pygments`	Syntax highlighting	✅ Yes	
`requests`	HTTP requests	✅ Yes	
`colorama`	Cross-platform colors	✅ Yes	
`pillow`	Image processing (screen)	✅ Yes	

---

🔧 Configuration

Environment Variables

Variable	Purpose	Required	
`GROQ_API_KEY`	Groq AI API access	Optional	
`OPENAI_API_KEY`	OpenAI API access	Optional	
`ANTHROPIC_API_KEY`	Claude API access	Optional	
`LOCALAI_BASE`	Local AI endpoint	Optional	

At least one AI provider required for AI features

Optional: Termux:API Integration

For enhanced device integration:

```bash
pkg install termux-api
```

---

🐛 Troubleshooting

Common Issues

Problem	Solution	
`ModuleNotFoundError`	Run `pip install -r requirements.txt`	
AI not responding	Check API key with `echo $GROQ_API_KEY`	
Screen capture fails	Ensure device is rooted or use terminal buffer mode	
Permission denied	Run `termux-setup-storage`	

Debug Mode

```bash
# Run with verbose output
python termux_ai.py --debug
```

---

🤝 Contributing

We welcome contributions! Areas of focus:

- 🐛 Bug fixes
- ✨ New features (especially screen reading improvements)
- 📚 Documentation
- 🧪 Testing on different devices

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

📜 License

MIT License - see [LICENSE](LICENSE) file.

---

🙏 Acknowledgments

- [Rich](https://github.com/Textualize/rich) for beautiful terminal UI
- [OpenAI](https://openai.com/) / [Groq](https://groq.com/) for AI APIs
- [Termux](https://termux.dev/) community for the amazing terminal environment

---

Made with ❤️ for the Termux community
