---
name: format
description: Auto-format PHP code using Laravel Pint (PSR-12)
---

# /format

Auto-format PHP files using Laravel Pint (PSR-12 with project-specific rules).

## Usage

```
/format [--file=path] [--all]
```

## Examples

```bash
/format                              # Format current/edited file
/format --file=app/Models/User.php   # Format specific file
/format --all                        # Format entire project (long!)
```

## Formatting Rules

Configured in `pint.json`:

- **Preset:** Laravel (PSR-12)
- **Simplified null return:** `return null;` → `return;`
- **Braces:** No forced braces on short functions
- **Class instantiation:** No braces required

## Manual Run

```bash
composer pint                        # Format all
./vendor/bin/pint app/Models/User.php  # Format specific file
```

## Auto-Format on Save

**Automatic:** When you edit or create a PHP file, Pint runs automatically via the PostToolUse hook.

## Implementation

```bash
cd $CLAUDE_PROJECT_DIR && ./vendor/bin/pint {{file}}
```
