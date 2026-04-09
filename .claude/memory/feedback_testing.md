---
name: Testing Requirements & Approach
description: Unit, integration, API testing standards
type: feedback
---

## Testing Standards

**Test Framework**
- Unit tests: Jest with TypeScript support
- API tests: Supertest for HTTP endpoints
- Test files: `*.test.ts` or `*.spec.ts`
- Coverage minimum: Critical paths must be tested

**What to Test**
- All API endpoints (request/response validation)
- Service layer business logic
- Error handling & edge cases
- Database operations with real DB connection
- Socket.io events for real-time features

**Integration Tests**
- Use real MongoDB (not mocks)
- Test full request → service → database flow
- Include authentication if applicable
- Test concurrent requests

## How to Apply

When adding API: write tests before merging
When optimizing: ensure tests catch regressions
When refactoring: keep test coverage >80%
When finding bugs: write test that reproduces before fixing
When pairing services: test integration not isolation
