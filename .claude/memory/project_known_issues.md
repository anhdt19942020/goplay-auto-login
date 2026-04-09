---
name: Known Issues & Workarounds
description: Technical debt, performance concerns, gaps
type: project
---

## Performance Issues

### Socket.io Scalability
- **Issue**: Performance degrades with >100 concurrent users
- **Current**: Room-based broadcasts are inefficient
- **Workaround**: Limit room size to 50 users currently
- **Timeline**: Q2 2026 optimization sprint

### API Response Times
- **Issue**: Some scoring endpoints slow under load
- **Current**: No caching implemented
- **Workaround**: Use database connection pooling
- **Fix**: Add Redis caching for frequently accessed states

## Documentation Gaps

- Match monitoring API examples incomplete
- Socket.io event payload documentation missing
- Test coverage for high-concurrency scenarios low

## How to Apply

When adding features: be mindful of Socket.io broadcast impact
When optimizing: measure before/after with >100 concurrent users
When documenting: include payload examples and error cases
