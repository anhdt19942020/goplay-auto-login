---
name: make-crud
description: Generate complete CRUD structure (Model, Migration, Controller, Service, Repository, Transformer, Request, Route)
---

# /make-crud

Generates a complete CRUD module following edutalk-api architecture:
- Eloquent Model with migrations
- Repository (interface + implementation)
- Service layer
- Controller (resourceful)
- FormRequest (validation)
- Fractal Transformer
- API routes

## Usage

```
/make-crud ModelName [--mongodb] [--domain=Academic]
```

## Examples

```
/make-crud User                          # Standard MySQL model
/make-crud Log --mongodb                 # MongoDB collection model
/make-crud ClassRoom --domain=Classrooms # Domain-specific
/make-crud PaymentSchedule --domain=Finances
```

## What Gets Generated

For `/make-crud User`:

1. **Model:** `app/Models/User.php`
2. **Migration:** `database/migrations/YYYY_MM_DD_HHMMSS_create_users_table.php`
3. **Repository Interface:** `app/Repositories/UserRepository.php`
4. **Repository Implementation:** `app/Repositories/Eloquent/UserRepository.php`
5. **Service:** `app/Services/UserService.php`
6. **Controller:** `app/Http/Controllers/UserController.php` (resourceful)
7. **Request:** `app/Http/Requests/StoreUserRequest.php`
8. **Transformer:** `app/Transformers/UserTransformer.php`
9. **Route:** Added to `routes/api.php` as RESTful resource

## Generated Code Patterns

### Model
```php
class User extends Model
{
    use HasFactory;
    protected $fillable = ['name', 'email', 'password'];
    protected $hidden = ['password'];
}
```

### Repository
```php
interface UserRepository {
    public function all();
    public function find($id);
    public function create(array $data);
    public function update($id, array $data);
    public function delete($id);
}
```

### Service
```php
class UserService {
    public function __construct(UserRepository $repo) { ... }
    public function createUser(array $data) { ... }
    public function updateUser($id, array $data) { ... }
}
```

### Controller
```php
class UserController extends Controller {
    public function index() { return $users; }
    public function store(StoreUserRequest $request) { ... }
    public function show(User $user) { ... }
    public function update(UpdateUserRequest $request, User $user) { ... }
    public function destroy(User $user) { ... }
}
```

### Transformer
```php
class UserTransformer extends TransformerAbstract {
    public function transform(User $user) {
        return [
            'id' => $user->id,
            'name' => $user->name,
            'email' => $user->email,
        ];
    }
}
```

### Route
```php
Route::apiResource('users', UserController::class);
```

## After Generation

1. ✅ Add columns to migration (edit the migration file)
2. ✅ Run migration: `/artisan migrate`
3. ✅ Update Request validation rules: `app/Http/Requests/StoreUserRequest.php`
4. ✅ Add transformer fields: `app/Transformers/UserTransformer.php`
5. ✅ Implement business logic in Service: `app/Services/UserService.php`

## Domain-Specific Generation

Use `--domain=DomainName` to organize in subdirectories:

```
/make-crud Student --domain=Academic
  → app/Domain/Academic/Models/Student.php
  → app/Domain/Academic/Services/StudentService.php
  → app/Http/Controllers/Academic/StudentController.php
  → routes/academic.php
```
