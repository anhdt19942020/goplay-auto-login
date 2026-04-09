---
name: Code Standards & Naming Rules
description: Enforced code style, naming conventions, file organization
type: feedback
---

## Enforced Standards

**Naming Conventions**
- Files: `kebab-case` (user-controller.ts)
- Classes: `PascalCase` (UserService)
- Functions/Variables: `camelCase` (getUserById)
- Constants: `UPPER_SNAKE_CASE` (API_BASE_URL)
- Database: `snake_case` (user_accounts)

**Code Style**
- Formatter: Prettier (auto via hooks)
- Linter: ESLint airbnb config
- Max line length: 100 characters
- Indentation: 2 spaces
- No semicolons (Prettier enforces)

**File Structure**
- Controllers in `src/controllers/`
- Services in `src/services/`
- Models in `src/models/`
- Middleware in `src/middleware/`
- Routes in `src/routes/`

## How to Apply

When writing code: use naming conventions immediately
When reviewing: flag non-standard names before merge
When testing: apply same naming to test files (*.test.ts)
When creating: organize by feature folder if large domain
