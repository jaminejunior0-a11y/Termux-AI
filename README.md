🚀 Ethical AI Terminal (v6.7)
An Autonomous Termux Orchestrator & AI Bridge
The Ethical AI Terminal is a high-fidelity, PTY-based shell wrapper designed for Termux and Linux environments. It integrates a direct-link AI assistant (Groq/OpenAI) to provide real-time command suggestions, security audits, and system orchestration without the bloat.
✨ Features
 * Direct-Link AI: Bypasses local proxy conflicts (like Orbot/VPNs) for consistent AI availability.
 * High-Fidelity UI: Powered by Rich for a cyberpunk-style dashboard and readable output.
 * Agnostic Design: Works on any Termux or Linux setup—fully customizable for your own drive mounts.
 * Proactive Error Analysis: (Optional) Can be configured to suggest fixes for "Command Not Found" errors.
 * Low Overhead: Optimized for mobile devices to ensure zero lag during standard terminal operations.
🛠️ Installation
1. Clone the Repository
git clone https://github.com/jaminejunior0-a11y/Termux-AI.git.git
cd Termux-AI 

3. Install Dependencies
pip install rich httpx

4. Set Up Your API Keys
This script supports both Groq (Llama 3.3) and OpenAI. Add your preferred key to your shell profile (~/.bashrc or ~/.zshrc):
export GROQ_API_KEY='your_groq_api_key_here'
# OR
export OPENAI_API_KEY='your_openai_api_key_here'

🚀 Usage
Run the orchestrator:
python termux_ai.py

Commands
 * Standard Commands: Run any shell command (ls, pkg install, git, etc.) as usual.
 * AI Integration: Use the ai keyword to talk to the assistant.
   * Example: ai how do I find large files in this directory?
 * Clear Screen: Use clear to refresh the dashboard.

🛡️ Ethical Use
This tool is intended for Cybersecurity hobbyists and Developers. Always ensure you have permission before performing audits or network scans on infrastructure you do not own.


🙏 Acknowledgments

- [Rich](https://github.com/Textualize/rich) for beautiful terminal UI
- [OpenAI](https://openai.com/) / [Groq](https://groq.com/) for AI APIs
- [Termux](https://termux.dev/) community for the amazing terminal environment

---

Made with ❤️ for the Termux community
