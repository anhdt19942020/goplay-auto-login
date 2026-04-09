# Claude Code Quick Reference

Fast lookup for common tasks in this project.

## 🎯 Most Used Slash Commands

| Command | What it does | When to use |
|---------|-------------|-----------|
| `/test` | Generate & run tests | After writing code |
| `/commit` | Create conventional commit | Before pushing |
| `/pr` | Prepare pull request | When PR ready |
| `/doc` | Generate API documentation | After API changes |
| `/optimize` | Performance analysis | Before deployment |

## 🤖 Subagents (Auto-Invoked)

| Agent | Triggers | What it does |
|-------|----------|------------|
| code-reviewer | Any code changes | Reviews code quality |
| test-engineer | New functions/methods | Generates tests |
| secure-reviewer | File writes | Security checks |
| performance-optimizer | Complex queries | Performance analysis |
| documentation-writer | API changes | Generates docs |

## 📝 Project Memory (Auto-Loaded)

Your context auto-loads from:
1. `CLAUDE.md` - Project standards & team info
2. `.claude/memory/` - Persistent decisions & status

**View memory:** Check `.claude/memory/MEMORY.md` for index

## 🏗️ Project Structure

```
src/
├── controllers/      # API handlers
├── services/         # Business logic
├── models/          # Mongoose schemas
├── middleware/      # Express middleware
├── routes/          # API routes
├── utils/           # Helper functions
└── types/           # TypeScript types

docs/
├── architecture.md
├── api-standards.md
└── database-schema.md

.claude/
├── commands/        # Slash commands
├── agents/          # Subagents
├── hooks/           # Auto-format/lint
├── memory/          # Project context
└── SETUP.md         # Setup guide
```

## 🔑 Key Standards

**Naming**
- Files: `kebab-case` (user-controller.ts)
- Functions: `camelCase` (getUserById)
- Classes: `PascalCase` (UserService)
- Constants: `UPPER_SNAKE_CASE` (API_BASE_URL)

**Code Style**
- Max line: 100 chars
- Indentation: 2 spaces
- Formatter: Prettier
- Linter: ESLint airbnb

**Testing**
- Framework: Jest + Supertest
- File pattern: `*.test.ts`
- Must test: All APIs, critical logic
- Use real DB: No mocks for integration tests

**Git**
- Branches: `feature/name` or `fix/name`
- Commits: Conventional format
- PRs: Required, 1 approval needed

## ⚙️ Common Patterns

### Writing an API Endpoint

```typescript
// 1. Define route in src/routes/
router.post('/api/v1/matches/:id/submit-answer', submitAnswer);

// 2. Add controller in src/controllers/
async function submitAnswer(req: Request, res: Response) {
  const { id } = req.params;
  const result = await matchService.submitAnswer(id, req.body);
  res.json({ data: result, success: true });
}

// 3. Add service in src/services/
async submitAnswer(id: string, answer: unknown) {
  const match = await MatchModel.findById(id);
  // business logic
  return result;
}

// 4. Write tests (use /test command)
```

### Adding a Database Model

```typescript
// 1. Create schema in src/models/
const matchSchema = new Schema({
  title: String,
  status: { type: String, enum: ['active', 'finished'] },
  createdAt: { type: Date, default: Date.now },
  updatedAt: { type: Date, default: Date.now }
});

// 2. Add index on frequently queried fields
matchSchema.index({ status: 1, createdAt: -1 });

// 3. Export model
export const MatchModel = model('matches', matchSchema);

// 4. Document in docs/database-schema.md
```

## 📊 Current Project Status

**Focus Areas**
- Match monitoring APIs (in development)
- Socket.io performance optimization (planned)

**Known Issues**
- Socket.io degrades >100 concurrent users (workaround: limit rooms to 50)
- Some endpoints need caching

**See**: `.claude/memory/project_*.md` for details

## 🎓 Learning Paths

**New to project?** Read in order:
1. This quick reference (5 min)
2. `CLAUDE.md` for standards (10 min)
3. `.claude/memory/MEMORY.md` for context (15 min)
4. Run `/test` or `/doc` to see commands in action (5 min)

**New to Claude Code?** 
1. Try `/test` command
2. Use `/doc` to generate documentation
3. Check `.claude/SETUP.md` for detailed setup

**Master all features?**
1. See https://github.com/luongnv89/claude-howto
2. Full learning path: 11-13 hours

## 🔗 Important Links

| Resource | Purpose |
|----------|---------|
| `@docs/architecture.md` | System design |
| `@docs/api-standards.md` | API patterns |
| `@docs/database-schema.md` | Data models |
| `.claude/memory/` | Project context |
| `.claude/SETUP.md` | Detailed setup |

## 💬 Team Contacts

- **Sarah Chen** (@sarah.chen) - Tech Lead - Architecture decisions
- **Mike Johnson** (@mike.j) - Product Manager - Features & prioritization  
- **Alex Kim** (@alex.k) - DevOps - Deployment & infrastructure

---

**Tip**: Bookmark this file. Check memory files for project-specific decisions!
