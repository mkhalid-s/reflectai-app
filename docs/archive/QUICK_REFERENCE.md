# ReflectAI Quick Reference Card

## 🚀 Essential Commands

```bash
# First Time Setup
./rai setup all          # Complete setup

# Daily Development
./rai run app           # Start application
./rai test              # Run tests
./rai check             # Run all checks
./rai clean             # Clean cache

# Before Commit
./rai check format      # Format code
./rai check lint        # Fix linting
./rai test              # Run tests
```

## 📁 Project Structure

```
reflectai-platform/
├── ./rai              # ← YOUR MAIN TOOL
├── src/               # Source code
├── tests/             # Test files
├── docs/              # Documentation
└── .env               # Config (create from .env.example)
```

## 🔧 Common Tasks

| I want to... | Command |
|-------------|---------|
| Install dependencies | `./rai setup deps` |
| Start the app | `./rai run app` |
| Run tests | `./rai test` |
| Format code | `./rai check format` |
| Check code quality | `./rai check` |
| Run in Docker | `./rai run docker` |
| Setup database | `./rai setup db` |
| Run migrations | `./rai db migrate` |
| Clean everything | `./rai clean` |
| Get help | `./rai help` |

## 🐛 Troubleshooting

```bash
# If something's broken
./rai clean             # Clean cache
./rai setup deps        # Reinstall deps
./rai db reset         # Reset database

# Nuclear option
./rai clean
./rai setup all
```

## 💡 Pro Tips

1. **See all commands**: `./rai help`
2. **Check environment**: `./rai version`
3. **Quick alias**: Add to ~/.bashrc: `alias d='./dev'`

## 📚 Full Documentation

See `/docs/DEVELOPER_GUIDE.md` for complete guide.

---
**Remember: When in doubt, run `./rai help`**