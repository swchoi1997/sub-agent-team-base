#!/usr/bin/env bash
# company db-guard — Claude Code PreToolUse hook for the Bash tool.
#
# Policy (docs/company/profile.md, playbooks/common-rules.md §3):
#   databases: only SELECT / read-only inspection is free; everything else needs a human.
# This hook does not decide; it asks. When a Bash command looks like a database write,
# a migration, or a restore, it returns permissionDecision "ask" so the human confirms it.
# Commands it cannot inspect (SQL from a file or stdin redirect) are asked too.
#
# Installed by /company:init into <project>/.claude/hooks/ and registered in
# <project>/.claude/settings.json. Requires bash; uses jq or python3 if present.

set -u
input="$(cat)"

extract_command() {
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null && return
  fi
  if command -v python3 >/dev/null 2>&1; then
    printf '%s' "$input" | python3 -c 'import json,sys
try:
    print(json.load(sys.stdin).get("tool_input",{}).get("command",""))
except Exception:
    pass' 2>/dev/null && return
  fi
  # Fallback: inspect the raw payload.
  printf '%s' "$input"
}

cmd="$(extract_command)"
[ -z "$cmd" ] && exit 0
lc="$(printf '%s' "$cmd" | tr '[:upper:]' '[:lower:]')"

ask() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"[company db-guard] %s Only SELECT is free; this needs human approval (temporary test DBs: approve if this targets one)."}}\n' "$1"
  exit 0
}

has() { printf '%s' "$lc" | grep -Eq -- "$1"; }
has_word() { printf '%s' "$lc" | grep -Ewq -- "$1"; }

# 1. Migration / schema / seed / restore tools: always ask.
migration_re='flyway[^|;&]*(migrate|clean|repair|baseline|undo)|flyway(migrate|clean|repair|baseline|undo)|flyway:(migrate|clean|repair|baseline|undo)'
migration_re="$migration_re"'|liquibase[^|;&]*(update|rollback|drop-?all|changelog-?sync)|liquibase:(update|rollback|dropall)'
migration_re="$migration_re"'|prisma[^|;&]*(migrate +(dev|deploy|reset|resolve)|db +(push|seed|execute))'
migration_re="$migration_re"'|(rails|rake|bin/rails)[^|;&]*db:(migrate|seed|reset|drop|setup|rollback|schema:load|prepare)'
migration_re="$migration_re"'|alembic[^|;&]*(upgrade|downgrade|stamp)|manage\.py[^|;&]*(migrate|flush|loaddata|sqlflush)'
migration_re="$migration_re"'|knex[^|;&]*(migrate:(latest|up|down|rollback)|seed:run)|sequelize(-cli)?[^|;&]*db:(migrate|seed|drop)'
migration_re="$migration_re"'|typeorm[^|;&]*(migration:(run|revert)|schema:(sync|drop))|drizzle-kit[^|;&]*(push|migrate|drop)'
migration_re="$migration_re"'|goose[^|;&]*(up|down|reset|redo)|dbmate[^|;&]*(up|down|migrate|rollback|drop|load)'
migration_re="$migration_re"'|sqlx[^|;&]*migrate +(run|revert)|diesel[^|;&]*(migration +(run|revert|redo)|database +(reset|setup))'
migration_re="$migration_re"'|(^|[^a-z])migrate[^|;&]*-database|atlas[^|;&]*(migrate +apply|schema +apply)'
migration_re="$migration_re"'|pg_restore|mongorestore|mongoimport|mysqlimport|redis-cli[^|;&]*--pipe'
if has "$migration_re"; then
  ask "Migration/seed/restore command detected."
fi

# 2. Database clients.
client_re='(^|[^a-z0-9_-])(psql|mysql|mariadb|mongosh|mongo|sqlite3|redis-cli|cqlsh|clickhouse-client|clickhouse|sqlcmd|duckdb|cockroach +sql|usql)([^a-z0-9_-]|$)'
if has "$client_re"; then
  # SQL that cannot be inspected: from a file or a stdin redirect.
  if has '(^|[[:space:]])(-f|--file|-i|--input|source)([[:space:]=]|$)|<[^<(]|\\i[[:space:]]|\.read[[:space:]]'; then
    ask "Database client reads SQL from a file or stdin; contents cannot be inspected."
  fi
  sql_write='insert|update|delete|merge|upsert|replace|create|alter|drop|truncate|rename|grant|revoke|copy|into|vacuum|reindex|cluster|call|execute|import|load|attach|detach|pragma|restore|comment'
  if has_word "$sql_write"; then
    ask "Database write or DDL detected in a database client command."
  fi
  mongo_write='insert|insertone|insertmany|update|updateone|updatemany|replaceone|deleteone|deletemany|remove|drop|dropdatabase|dropindex|createcollection|createindex|renamecollection|bulkwrite|findoneandupdate|findoneanddelete|findoneandreplace|findandmodify'
  if has '(mongosh|mongo)([^a-z]|$)' && has_word "$mongo_write"; then
    ask "MongoDB write detected."
  fi
  redis_write='set|setex|setnx|mset|msetnx|getset|getdel|append|del|unlink|expire|pexpire|persist|rename|renamenx|incr|incrby|decr|decrby|hset|hmset|hdel|hincrby|lpush|rpush|lpop|rpop|lset|lrem|ltrim|sadd|srem|spop|smove|zadd|zrem|zincrby|xadd|xdel|xtrim|flushdb|flushall|restore|migrate|copy|move|swapdb|eval|evalsha|fcall|config|script|function'
  if has 'redis-cli' && has_word "$redis_write"; then
    ask "Redis write detected."
  fi
fi

exit 0
