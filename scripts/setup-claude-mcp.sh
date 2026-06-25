#!/bin/bash
# Claude Code MCP Server Setup Script for ReflectAI
# Version: 1.0.0
# Author: ReflectAI Development Team

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check Node.js
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        print_success "Node.js found: $NODE_VERSION"

        # Check if version is 18+
        MAJOR_VERSION=$(echo $NODE_VERSION | cut -d'.' -f1 | tr -d 'v')
        if [ "$MAJOR_VERSION" -lt 18 ]; then
            print_error "Node.js 18+ required, found $NODE_VERSION"
            exit 1
        fi
    else
        print_error "Node.js not found. Please install Node.js 18+"
        echo "Visit: https://nodejs.org/"
        exit 1
    fi

    # Check npm
    if command -v npm &> /dev/null; then
        NPM_VERSION=$(npm --version)
        print_success "npm found: $NPM_VERSION"
    else
        print_error "npm not found"
        exit 1
    fi

    # Check git
    if command -v git &> /dev/null; then
        print_success "git found: $(git --version)"
    else
        print_error "git not found"
        exit 1
    fi

    # Check if in ReflectAI project
    if [ ! -f "CLAUDE.md" ]; then
        print_warning "Not in ReflectAI project root. Run from project directory!"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi

    print_success "All prerequisites met!"
    echo
}

# Setup PostgreSQL MCP
setup_postgres_mcp() {
    print_header "Setting up PostgreSQL MCP Server"

    MCP_DIR="$HOME/mcp-servers"

    # Create directory if not exists
    if [ ! -d "$MCP_DIR" ]; then
        print_info "Creating MCP servers directory..."
        mkdir -p "$MCP_DIR"
    fi

    cd "$MCP_DIR"

    # Clone or update repository
    if [ ! -d "servers" ]; then
        print_info "Cloning MCP servers repository..."
        git clone https://github.com/modelcontextprotocol/servers.git
        print_success "Repository cloned"
    else
        print_info "Updating MCP servers repository..."
        cd servers
        git pull
        cd ..
        print_success "Repository updated"
    fi

    # Install PostgreSQL MCP
    print_info "Installing PostgreSQL MCP dependencies..."
    cd "$MCP_DIR/servers/src/postgres"

    if [ -f "package.json" ]; then
        npm install
        print_success "PostgreSQL MCP installed"
    else
        print_error "PostgreSQL MCP package.json not found"
        exit 1
    fi

    # Test server
    print_info "Testing PostgreSQL MCP server..."
    if node index.js --help &> /dev/null; then
        print_success "PostgreSQL MCP server working"
    else
        print_warning "Could not verify PostgreSQL MCP (may need configuration)"
    fi

    echo
}

# Setup GitHub MCP
setup_github_mcp() {
    print_header "Setting up GitHub MCP Server"

    print_info "GitHub MCP uses npx, no installation needed!"
    print_success "GitHub MCP ready (requires token configuration)"
    echo
}

# Configure environment variables
configure_env() {
    print_header "Configuring Environment Variables"

    SHELL_RC="$HOME/.zshrc"
    if [ ! -f "$SHELL_RC" ]; then
        SHELL_RC="$HOME/.bashrc"
    fi

    print_info "Detected shell configuration: $SHELL_RC"

    # PostgreSQL configuration
    if ! grep -q "PGHOST=localhost" "$SHELL_RC"; then
        print_info "Adding PostgreSQL environment variables..."
        cat >> "$SHELL_RC" << 'EOF'

# PostgreSQL MCP Configuration
export PGHOST=localhost
export PGPORT=5432
export PGUSER=reflectai
export PGPASSWORD=devpassword
export PGDATABASE=reflectai
EOF
        print_success "PostgreSQL env vars added to $SHELL_RC"
    else
        print_info "PostgreSQL env vars already configured"
    fi

    # GitHub token prompt
    echo
    read -p "Do you have a GitHub personal access token? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter GitHub token (ghp_...): " GITHUB_TOKEN
        if [ ! -z "$GITHUB_TOKEN" ]; then
            if ! grep -q "GITHUB_TOKEN=" "$SHELL_RC"; then
                echo "" >> "$SHELL_RC"
                echo "# GitHub MCP Configuration" >> "$SHELL_RC"
                echo "export GITHUB_TOKEN=\"$GITHUB_TOKEN\"" >> "$SHELL_RC"
                print_success "GitHub token added to $SHELL_RC"
            else
                print_info "GitHub token already configured"
            fi
        fi
    else
        print_warning "GitHub MCP requires a personal access token"
        print_info "Create one at: https://github.com/settings/tokens"
        print_info "Required scopes: repo, read:org, workflow"
    fi

    echo
}

# Configure Claude Desktop
configure_claude_desktop() {
    print_header "Configuring Claude Desktop"

    CLAUDE_CONFIG_DIR="$HOME/.config/claude"
    CLAUDE_CONFIG="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"

    # Create directory if not exists
    if [ ! -d "$CLAUDE_CONFIG_DIR" ]; then
        print_info "Creating Claude config directory..."
        mkdir -p "$CLAUDE_CONFIG_DIR"
    fi

    # Backup existing config
    if [ -f "$CLAUDE_CONFIG" ]; then
        print_info "Backing up existing config..."
        cp "$CLAUDE_CONFIG" "$CLAUDE_CONFIG.backup.$(date +%Y%m%d_%H%M%S)"
    fi

    # Create or update config
    print_info "Creating Claude Desktop configuration..."

    # Get absolute path to postgres MCP
    POSTGRES_MCP_PATH="$HOME/mcp-servers/servers/src/postgres/index.js"

    cat > "$CLAUDE_CONFIG" << EOF
{
  "mcpServers": {
    "postgres": {
      "command": "node",
      "args": ["$POSTGRES_MCP_PATH"],
      "env": {
        "PGHOST": "\${PGHOST}",
        "PGPORT": "\${PGPORT}",
        "PGUSER": "\${PGUSER}",
        "PGPASSWORD": "\${PGPASSWORD}",
        "PGDATABASE": "\${PGDATABASE}"
      }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "\${GITHUB_TOKEN}"
      }
    }
  }
}
EOF

    print_success "Claude Desktop configured"
    print_info "Config location: $CLAUDE_CONFIG"
    echo
}

# Verify setup
verify_setup() {
    print_header "Verifying Setup"

    # Check MCP servers directory
    if [ -d "$HOME/mcp-servers/servers/src/postgres" ]; then
        print_success "PostgreSQL MCP directory exists"
    else
        print_error "PostgreSQL MCP directory not found"
    fi

    # Check Claude config
    if [ -f "$HOME/.config/claude/claude_desktop_config.json" ]; then
        print_success "Claude Desktop config exists"

        # Validate JSON
        if python3 -m json.tool "$HOME/.config/claude/claude_desktop_config.json" &> /dev/null; then
            print_success "Claude Desktop config is valid JSON"
        else
            print_error "Claude Desktop config has JSON errors"
        fi
    else
        print_error "Claude Desktop config not found"
    fi

    # Check environment variables
    source "$HOME/.zshrc" 2>/dev/null || source "$HOME/.bashrc" 2>/dev/null || true

    if [ ! -z "$PGHOST" ]; then
        print_success "PostgreSQL env vars loaded"
    else
        print_warning "PostgreSQL env vars not loaded (restart shell)"
    fi

    if [ ! -z "$GITHUB_TOKEN" ]; then
        print_success "GitHub token configured"
    else
        print_warning "GitHub token not configured"
    fi

    echo
}

# Print next steps
print_next_steps() {
    print_header "Setup Complete! 🎉"

    cat << EOF

${GREEN}✅ MCP servers are installed and configured!${NC}

${YELLOW}📋 NEXT STEPS:${NC}

1. ${BLUE}Restart your shell:${NC}
   source ~/.zshrc  # or ~/.bashrc

2. ${BLUE}Verify database connection:${NC}
   ./rai docker status
   ./rai db connections

3. ${BLUE}Test Claude Code:${NC}
   claude

   Try these commands:
   • "List all tables in the database"
   • "Show me the structure of the users table"
   • "List open GitHub issues in this repository"

4. ${BLUE}Read the documentation:${NC}
   docs/claude-code/README.md
   docs/claude-code/01-getting-started/03-quick-start-guide.md

5. ${BLUE}Try new slash commands:${NC}
   /db_inspect
   /cache_status
   /temporal_status

${YELLOW}⚠️  IMPORTANT:${NC}

• If GitHub MCP doesn't work, create a personal access token:
  https://github.com/settings/tokens
  Scopes needed: repo, read:org, workflow

• PostgreSQL MCP requires ReflectAI services to be running:
  ./rai docker up dev

${GREEN}🎯 Quick Test:${NC}

claude
You: "Show me all database tables"

If you see a list of tables, everything is working! 🎉

${BLUE}📚 More Info:${NC}
• PostgreSQL MCP: docs/claude-code/02-mcp-servers/01-postgresql-mcp-setup.md
• GitHub MCP: docs/claude-code/02-mcp-servers/02-github-mcp-setup.md
• Troubleshooting: docs/claude-code/08-troubleshooting/01-common-issues-faq.md

${GREEN}Need help? Ask in #reflectai-dev on Slack!${NC}

EOF
}

# Main execution
main() {
    clear
    print_header "Claude Code MCP Setup for ReflectAI"
    echo
    print_info "This script will install and configure:"
    echo "  • PostgreSQL MCP Server (natural language database queries)"
    echo "  • GitHub MCP Server (automated PR management)"
    echo
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Setup cancelled"
        exit 0
    fi
    echo

    check_prerequisites
    setup_postgres_mcp
    setup_github_mcp
    configure_env
    configure_claude_desktop
    verify_setup
    print_next_steps
}

# Run main function
main "$@"
