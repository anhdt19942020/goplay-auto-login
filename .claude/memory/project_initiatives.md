---
name: Current Project Initiatives
description: Active work streams and priorities for 2026 Q2
type: project
---

## Active Work Streams

### 1. Match Monitoring APIs (In Development)
- APIs for real-time match state tracking
- Letter-cards scoring APIs: submit-answer, submit-pronunciation
- Navigation: navigate-question, get-state endpoints
- **Status**: API layer implemented, needs integration testing
- **Why**: Core feature for competitive gaming

### 2. Socket.io Performance Optimization (Planned)
- Optimize real-time updates for high concurrent users
- Current concern: Scalability with large participant counts
- **Why**: Users reporting latency issues at >100 concurrent connections
- **Timeline**: After match monitoring complete

## Implementation Priorities

1. Complete match monitoring API tests (unit + integration)
2. Document scoring APIs with examples
3. Performance profile Socket.io connections
4. Optimize broadcast messages for >1000 users

## How to Apply

When suggesting API changes: prioritize match monitoring completeness
When optimizing: Socket.io is secondary but track metrics
When testing: include high-load scenarios
