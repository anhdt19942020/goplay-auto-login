---
name: laravel-crud
description: >-
  Generate complete CRUD modules following edutalk-api's Repository/Service/Transformer architecture.
  Use when building new features, adding data models, or implementing RESTful API endpoints.
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
paths: "app/**/*.php,routes/**/*.php,database/migrations/**/*.php"
---

# Laravel CRUD Generation

Generate complete CRUD modules for edutalk-api following established patterns:
- **Repository Pattern** (interface + Eloquent implementation)
- **Service Layer** (business logic, validation, events)
- **Fractal Transformers** (API response formatting)
- **FormRequests** (input validation)
- **Controller** (resourceful REST)
- **Model & Migration**
- **API Routes** (RESTful)

## When to Use

- ✅ Creating new entities (User, ClassRoom, PaymentSchedule, etc.)
- ✅ Adding new domains (Academic, Finances, Classrooms, Study)
- ✅ Implementing standard CRUD operations
- ✅ Building API endpoints with validation and authorization
- ❌ NOT for complex business logic that spans multiple models
- ❌ NOT for non-standard operations (use services directly instead)

## Generation Pattern

### 1. Model & Migration
```bash
php artisan make:model ModelName -m
```

Edit migration (`database/migrations/`):
```php
Schema::create('model_names', function (Blueprint $table) {
    $table->id();
    $table->string('name');
    $table->string('email')->unique();
    $table->timestamps();
});
```

Eloquent model (`app/Models/ModelName.php`):
```php
namespace App\Models;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class ModelName extends Model {
    use HasFactory;
    protected $fillable = ['name', 'email'];
}
```

### 2. Repository Interface & Implementation
Interface (`app/Repositories/ModelNameRepository.php`):
```php
namespace App\Repositories;

interface ModelNameRepository {
    public function all();
    public function find($id);
    public function findByEmail($email);
    public function create(array $data);
    public function update($id, array $data);
    public function delete($id);
}
```

Implementation (`app/Repositories/Eloquent/ModelNameRepository.php`):
```php
namespace App\Repositories\Eloquent;
use App\Models\ModelName;
use App\Repositories\ModelNameRepository as RepositoryContract;

class ModelNameRepository implements RepositoryContract {
    protected $model;

    public function __construct(ModelName $model) {
        $this->model = $model;
    }

    public function all() {
        return $this->model->all();
    }

    public function find($id) {
        return $this->model->find($id);
    }

    public function create(array $data) {
        return $this->model->create($data);
    }

    public function update($id, array $data) {
        $model = $this->find($id);
        $model->update($data);
        return $model;
    }

    public function delete($id) {
        return $this->model->destroy($id);
    }
}
```

### 3. Service Layer
Service (`app/Services/ModelNameService.php`):
```php
namespace App\Services;
use App\Repositories\ModelNameRepository;

class ModelNameService {
    protected $repository;

    public function __construct(ModelNameRepository $repository) {
        $this->repository = $repository;
    }

    public function getAllModelNames() {
        return $this->repository->all();
    }

    public function getModelNameById($id) {
        return $this->repository->find($id);
    }

    public function createModelName(array $data) {
        // Validate, process, then create
        return $this->repository->create($data);
    }

    public function updateModelName($id, array $data) {
        return $this->repository->update($id, $data);
    }

    public function deleteModelName($id) {
        return $this->repository->delete($id);
    }
}
```

### 4. FormRequest (Validation)
StoreRequest (`app/Http/Requests/StoreModelNameRequest.php`):
```php
namespace App\Http\Requests;
use Illuminate\Foundation\Http\FormRequest;

class StoreModelNameRequest extends FormRequest {
    public function authorize() {
        return auth()->check();
    }

    public function rules() {
        return [
            'name' => 'required|string|max:255',
            'email' => 'required|email|unique:model_names',
        ];
    }
}
```

UpdateRequest (`app/Http/Requests/UpdateModelNameRequest.php`):
```php
public function rules() {
    return [
        'name' => 'sometimes|string|max:255',
        'email' => 'sometimes|email|unique:model_names,email,' . $this->model_name->id,
    ];
}
```

### 5. Transformer (API Response)
Transformer (`app/Transformers/ModelNameTransformer.php`):
```php
namespace App\Transformers;
use App\Models\ModelName;
use League\Fractal\TransformerAbstract;

class ModelNameTransformer extends TransformerAbstract {
    public function transform(ModelName $model) {
        return [
            'id' => $model->id,
            'name' => $model->name,
            'email' => $model->email,
            'createdAt' => $model->created_at->toIso8601String(),
        ];
    }
}
```

### 6. Controller (Resourceful)
Controller (`app/Http/Controllers/ModelNameController.php`):
```php
namespace App\Http\Controllers;
use App\Models\ModelName;
use App\Services\ModelNameService;
use App\Http\Requests\StoreModelNameRequest;
use App\Http\Requests\UpdateModelNameRequest;
use App\Transformers\ModelNameTransformer;
use Illuminate\Http\Request;

class ModelNameController extends Controller {
    protected $service;

    public function __construct(ModelNameService $service) {
        $this->service = $service;
        $this->middleware('auth:api');
    }

    public function index() {
        $models = $this->service->getAllModelNames();
        return $this->response->collection($models, new ModelNameTransformer());
    }

    public function store(StoreModelNameRequest $request) {
        $model = $this->service->createModelName($request->validated());
        return $this->response->item($model, new ModelNameTransformer())
                              ->setStatusCode(201);
    }

    public function show(ModelName $model) {
        return $this->response->item($model, new ModelNameTransformer());
    }

    public function update(UpdateModelNameRequest $request, ModelName $model) {
        $updated = $this->service->updateModelName($model->id, $request->validated());
        return $this->response->item($updated, new ModelNameTransformer());
    }

    public function destroy(ModelName $model) {
        $this->service->deleteModelName($model->id);
        return response()->noContent();
    }
}
```

### 7. Routes (RESTful)
Routes (`routes/api.php`):
```php
Route::apiResource('model-names', ModelNameController::class);
// Generates: GET /model-names, POST /model-names, 
//            GET /model-names/{model_name}, PUT /model-names/{model_name}, 
//            DELETE /model-names/{model_name}
```

Or domain-specific route file (`routes/domain.php`):
```php
Route::middleware(['auth:api'])->group(function () {
    Route::apiResource('model-names', ModelNameController::class);
});
```

## Post-Generation Checklist

1. ✅ Run migration: `php artisan migrate`
2. ✅ Add columns/indexes to migration as needed
3. ✅ Update FormRequest validation rules
4. ✅ Update Transformer with all desired output fields
5. ✅ Add authorization checks in Controller (e.g., `$this->authorize('update', $model)`)
6. ✅ Add Service-level business logic (validation, events, queued jobs)
7. ✅ Test endpoints: Feature test in `tests/Feature/`
8. ✅ Regenerate API docs: `npm run swagger`
9. ✅ Format code: `composer pint`

## Examples from Project

### Academic Domain
```bash
# Generate Student CRUD
php artisan make:model Student -m
# → app/Domain/Academic/Models/Student.php
# → app/Services/Academic/StudentService.php
# → app/Repositories/StudentRepository.php
# → routes/academic.php
```

### Finance Domain
```bash
# Generate PaymentSchedule CRUD
php artisan make:model PaymentSchedule -m
# → app/Domain/Finances/Models/PaymentSchedule.php
# → app/Services/Finances/PaymentScheduleService.php
```

## Common Patterns & Tweaks

### Soft Deletes
Add to Model:
```php
use SoftDeletes;
protected $dates = ['deleted_at'];
```

Add to migration:
```php
$table->softDeletes();
```

### Timestamps
Model (default):
```php
public $timestamps = true;
```

### Relationships
Model:
```php
public function classes() {
    return $this->hasMany(ClassRoom::class);
}
```

Transformer (include related data):
```php
protected $availableIncludes = ['classes'];

public function includeClasses(Student $student) {
    return $this->collection($student->classes, new ClassRoomTransformer());
}
```

### Scopes
Model:
```php
public function scopeActive($query) {
    return $query->where('status', 'active');
}
```

Usage:
```php
Student::active()->get();
```

### Authorization
Controller:
```php
public function update(UpdateStudentRequest $request, Student $student) {
    $this->authorize('update', $student);  // Uses StudentPolicy
    ...
}
```

Policy (`app/Policies/StudentPolicy.php`):
```php
public function update(User $user, Student $student) {
    return $user->id === $student->teacher_id;
}
```

## Testing CRUD

Feature test (`tests/Feature/StudentTest.php`):
```php
public function test_create_student() {
    $response = $this->postJson('/api/v1/students', [
        'name' => 'John',
        'email' => 'john@example.com',
    ]);
    $response->assertStatus(201);
    $this->assertDatabaseHas('students', ['email' => 'john@example.com']);
}

public function test_update_student() {
    $student = Student::factory()->create();
    $response = $this->putJson("/api/v1/students/{$student->id}", [
        'name' => 'Jane',
    ]);
    $response->assertStatus(200);
    $this->assertEquals('Jane', $student->fresh()->name);
}
```

Unit test (`tests/Unit/StudentServiceTest.php`):
```php
public function test_service_creates_student() {
    $repo = $this->createMock(StudentRepository::class);
    $service = new StudentService($repo);
    $repo->expects($this->once())->method('create')
         ->with(['name' => 'John', 'email' => 'john@example.com'])
         ->willReturn(new Student(['id' => 1, 'name' => 'John']));
    
    $result = $service->createStudent(['name' => 'John', 'email' => 'john@example.com']);
    $this->assertEquals('John', $result->name);
}
```

## Troubleshooting

- **Model not found in route binding:** Add route model binding in `RouteServiceProvider`
- **Transformer not applying:** Check response uses `$this->response->item()` or `->collection()`
- **Repository not resolving:** Register in service provider (`app/Providers/AppServiceProvider.php`)
- **Validation not working:** Ensure FormRequest is injected in controller method signature
