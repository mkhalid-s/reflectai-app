# ReflectAI Scripts Directory

This directory contains specialized scripts for production operations, migrations, and advanced configurations that complement the main `./dev` CLI tool.

## 📁 Directory Structure

```
scripts/
├── production/          # Production deployment scripts
├── migration/           # Data migration utilities
├── validation/          # System validation tools
└── advanced/           # Advanced configuration scripts
```

## 🎯 Important Note

**Most development tasks should use the `./dev` CLI tool instead of these scripts.**

These scripts are for specialized operations that are either:
- Too complex for the CLI
- Production-specific
- Rarely used advanced configurations

## 📂 Script Categories

### Production (`/production`)
Scripts for production deployment and operations.

| Script | Purpose | Usage |
|--------|---------|-------|
| `deploy.sh` | Production deployment | `./scripts/production/deploy.sh [environment]` |

### Migration (`/migration`)
Data migration and transformation utilities.

| Script | Purpose | Usage |
|--------|---------|-------|
| `data_migration.py` | Migrate legacy data | `python scripts/migration/data_migration.py --source=legacy --target=new` |

### Validation (`/validation`)
System validation and health checks.

| Script | Purpose | Usage |
|--------|---------|-------|
| `validate_system.py` | Comprehensive system validation | `python scripts/validation/validate_system.py` |
| `comprehensive_validation.py` | Full implementation validation | `python scripts/validation/comprehensive_validation.py` |

### Advanced (`/advanced`)
Advanced setup and configuration scripts.

| Script | Purpose | Usage |
|--------|---------|-------|
| `setup_secrets.py` | Advanced secret management (Doppler/Vault) | `python scripts/advanced/setup_secrets.py --provider=doppler` |
| `setup_redis_dev.py` | Comprehensive Redis development setup | `python scripts/advanced/setup_redis_dev.py --full` |

## 🚀 Quick Reference

### For Developers
Use the `./dev` CLI for common tasks:
```bash
./rai setup all      # Complete setup
./rai run app        # Run application
./rai test           # Run tests
./rai check          # Code quality checks
```

### For DevOps
Production operations:
```bash
./scripts/production/deploy.sh staging
./scripts/production/deploy.sh production
```

### For Data Engineers
Data migration:
```bash
python scripts/migration/data_migration.py --help
python scripts/migration/data_migration.py --dry-run
python scripts/migration/data_migration.py --execute
```

### For System Administrators
System validation:
```bash
python scripts/validation/validate_system.py
python scripts/validation/comprehensive_validation.py --verbose
```

## ⚠️ Important Notes

1. **Always use `./dev` first** - Check if your task can be done with the main CLI
2. **Production scripts require approval** - Don't run production scripts without authorization
3. **Backup before migration** - Always backup data before running migration scripts
4. **Test in staging** - Test all scripts in staging environment first

## 🔧 Script Development Guidelines

When creating new scripts:

1. **Check if it belongs in `./dev`** - Most functionality should be in the main CLI
2. **Place in correct category** - Use the appropriate subdirectory
3. **Document thoroughly** - Include docstrings and usage examples
4. **Add error handling** - Scripts should fail gracefully
5. **Include dry-run option** - For destructive operations
6. **Update this README** - Keep documentation current

## 📋 Maintenance

### Deprecated Scripts
Scripts that have been replaced by `./dev` commands are archived in `/archive/old_scripts/`:
- `setup_local_db.sh` → Use `./rai setup db`
- `setup_local_redis.sh` → Use `./rai setup redis`
- `manage_migrations.py` → Use `./rai db migrate`

### Future Consolidation
We're working to integrate more scripts into the `./dev` CLI. Scripts here should only be for specialized operations that don't fit the CLI model.

## 🆘 Need Help?

1. Check `./rai help` first
2. Read script docstrings: `python script.py --help`
3. Check `/docs/DEVELOPER_GUIDE.md`
4. Ask in team chat

---

**Remember: The `./dev` CLI is the primary tool. These scripts are for special cases only.**