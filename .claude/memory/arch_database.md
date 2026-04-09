---
name: Database Architecture & Patterns
description: Mongoose, MongoDB, schema design, relationships
type: reference
---

## Database Standards

**ORM / Query Language**
- Use Mongoose for schema & validation
- Define schemas with TypeScript types
- Leverage Mongoose middleware for hooks
- Use lean() for read-only queries (performance)

**Schema Design**
- Collection names: `snake_case` (user_accounts, game_matches)
- Field names: `camelCase` (firstName, createdAt)
- Always include timestamps: `createdAt`, `updatedAt`
- Use indexes on frequently queried fields

**Security**
- Never hardcode credentials (use .env)
- Protect connection strings
- Use environment-specific configs
- Validate/sanitize input before queries
- No sensitive data in logs

**Performance**
- Create indexes on: foreign key fields, search fields
- Use `.select()` to fetch only needed fields
- Use `.lean()` for read-only operations
- Batch operations when possible
- Monitor query performance

## How to Apply

When designing schema: use TypeScript interfaces as source of truth
When querying: select only needed fields
When indexing: measure impact before adding
When securing: use .env for all secrets
When optimizing: profile query performance first
