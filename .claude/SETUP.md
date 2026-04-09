# Claude Code Setup Guide

This project is configured with Claude Code standards. Follow this guide to enable all features.

## ✅ What's Already Set Up

- ✅ **Slash Commands** in `.claude/commands/` (8 commands ready)
- ✅ **Project Memory** in `.claude/memory/` (persistent context)
- ✅ **Subagents** in `.claude/agents/` (9 specialized agents)
- ✅ **Hook Scripts** in `.claude/hooks/` (auto-formatting & security scanning)
- ✅ **CLAUDE.md** updated with Claude Code standards

## 🔧 Manual Configuration Needed

### Step 1: Enable Hooks (Optional but Recommended)

Hooks auto-run checks when you write/edit code.

**Option A: Merge settings into ~/.claude/settings.json**

1. Open `~/.claude/settings.json` (or create if missing)
2. Add this "hooks" section to your existing config:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": ["D:/projects/vu-dai-tri-tue-api/.claude/hooks/format-code.sh"]
      },
      {
        "matcher": "Edit",
        "hooks": ["D:/projects/vu-dai-tri-tue-api/.claude/hooks/format-code.sh"]
      }
    ]
  }
}
```

**Option B: Let Claude Code handle it**

Type in Claude Code:
```
/update-config
```

Then select "Add hooks for auto-formatting and linting"

### Step 2: Make Hooks Executable (Linux/macOS only)

```bash
chmod +x D:/projects/vu-dai-tri-tue-api/.claude/hooks/*.sh
```

## 🎯 Using Claude Code Features

### **Slash Commands** (Type in Claude prompt)

```bash
/commit           # Create conventional commit
/pr               # Prepare pull request
/test             # Generate & run tests
/optimize         # Performance analysis
/doc              # Generate API docs
/setup-ci-cd      # Configure CI/CD
```

### **Subagents** (Auto-invoked when relevant)

Available agents in `.claude/agents/`:
- `code-reviewer.md` - Full code reviews
- `test-engineer.md` - Test generation
- `documentation-writer.md` - API docs
- `secure-reviewer.md` - Security checks
- `performance-optimizer.md` - Performance profiling

Agents auto-run for complex tasks. You can also request them explicitly:
```
/code-reviewer
```

### **Project Memory** (Auto-loads each session)

Memory files in `.claude/memory/` auto-load. They contain:
- User profile & preferences
- Project status & initiatives
- Known issues & workarounds
- Architecture decisions
- Team contacts

Update memory when:
- Starting new initiative → add to `project_initiatives.md`
- Discovering issue → add to `project_known_issues.md`
- Making architecture decision → add to relevant `arch_*.md`

## 📋 Quick Workflow

```
1. Type your task in Claude Code
   ↓
2. CLAUDE.md auto-loads (project context)
3. Memory auto-loads (persistent decisions)
   ↓
4. Code hooks auto-format/lint (if enabled)
5. Agents auto-review (if complex task)
   ↓
6. Use slash commands as needed
   - /test    → Generate tests
   - /commit  → Commit with conventional format
   - /pr      → Prepare pull request
   ↓
7. Memory saved for next session
```

## 🔍 File Locations

```
.claude/
├── commands/           # Slash commands (copy any to ~/.claude/commands/)
├── agents/             # Subagents (auto-loaded)
├── hooks/              # Auto-formatting & security checks
├── memory/             # Project memory (auto-loaded)
│   ├── MEMORY.md       # Index of all memories
│   ├── user_*.md       # User profile
│   ├── project_*.md    # Project status & issues
│   ├── feedback_*.md   # Development standards
│   ├── arch_*.md       # Architecture decisions
│   └── reference_*.md  # External references
├── settings-template.json  # Template (merge into ~/.claude/settings.json)
└── SETUP.md            # This file
```

## ⚡ Next Steps

1. ✅ Review memory files to understand project context
2. ✅ Configure hooks (optional but recommended)
3. ✅ Copy slash commands to `~/.claude/commands/` for global use
4. ✅ Try `/test` or `/doc` commands

## 🆘 Troubleshooting

**Hooks not running?**
- Check `~/.claude/settings.json` has hooks configured
- Verify hook script paths are absolute
- Run `chmod +x .claude/hooks/*.sh` (Unix/macOS)

**Memory not loading?**
- Memory auto-loads from `CLAUDE.md` and `.claude/memory/`
- If missing context, check memory files exist
- Update MEMORY.md index if files added/removed

**Slash commands not found?**
- Commands must be in `.claude/commands/` or `~/.claude/commands/`
- File names must match: `/commandname` → `commandname.md`
- Check file has frontmatter or agent spec

## 📚 Learn More

Full Claude Code guide: https://github.com/luongnv89/claude-howto

- Slash Commands: 30 min tutorial
- Memory System: 45 min tutorial
- Hooks: 1 hour tutorial
- Subagents: 1.5 hour tutorial

---

**Last Updated**: April 2026
**Project**: Vũ Đài Trí Tuệ API (Edutalk Labs)
