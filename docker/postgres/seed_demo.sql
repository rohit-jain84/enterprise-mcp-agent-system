-- Clean existing sessions
DELETE FROM approvals;
DELETE FROM messages;
DELETE FROM sessions;

-- Create demo sessions with realistic titles
INSERT INTO sessions (id, user_id, title, total_tokens, total_cost, created_at, updated_at) VALUES
  ('a1111111-1111-1111-1111-111111111111', '5b1c296f-37ec-4651-879b-5b1d5a871bda',
   'Q3 Sprint Planning - Summarize open tickets', 4280, 0.0856,
   NOW() - INTERVAL '2 hours', NOW() - INTERVAL '5 minutes'),

  ('b2222222-2222-2222-2222-222222222222', '5b1c296f-37ec-4651-879b-5b1d5a871bda',
   'Review PR #142 - Auth middleware refactor', 3150, 0.0630,
   NOW() - INTERVAL '1 day', NOW() - INTERVAL '3 hours'),

  ('c3333333-3333-3333-3333-333333333333', '5b1c296f-37ec-4651-879b-5b1d5a871bda',
   'Schedule team sync for next week', 1820, 0.0364,
   NOW() - INTERVAL '2 days', NOW() - INTERVAL '1 day'),

  ('d4444444-4444-4444-4444-444444444444', '5b1c296f-37ec-4651-879b-5b1d5a871bda',
   'Bug triage - Production error logs', 5640, 0.1128,
   NOW() - INTERVAL '3 days', NOW() - INTERVAL '2 days');

-- Messages for Session 1: Sprint Planning
INSERT INTO messages (session_id, role, content, token_count, cost, created_at) VALUES
  ('a1111111-1111-1111-1111-111111111111', 'user',
   'Can you pull up all open tickets in the INGEST project and summarize what is left for this sprint?',
   28, 0.0006, NOW() - INTERVAL '2 hours'),

  ('a1111111-1111-1111-1111-111111111111', 'assistant',
   E'I will fetch the open tickets from the project management system.\n\n**Calling tool:** `list_tickets` on **Project Mgmt** server\n```json\n{"project": "INGEST", "status": "open", "sprint": "current"}\n```\n\nFound **8 open tickets** in the current sprint. Here is the breakdown:\n\n### High Priority (3)\n- **INGEST-341** \u2014 Fix CSV parser timeout on files >500MB\n- **INGEST-338** \u2014 Add retry logic for S3 upload failures\n- **INGEST-335** \u2014 Database migration for new audit columns\n\n### Medium Priority (3)\n- **INGEST-340** \u2014 Update API docs for v2 endpoints\n- **INGEST-339** \u2014 Add unit tests for batch processor\n- **INGEST-336** \u2014 Refactor logging to use structured format\n\n### Low Priority (2)\n- **INGEST-342** \u2014 Clean up deprecated config flags\n- **INGEST-337** \u2014 Add Grafana dashboard for ingestion metrics\n\n**Sprint velocity:** 34 of 55 story points completed (62%). The 3 high-priority items account for 21 remaining points.',
   850, 0.0170, NOW() - INTERVAL '1 hour 55 minutes'),

  ('a1111111-1111-1111-1111-111111111111', 'user',
   'Assign INGEST-341 to Sarah and move INGEST-342 to the backlog',
   18, 0.0004, NOW() - INTERVAL '1 hour 50 minutes'),

  ('a1111111-1111-1111-1111-111111111111', 'assistant',
   E'I will make both changes now.\n\n**Calling tool:** `update_ticket` on **Project Mgmt** server\n```json\n{"ticket_id": "INGEST-341", "assignee": "sarah.chen@acme.com"}\n```\n\u2705 **INGEST-341** assigned to Sarah Chen.\n\n**Calling tool:** `transition_ticket` on **Project Mgmt** server\n```json\n{"ticket_id": "INGEST-342", "status": "backlog"}\n```\n\u26a0\ufe0f **Approval required** \u2014 Moving a ticket out of the current sprint requires manager approval. I have submitted an approval request.\n\nINGEST-341 is assigned. INGEST-342 is pending approval to move to backlog.',
   420, 0.0084, NOW() - INTERVAL '1 hour 48 minutes'),

  ('a1111111-1111-1111-1111-111111111111', 'user',
   'Great, what is Sarah current workload looking like?',
   12, 0.0002, NOW() - INTERVAL '1 hour 40 minutes'),

  ('a1111111-1111-1111-1111-111111111111', 'assistant',
   E'**Calling tool:** `list_tickets` on **Project Mgmt** server\n```json\n{"assignee": "sarah.chen@acme.com", "status": "in_progress"}\n```\n\nSarah currently has **3 tickets in progress**:\n\n| Ticket | Title | Points | Due |\n|--------|-------|--------|-----|\n| INGEST-330 | Implement chunked upload API | 8 | Apr 16 |\n| INGEST-334 | Fix memory leak in stream processor | 5 | Apr 17 |\n| INGEST-341 | Fix CSV parser timeout *(just assigned)* | 8 | Apr 18 |\n\n**Total: 21 story points** \u2014 that is above her average of 16 per sprint. You may want to consider reassigning INGEST-341 or extending the deadline.',
   380, 0.0076, NOW() - INTERVAL '1 hour 38 minutes');

-- Messages for Session 2: PR Review
INSERT INTO messages (session_id, role, content, token_count, cost, created_at) VALUES
  ('b2222222-2222-2222-2222-222222222222', 'user',
   'Review PR #142 on the backend repo. Focus on security implications of the auth middleware changes.',
   22, 0.0004, NOW() - INTERVAL '1 day'),

  ('b2222222-2222-2222-2222-222222222222', 'assistant',
   E'**Calling tool:** `get_pull_request` on **GitHub** server\n```json\n{"repo": "acme/backend", "pr_number": 142}\n```\n\n**Calling tool:** `get_diff` on **GitHub** server\n```json\n{"repo": "acme/backend", "pr_number": 142}\n```\n\n## PR #142 Review: Auth Middleware Refactor\n\n**Author:** @james.wu | **Files changed:** 12 | **+340 / -180**\n\n### Security Findings\n\n\U0001f534 **Critical \u2014 Token validation bypass**\nIn `middleware/auth.py:47`, the new code skips JWT validation for paths starting with `/api/internal/`. However, the internal API endpoints are also accessible externally. This creates an authentication bypass.\n\n```python\n# Line 47 - VULNERABLE\nif request.path.startswith("/api/internal/"):\n    return await call_next(request)\n```\n\n**Recommendation:** Use network-level restrictions or a separate internal auth scheme.\n\n\U0001f7e1 **Medium \u2014 Refresh token not rotated**\nThe refresh endpoint at `auth.py:89` reuses the same refresh token instead of issuing a new one. This violates refresh token rotation best practice (RFC 6749 Section 10.4).\n\n\U0001f7e2 **Low \u2014 Debug logging of token payload**\n`auth.py:52` logs the decoded JWT payload at DEBUG level. In production, this could expose user IDs and claims to log aggregators.\n\n### Overall Assessment\n**Do not merge** until the critical path bypass is fixed. The refresh token rotation should also be addressed before merging.',
   920, 0.0184, NOW() - INTERVAL '23 hours');

-- Messages for Session 3: Calendar scheduling
INSERT INTO messages (session_id, role, content, token_count, cost, created_at) VALUES
  ('c3333333-3333-3333-3333-333333333333', 'user',
   'Find a 1-hour slot next week where the entire backend team is free for a sync meeting',
   20, 0.0004, NOW() - INTERVAL '2 days'),

  ('c3333333-3333-3333-3333-333333333333', 'assistant',
   E'**Calling tool:** `find_free_slots` on **Calendar** server\n```json\n{"attendees": ["sarah.chen@acme.com", "james.wu@acme.com", "admin@acme.com", "priya.patel@acme.com"], "duration_minutes": 60, "range_start": "2026-04-20", "range_end": "2026-04-24"}\n```\n\nFound **3 available slots** next week where all 4 team members are free:\n\n| Day | Time | Notes |\n|-----|------|-------|\n| **Mon Apr 20** | 2:00 PM \u2013 3:00 PM | Best option \u2014 no adjacent meetings |\n| **Wed Apr 22** | 10:00 AM \u2013 11:00 AM | Sarah has a meeting at 11:30 |\n| **Thu Apr 23** | 3:00 PM \u2013 4:00 PM | James has a 1:1 at 4:15 |\n\nWould you like me to create the calendar event for one of these slots?',
   450, 0.0090, NOW() - INTERVAL '2 days' + INTERVAL '5 minutes'),

  ('c3333333-3333-3333-3333-333333333333', 'user',
   'Book Monday 2pm. Title it Backend Team Sync and add a Zoom link.',
   16, 0.0003, NOW() - INTERVAL '2 days' + INTERVAL '10 minutes'),

  ('c3333333-3333-3333-3333-333333333333', 'assistant',
   E'**Calling tool:** `create_event` on **Calendar** server\n```json\n{"title": "Backend Team Sync", "start": "2026-04-20T14:00:00", "end": "2026-04-20T15:00:00", "attendees": ["sarah.chen@acme.com", "james.wu@acme.com", "admin@acme.com", "priya.patel@acme.com"], "conference": "zoom"}\n```\n\u26a0\ufe0f **Approval required** \u2014 Creating calendar events with external attendees requires approval.\n\nI have submitted the approval request. Once approved, the event will be created and invitations sent to all 4 attendees.',
   340, 0.0068, NOW() - INTERVAL '2 days' + INTERVAL '12 minutes');

-- Messages for Session 4: Bug Triage
INSERT INTO messages (session_id, role, content, token_count, cost, created_at) VALUES
  ('d4444444-4444-4444-4444-444444444444', 'user',
   'We are seeing a spike in 500 errors in production. Can you check the error logs and help me triage?',
   24, 0.0005, NOW() - INTERVAL '3 days'),

  ('d4444444-4444-4444-4444-444444444444', 'assistant',
   E'**Calling tool:** `list_issues` on **GitHub** server\n```json\n{"repo": "acme/backend", "labels": ["bug", "production"], "state": "open", "sort": "created", "direction": "desc"}\n```\n\nI found **5 recent production issues**. Cross-referencing with error patterns:\n\n### Critical (Action needed now)\n1. **#289** \u2014 `ConnectionPool exhausted` in payment service\n   - First seen: 2 hours ago | Frequency: ~200/min\n   - Root cause: Missing connection release in `payment_handler.py:134`\n   - **Fix:** Add `finally: conn.release()` block\n\n2. **#287** \u2014 `TimeoutError` on `/api/v2/reports/generate`\n   - First seen: 6 hours ago | Frequency: ~50/min\n   - Root cause: N+1 query in report aggregation (no eager loading)\n\n### Monitoring (Non-critical)\n3. **#290** \u2014 `KeyError: user_preferences` for newly created accounts\n4. **#288** \u2014 Intermittent Redis `ConnectionResetError`\n5. **#286** \u2014 Deprecated API endpoint still receiving traffic\n\nI recommend addressing #289 first \u2014 the connection pool exhaustion is likely causing cascading failures that may be amplifying the other errors.',
   1200, 0.0240, NOW() - INTERVAL '3 days' + INTERVAL '3 minutes');

-- Approval records
INSERT INTO approvals (id, session_id, tool_name, tool_args, reason, status, expires_at, created_at) VALUES
  ('e1111111-1111-1111-1111-111111111111',
   'a1111111-1111-1111-1111-111111111111',
   'transition_ticket',
   '{"ticket_id": "INGEST-342", "status": "backlog"}',
   'Moving ticket out of current sprint requires manager approval',
   'pending',
   NOW() + INTERVAL '24 hours',
   NOW() - INTERVAL '1 hour 48 minutes'),

  ('e2222222-2222-2222-2222-222222222222',
   'c3333333-3333-3333-3333-333333333333',
   'create_event',
   '{"title": "Backend Team Sync", "start": "2026-04-20T14:00:00", "attendees": ["sarah.chen@acme.com", "james.wu@acme.com", "admin@acme.com", "priya.patel@acme.com"]}',
   'Creating calendar events with external attendees requires approval',
   'pending',
   NOW() + INTERVAL '24 hours',
   NOW() - INTERVAL '2 days'),

  ('e3333333-3333-3333-3333-333333333333',
   'b2222222-2222-2222-2222-222222222222',
   'create_issue_comment',
   '{"repo": "acme/backend", "pr_number": 142, "body": "Security review complete - see findings above"}',
   'Posting comments to GitHub PRs requires approval',
   'approved',
   NOW() + INTERVAL '24 hours',
   NOW() - INTERVAL '22 hours');

UPDATE approvals SET status='approved',
  responded_by='5b1c296f-37ec-4651-879b-5b1d5a871bda',
  responded_at=NOW() - INTERVAL '21 hours'
WHERE id='e3333333-3333-3333-3333-333333333333';
