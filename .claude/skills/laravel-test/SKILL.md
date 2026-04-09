---
name: laravel-test
description: >-
  Write comprehensive unit and feature tests for Laravel code.
  Use when testing services, repositories, models, API endpoints, and business logic.
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
paths: "tests/**/*.php,app/**/*.php"
---

# Laravel Testing

Write comprehensive unit and feature tests following PHPUnit + Laravel conventions.

## When to Use

- ✅ Testing API endpoints (Feature tests)
- ✅ Testing business logic in Services/Repositories (Unit tests)
- ✅ Testing Models and database interactions
- ✅ Testing authorization/permissions
- ✅ Testing event dispatching and queue jobs
- ❌ NOT for testing framework internals or third-party packages

## Test Structure

### Feature Tests
**Location:** `tests/Feature/`
**Purpose:** Test complete workflows, API endpoints, database interactions

```php
// tests/Feature/UserApiTest.php
namespace Tests\Feature;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;
use App\Models\User;

class UserApiTest extends TestCase {
    use RefreshDatabase;  // Rollback DB after each test

    public function test_get_users_returns_list() {
        User::factory()->count(3)->create();
        
        $response = $this->getJson('/api/v1/users');
        
        $response->assertStatus(200)
                 ->assertJsonCount(3, 'data')
                 ->assertJsonStructure(['data' => ['*' => ['id', 'name', 'email']]]);
    }

    public function test_create_user_with_valid_data() {
        $response = $this->postJson('/api/v1/users', [
            'name' => 'John Doe',
            'email' => 'john@example.com',
            'password' => 'password123',
        ]);

        $response->assertStatus(201)
                 ->assertJson(['data' => ['name' => 'John Doe', 'email' => 'john@example.com']]);
        $this->assertDatabaseHas('users', ['email' => 'john@example.com']);
    }

    public function test_create_user_with_invalid_email() {
        $response = $this->postJson('/api/v1/users', [
            'name' => 'John Doe',
            'email' => 'invalid-email',
            'password' => 'password123',
        ]);

        $response->assertStatus(422)
                 ->assertJsonValidationErrors(['email']);
    }

    public function test_update_user() {
        $user = User::factory()->create(['name' => 'Old Name']);
        
        $response = $this->putJson("/api/v1/users/{$user->id}", [
            'name' => 'New Name',
        ]);

        $response->assertStatus(200);
        $this->assertEquals('New Name', $user->fresh()->name);
    }

    public function test_delete_user() {
        $user = User::factory()->create();
        
        $response = $this->deleteJson("/api/v1/users/{$user->id}");

        $response->assertStatus(204);
        $this->assertNull(User::find($user->id));
    }

    public function test_unauthorized_user_cannot_access() {
        $response = $this->getJson('/api/v1/users');
        $response->assertStatus(401);
    }

    public function test_user_can_only_update_own_profile() {
        $user1 = User::factory()->create();
        $user2 = User::factory()->create();
        
        $this->actingAs($user1)
             ->putJson("/api/v1/users/{$user2->id}", ['name' => 'Hacked'])
             ->assertStatus(403);
    }
}
```

### Unit Tests
**Location:** `tests/Unit/`
**Purpose:** Test individual components (Services, Repositories, Models)

```php
// tests/Unit/UserServiceTest.php
namespace Tests\Unit;
use PHPUnit\Framework\TestCase;
use Mockery;
use App\Services\UserService;
use App\Repositories\UserRepository;
use App\Models\User;

class UserServiceTest extends TestCase {
    public function test_service_creates_user() {
        // Mock the repository
        $repository = Mockery::mock(UserRepository::class);
        $repository->shouldReceive('create')
                   ->with(['name' => 'John', 'email' => 'john@example.com'])
                   ->once()
                   ->andReturn(new User(['id' => 1, 'name' => 'John']));

        $service = new UserService($repository);
        $result = $service->createUser(['name' => 'John', 'email' => 'john@example.com']);

        $this->assertEquals('John', $result->name);
        $this->assertEquals(1, $result->id);
    }

    public function test_service_updates_user() {
        $repository = Mockery::mock(UserRepository::class);
        $user = new User(['id' => 1, 'name' => 'Old Name']);
        
        $repository->shouldReceive('update')
                   ->with(1, ['name' => 'New Name'])
                   ->once()
                   ->andReturn($user->setAttribute('name', 'New Name'));

        $service = new UserService($repository);
        $result = $service->updateUser(1, ['name' => 'New Name']);

        $this->assertEquals('New Name', $result->name);
    }

    public function test_service_deletes_user() {
        $repository = Mockery::mock(UserRepository::class);
        $repository->shouldReceive('delete')
                   ->with(1)
                   ->once()
                   ->andReturn(true);

        $service = new UserService($repository);
        $result = $service->deleteUser(1);

        $this->assertTrue($result);
    }
}
```

### Test Base Class
```php
// tests/TestCase.php
namespace Tests;
use Illuminate\Foundation\Testing\TestCase as BaseTestCase;

abstract class TestCase extends BaseTestCase {
    use CreatesApplication;

    protected function setUp(): void {
        parent::setUp();
        // Setup common test state
    }
}
```

## Test Traits

### RefreshDatabase
Rolls back database after each test:
```php
use Illuminate\Foundation\Testing\RefreshDatabase;

class UserTest extends TestCase {
    use RefreshDatabase;  // ← Auto rollback/refresh DB
}
```

### WithoutMiddleware
Skip middleware (auth, CORS, etc.):
```php
public function test_endpoint_without_auth() {
    $this->withoutMiddleware()
         ->getJson('/api/v1/users')
         ->assertStatus(200);
}
```

### AuthenticatedUser
Act as authenticated user:
```php
public function test_authenticated_user_action() {
    $user = User::factory()->create();
    
    $response = $this->actingAs($user)
                     ->getJson('/api/v1/users');
    
    $response->assertStatus(200);
}
```

## Assertions

### HTTP Status
```php
$response->assertStatus(200);
$response->assertStatus(201);
$response->assertStatus(204);
$response->assertStatus(400);
$response->assertStatus(401);
$response->assertStatus(403);
$response->assertStatus(404);
$response->assertStatus(500);
```

### JSON Structure
```php
$response->assertJson(['data' => ['id' => 1, 'name' => 'John']]);
$response->assertJsonCount(5, 'data');
$response->assertJsonStructure(['data' => ['*' => ['id', 'name']]]);
$response->assertJsonMissing(['password']);
$response->assertJsonValidationErrors(['email', 'name']);
```

### Database
```php
$this->assertDatabaseHas('users', ['email' => 'john@example.com']);
$this->assertDatabaseMissing('users', ['email' => 'deleted@example.com']);
$this->assertDatabaseCount('users', 5);
```

### Collections/Models
```php
$response->assertJsonCount(5);
$response->assertJsonCount(10, 'data');
$response->assertJsonPath('data.0.name', 'John');
```

## Factories & Seeders

### Create Test Data with Factories
```php
// database/factories/UserFactory.php
namespace Database\Factories;
use Illuminate\Database\Eloquent\Factories\Factory;
use App\Models\User;

class UserFactory extends Factory {
    protected $model = User::class;

    public function definition() {
        return [
            'name' => $this->faker->name(),
            'email' => $this->faker->unique()->safeEmail(),
            'password' => bcrypt('password'),
            'created_at' => now(),
        ];
    }

    public function admin() {
        return $this->state(function (array $attributes) {
            return ['role' => 'admin'];
        });
    }
}
```

### Use Factory in Tests
```php
// Create single instance
$user = User::factory()->create();

// Create multiple
$users = User::factory()->count(5)->create();

// Use custom state
$admin = User::factory()->admin()->create();

// With specific attributes
$user = User::factory()->create(['name' => 'John Doe']);
```

## Mocking & Stubbing

### Mock Repository
```php
$mock = Mockery::mock(UserRepository::class);
$mock->shouldReceive('find')
     ->with(1)
     ->once()
     ->andReturn(new User(['id' => 1, 'name' => 'John']));
```

### Mock External API
```php
$mock = Mockery::mock('alias:App\External\GoogleApi');
$mock->shouldReceive('getCalendar')
     ->andReturn(['events' => []]);
```

### Spy on Events
```php
Event::fake();
Event::assertDispatched(UserCreated::class);
Event::assertNotDispatched(UserDeleted::class);
```

## Running Tests

### Run all tests
```bash
php artisan test
./vendor/bin/phpunit
```

### Run specific test file
```bash
php artisan test tests/Feature/UserTest.php
./vendor/bin/phpunit tests/Feature/UserTest.php
```

### Run tests matching pattern
```bash
php artisan test --filter=test_create_user
./vendor/bin/phpunit --filter=test_create_user
```

### Run unit tests only
```bash
php artisan test --testsuite=unit
```

### Run feature tests only
```bash
php artisan test --testsuite=feature
```

### Generate coverage report
```bash
php artisan test --coverage-html coverage/
# Open coverage/index.html in browser
```

## Best Practices

1. **One assertion per test** (or logically related)
   ```php
   public function test_user_creation_and_notification() {
       // OK: Logically related
       $user = User::factory()->create();
       $this->assertDatabaseHas('users', ...);
       Notification::assertSent(...);
   }
   ```

2. **Use AAA pattern** (Arrange, Act, Assert)
   ```php
   public function test_update_user() {
       // Arrange
       $user = User::factory()->create(['name' => 'Old']);
       
       // Act
       $this->actingAs($user)
            ->putJson("/api/v1/users/{$user->id}", ['name' => 'New']);
       
       // Assert
       $this->assertEquals('New', $user->fresh()->name);
   }
   ```

3. **Test error cases**
   ```php
   public function test_invalid_input_returns_422() {
       $response = $this->postJson('/api/v1/users', ['email' => 'invalid']);
       $response->assertStatus(422);
       $response->assertJsonValidationErrors(['email']);
   }
   ```

4. **Test authorization**
   ```php
   public function test_unauthorized_user_cannot_delete() {
       $user = User::factory()->create();
       $other = User::factory()->create();
       
       $this->actingAs($other)
            ->deleteJson("/api/v1/users/{$user->id}")
            ->assertStatus(403);
   }
   ```

5. **Use descriptive test names**
   ```php
   // ✅ Good
   public function test_create_user_with_valid_data_returns_201() { ... }
   
   // ❌ Bad
   public function test_user() { ... }
   ```

## Configuration

**Config file:** `phpunit.xml`

```xml
<phpunit>
    <testsuites>
        <testsuite name="feature">
            <directory suffix="Test.php">./tests/Feature</directory>
        </testsuite>
        <testsuite name="unit">
            <directory suffix="Test.php">./tests/Unit</directory>
        </testsuite>
    </testsuites>
</phpunit>
```

## Common Pitfalls

❌ **Don't test framework features**
```php
// Bad: Testing Laravel, not your code
public function test_eloquent_creates_record() {
    User::create(['name' => 'John']);
    $this->assertDatabaseHas('users', ...);
}
```

✅ **Instead test your code**
```php
// Good: Testing your service/repository
public function test_user_service_validates_before_creating() {
    $service = new UserService($repo);
    $result = $service->createUser(['invalid' => 'data']);
    $this->assertFalse($result);
}
```

❌ **Don't skip RefreshDatabase for database tests**
```php
// Bad: Tests interfere with each other
public function test_user_creation() {
    User::create(['email' => 'test@example.com']);
}
```

✅ **Always use RefreshDatabase**
```php
// Good: Each test starts with clean DB
use RefreshDatabase;
```

❌ **Don't test implementation details**
```php
// Bad: Too specific
$this->assertEquals(
    "Hello " . $user->first_name . " " . $user->last_name,
    $user->getFullName()
);
```

✅ **Test behavior instead**
```php
// Good: Test what matters
$this->assertEquals('John Doe', $user->getFullName());
```
