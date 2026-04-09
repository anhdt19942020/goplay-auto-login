#!/bin/bash
# validate-bash.sh: Warn about dangerous bash commands
# Called after Bash tool use with the command as argument

COMMAND="$1"

# List of dangerous patterns to warn about
DANGEROUS_PATTERNS=(
  "git reset --hard"
  "git push --force"
  "rm -rf /"
  "drop database"
  "DROP TABLE"
  "DELETE FROM"
  "truncate table"
  "TRUNCATE TABLE"
)

for pattern in "${DANGEROUS_PATTERNS[@]}"; do
  if echo "$COMMAND" | grep -qi "$pattern"; then
    echo "⚠️  WARNING: Detected potentially destructive command: $pattern"
    echo "    Command: $COMMAND"
    echo "    Review carefully before executing."
  fi
done

exit 0
