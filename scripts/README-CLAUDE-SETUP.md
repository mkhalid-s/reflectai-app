# Claude Code MCP Setup Script

**Automated setup for PostgreSQL and GitHub MCP servers**

## 🚀 Quick Start

```bash
# Run the setup script
./scripts/setup-claude-mcp.sh
```

The script will:
1. ✅ Check all prerequisites (Node.js, npm, git)
2. ✅ Install PostgreSQL MCP server
3. ✅ Configure GitHub MCP server
4. ✅ Set up environment variables
5. ✅ Create Claude Desktop configuration
6. ✅ Verify everything works

**Time**: 5-10 minutes

---

## 📋 What Gets Installed

### PostgreSQL MCP Server
- **Location**: `~/mcp-servers/servers/src/postgres/`
- **Purpose**: Natural language database queries
- **Impact**: 3x faster database operations

### GitHub MCP Server
- **Location**: Uses `npx` (no installation)
- **Purpose**: Automated PR creation and management
- **Impact**: 5 minutes saved per PR

### Configuration Files
- **Shell config**: `~/.zshrc` or `~/.bashrc` (environment variables)
- **Claude config**: `~/.config/claude/claude_desktop_config.json`

---

## 🔧 Manual Setup (If Script Fails)

### Step 1: Install PostgreSQL MCP

```bash
# Create directory
mkdir -p ~/mcp-servers
cd ~/mcp-servers

# Clone repository
git clone https://github.com/modelcontextprotocol/servers.git
cd servers/src/postgres

# Install dependencies
npm install

# Test
node index.js --help
```

### Step 2: Configure Environment

Add to `~/.zshrc` or `~/.bashrc`:

```bash
# PostgreSQL MCP Configuration
export PGHOST=localhost
export PGPORT=5432
export PGUSER=reflectai
export PGPASSWORD=devpassword
export PGDATABASE=reflectai

# GitHub MCP Configuration
export GITHUB_TOKEN="ghp_your_token_here"
```

Reload shell:
```bash
source ~/.zshrc  # or ~/.bashrc
```

### Step 3: Configure Claude Desktop

Create `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "postgres": {
      "command": "node",
      "args": ["/Users/YOUR_USERNAME/mcp-servers/servers/src/postgres/index.js"],
      "env": {
        "PGHOST": "${PGHOST}",
        "PGPORT": "${PGPORT}",
        "PGUSER": "${PGUSER}",
        "PGPASSWORD": "${PGPASSWORD}",
        "PGDATABASE": "${PGDATABASE}"
      }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

**Important**: Replace `/Users/YOUR_USERNAME/` with your actual path!

---

## 🧪 Verification

### Test PostgreSQL MCP

```bash
# Start ReflectAI services
./rai docker up dev

# Start Claude
claude

# Try these:
You: "List all tables in the database"
You: "Show me the structure of the users table"
You: "Show me recent competency assessments"
```

### Test GitHub MCP

```bash
claude

# Try these:
You: "List open issues in this repository"
You: "Show me the last 5 commits"
You: "Create a PR for these changes"
```

---

## 🐛 Troubleshooting

### Script fails with "Node.js not found"

**Solution**: Install Node.js 18+
```bash
# macOS with Homebrew
brew install node@20

# Or download from
open https://nodejs.org/
```

### "Permission denied" error

**Solution**: Make script executable
```bash
chmod +x scripts/setup-claude-mcp.sh
```

### PostgreSQL MCP not connecting

**Solution**: Check database is running
```bash
./rai docker status
./rai docker up dev

# Test connection
./rai db connect
\q
```

### GitHub MCP "Bad credentials"

**Solution**: Create GitHub token
1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `repo`, `read:org`, `workflow`
4. Copy token
5. Add to `~/.zshrc`: `export GITHUB_TOKEN="ghp_..."`
6. Reload: `source ~/.zshrc`

### Claude can't find MCP servers

**Solution**: Check configuration
```bash
# Verify config exists
cat ~/.config/claude/claude_desktop_config.json

# Validate JSON syntax
python3 -m json.tool ~/.config/claude/claude_desktop_config.json

# Check paths are absolute
# /Users/username/... not ~/...
```

### Environment variables not working

**Solution**: Reload shell
```bash
# Close and reopen terminal, or:
source ~/.zshrc  # or ~/.bashrc

# Verify variables are set
echo $PGHOST
echo $GITHUB_TOKEN
```

---

## 📚 Documentation

**Full guides**:
- [PostgreSQL MCP Setup](../docs/claude-code/02-mcp-servers/01-postgresql-mcp-setup.md)
- [GitHub MCP Setup](../docs/claude-code/02-mcp-servers/02-github-mcp-setup.md)
- [Troubleshooting Guide](../docs/claude-code/08-troubleshooting/01-common-issues-faq.md)

**Quick links**:
- [Main README](../docs/claude-code/README.md)
- [Quick Start Guide](../docs/claude-code/01-getting-started/03-quick-start-guide.md)
- [Command Cheatsheet](../docs/claude-code/10-quick-reference/01-command-cheatsheet.md)

---

## 🎯 What's Next?

After successful setup:

1. **Read Quick Start Guide**
   ```bash
   open docs/claude-code/01-getting-started/03-quick-start-guide.md
   ```

2. **Try 5 Essential Tasks** (15 minutes)
   - Use `/research_module`
   - Use `/quick_test`
   - Use `/db_inspect`
   - Use `/cache_status`
   - Try natural language queries

3. **Configure Hooks** (optional but recommended)
   ```bash
   open docs/claude-code/03-hooks/README.md
   ```

4. **Share Your Experience**
   - Post wins in #reflectai-dev
   - Help others with setup
   - Report any issues

---

## 🤝 Contributing

Found a bug in the script? Have an improvement?

1. Edit `scripts/setup-claude-mcp.sh`
2. Test thoroughly
3. Submit PR
4. Help others!

---

## 📞 Getting Help

- **Documentation**: `docs/claude-code/`
- **Slack**: #reflectai-dev
- **Issues**: Create GitHub issue
- **Direct**: Ask me!

---

**Happy coding with Claude!** 🚀
