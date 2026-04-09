# Claude Code Setup Summary

**Date:** April 7, 2026  
**Project:** edutalk-api (Laravel 10 PHP API)  
**Status:** ✅ Complete

---

## What Was Configured

### 1. **Project Memory (CLAUDE.md)**
**File:** `D:\Projects\edutalk-api\CLAUDE.md`

Comprehensive project documentation covering:
- Tech stack (Laravel 10, PHP 8.1+, MongoDB, MySQL, RabbitMQ)
- Architecture patterns (Repository/Service/Transformer/DTO)
- Coding standards (Laravel Pint PSR-12, PHPStan level 5+)
- Common commands and workflows
- Database connections and API structure
- Cloud/external services (AWS S3, Telegram, Google APIs)
- Testing and quality assurance practices

**Usage:** Claude will automatically read this file and understand the project context, tech stack, and coding standards.

---

### 2. **Project Settings (.claude/settings.json)**
**File:** `D:\Projects\edutalk-api\.claude\settings.json`

Configured hooks:
- **PostToolUse (Write/Edit)** → Auto-run `php artisan pint` to format PHP files
- **PostToolUse (Bash)** → Validate dangerous commands before execution

**Effect:** When you create or edit a PHP file, Pint automatically formats it. When you run shell commands, dangerous patterns are flagged.

---

### 3. **Automation Scripts (.claude/hooks/)**
**Files:**
- `validate-bash.sh` - Warns about dangerous bash commands

---

### 4. **Slash Commands (.claude/commands/)**
**Available commands:**
- `/artisan <cmd>` - Run Laravel artisan commands
- `/make-crud <Model>` - Generate complete CRUD structure
- `/test [--file|--filter|--coverage]` - Run PHPUnit tests
- `/format [--file|--all]` - Auto-format PHP with Pint

**Usage:** Type `/artisan migrate` or `/make-crud User` directly in Claude Code.

---

### 5. **Project Skills (.claude/skills/)**
**Available skills:**
- `laravel-crud` - Generate CRUD modules following Repository/Service/Transformer patterns
- `laravel-test` - Write comprehensive unit and feature tests

**Auto-invocation:** Claude automatically uses these skills when relevant to your request (e.g., "create a User model").

---

### 6. **MCP Server Configuration (.mcp.json)**
**File:** `D:\Projects\edutalk-api\.mcp.json`

Configured MongoDB MCP server for database operations:
- Query MongoDB collections
- Analyze logs and analytics
- Use MCP tools like `//@mcp mongodbCitime aggregate`

---

## Quick Start Guide

### First Time Setup
```bash
# 1. Verify CLAUDE.md loads
cd D:\Projects\edutalk-api
# Claude will now automatically read CLAUDE.md and understand the project

# 2. Test a slash command
/artisan migrate:status

# 3. Test auto-formatting
# Create a new PHP file, Claude will auto-format it with Pint
```

### Common Workflows

**Create a new CRUD module:**
```
/make-crud User
# Generates: Model, Migration, Repository, Service, Controller, 
#            Transformer, FormRequest, and API routes
```

**Run tests:**
```
/test
/test --file=tests/Feature/UserTest.php
/test --filter=test_create_user --coverage
```

**Format code:**
```
/format
/format --file=app/Models/User.php
```

**Run artisan commands:**
```
/artisan migrate
/artisan tinker
/artisan queue:work
```

---

## File Structure Reference

```
D:\Projects\edutalk-api/
├── CLAUDE.md                          ← Project context & standards
├── .mcp.json                          ← MCP server config
├── .claude/
│   ├── settings.json                  ← Hooks & permission config
│   ├── settings.local.json            ← (existing, local-only)
│   ├── commands/
│   │   ├── artisan.md                 ← /artisan command
│   │   ├── make-crud.md               ← /make-crud command
│   │   ├── test.md                    ← /test command
│   │   └── format.md                  ← /format command
│   ├── hooks/
│   │   └── validate-bash.sh           ← Command validation
│   └── skills/
│       ├── laravel-crud/SKILL.md      ← CRUD generation skill
│       └── laravel-test/SKILL.md      ← Testing skill
├── app/
├── routes/
├── database/
├── tests/
└── ... (existing Laravel structure)
```

---

## Advanced Configuration

### Adding Project-Specific Skills
Create new skill at `.claude/skills/skill-name/SKILL.md` with frontmatter:

```markdown
---
name: my-skill
description: Brief description for auto-invocation
allowed-tools: Bash, Read, Write, Grep
paths: "app/**/*.php"
---

# Skill Documentation
...
```

### Adding Project-Specific Commands
Create new command at `.claude/commands/command-name.md`:

```markdown
---
name: command-name
description: What this command does
---

# /command-name

Usage, examples, implementation...
```

### Adding More Hooks
Edit `.claude/settings.json` to add hooks for:
- `SessionStart` - Initialize new sessions
- `UserPromptSubmit` - Validate user input
- `PreToolUse` - Prepare before tool execution
- `PostToolUseFailure` - Handle tool errors
- etc. (25+ event types available)

---

## Verification Checklist

Run these to verify everything works:

- [ ] Type `/artisan migrate:status` — should list migrations
- [ ] Edit a PHP file — should auto-format with Pint
- [ ] Run `/make-crud TestModel` — should generate CRUD structure
- [ ] Run `/test` — should execute tests
- [ ] Ask "What's the tech stack?" — Claude should reference CLAUDE.md

---

## Troubleshooting

### "command not found" for /artisan
- **Issue:** Vendor directory not loaded
- **Fix:** Run `composer install` in project directory

### Pint not formatting
- **Issue:** Hook timeout or pint not installed
- **Fix:** Run `composer require --dev laravel/pint`

### MongoDB MCP not connecting
- **Issue:** MONGODB_URI not set in environment
- **Fix:** Set env var or update `.mcp.json` with connection string

### Settings.json not being read
- **Issue:** Cache or permission issue
- **Fix:** Restart Claude Code or check file permissions

---

## Next Steps

1. **Add more domain-specific slash commands** for your team's workflows
2. **Create project-specific skills** for recurring tasks
3. **Configure organization-wide memory** in `~/.claude/CLAUDE.md`
4. **Set up team hooks** for CI/CD integration via `http` hook type
5. **Document team conventions** in project CLAUDE.md as they evolve

---

## References

- **Claude Code Guide:** `https://github.com/luongnv89/claude-howto`
- **Official Docs:** Claude Code documentation (in IDE)
- **This Project:** See CLAUDE.md at root for detailed standards

