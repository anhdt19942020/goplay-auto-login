---
name: API Design Principles
description: RESTful design, versioning, status codes, documentation
type: reference
---

## API Standards

**URL Structure**
- Version endpoints: `/api/v1/` (or v2, v3 if breaking changes)
- Resource-based: `/api/v1/matches`, `/api/v1/matches/:id`
- Actions as verbs in paths: `/api/v1/matches/:id/submit-answer`

**HTTP Methods**
- GET: Retrieve resource (no side effects)
- POST: Create resource
- PUT/PATCH: Update resource
- DELETE: Remove resource

**Response Format**
- Always JSON
- Success: `{ data: {...}, success: true }`
- Error: `{ error: "message", code: "ERROR_CODE", status: 400 }`
- Include HTTP status codes: 200, 201, 400, 404, 500

**Documentation**
- Every endpoint must have example request/response
- Include error cases and status codes
- Document Socket.io events separately
- Keep docs in code comments or `/docs` folder

## How to Apply

When designing endpoint: prefix with `/api/v1/`
When changing behavior: increment version if breaking
When documenting: include all status codes possible
When responding: use consistent error format
