---
name: artisan
description: Run Laravel artisan commands (migrate, seed, queue:work, tinker, etc.)
---

# /artisan

Run any Laravel artisan command directly.

## Usage

```
/artisan <command> [args]
```

## Common Commands

```bash
/artisan migrate              # Run pending migrations
/artisan migrate:fresh        # Reset DB and migrate (dev only)
/artisan db:seed              # Run seeders
/artisan queue:work           # Start RabbitMQ queue listener
/artisan tinker               # Interactive PHP shell
/artisan cache:clear          # Clear all caches
/artisan config:cache         # Cache config files
/artisan l5-swagger:generate  # Regenerate API docs
/artisan make:test Feature\ExampleTest
/artisan make:request StoreUserRequest
```

## Implementation

```bash
cd $CLAUDE_PROJECT_DIR && php artisan {{arguments}}
```
