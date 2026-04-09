---
name: test
description: Run PHPUnit tests with coverage and filtering options
---

# /test

Run tests via PHPUnit with various options.

## Usage

```
/test [--file=path/to/test.php] [--filter=testName] [--coverage] [--unit|--feature]
```

## Examples

```bash
/test                                    # Run all tests
/test --file=tests/Feature/UserTest.php  # Run specific test file
/test --filter=test_user_login           # Run tests matching pattern
/test --unit                             # Run unit tests only
/test --feature                          # Run feature tests only
/test --coverage                         # Generate HTML coverage report
```

## Implementation

```bash
cd $CLAUDE_PROJECT_DIR && php artisan test [options]
```

## Test Structure

### Feature Tests
Location: `tests/Feature/`
Test: API endpoints, database interactions, full workflows

```php
public function test_create_user_via_api() {
    $response = $this->postJson('/api/v1/users', [
        'name' => 'John Doe',
        'email' => 'john@example.com',
    ]);
    $response->assertStatus(201);
    $this->assertDatabaseHas('users', ['email' => 'john@example.com']);
}
```

### Unit Tests
Location: `tests/Unit/`
Test: Services, Repositories, Models, business logic

```php
public function test_user_service_creates_user() {
    $repo = $this->createMock(UserRepository::class);
    $service = new UserService($repo);
    $repo->expects($this->once())->method('create');
    $service->createUser(['name' => 'Test']);
}
```

## Coverage Report

Generate HTML coverage:

```bash
/test --coverage
```

Reports saved to `coverage/index.html` — open in browser.

## Running via Bash

```bash
php artisan test                                          # All tests
./vendor/bin/phpunit tests/Feature/UserTest.php          # Specific file
./vendor/bin/phpunit --filter=test_login                 # Pattern
./vendor/bin/phpunit --coverage-html coverage/           # Coverage
```
