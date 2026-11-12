#!/usr/bin/env bash
# Tests for plugins/company/project-hooks/db-guard.sh
# Usage: bash tests/db-guard.test.sh   (exit 0 = all pass)
set -u
HOOK="$(cd "$(dirname "$0")/.." && pwd)/plugins/company/project-hooks/db-guard.sh"
pass=0; fail=0

run() { # $1 = command string
  if command -v jq >/dev/null 2>&1; then
    jq -cn --arg c "$1" '{tool_name:"Bash",tool_input:{command:$c}}' | bash "$HOOK"
  else
    python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "$1" | bash "$HOOK"
  fi
}
expect() { # $1 = ask|allow, $2 = command
  out="$(run "$2")"
  if printf '%s' "$out" | grep -q '"permissionDecision":"ask"'; then got=ask; else got=allow; fi
  if [ "$got" = "$1" ]; then pass=$((pass+1)); else fail=$((fail+1)); printf 'FAIL expected=%s got=%s :: %s\n' "$1" "$got" "$2"; fi
}

# --- allowed: reads and unrelated commands
expect allow 'psql -h localhost -U app -c "SELECT id, updated_at FROM users LIMIT 5"'
expect allow 'mysql -e "show tables; describe orders"'
expect allow 'psql -c "\d users"'
expect allow 'sqlite3 app.db "select count(*) from todo"'
expect allow "mongosh --eval 'db.users.find({active:true}).limit(3)'"
expect allow 'redis-cli GET session:42'
expect allow './gradlew test'
expect allow 'npm install mysql2 pg'
expect allow 'grep -rn "insert into" src/main/resources'
expect allow 'git commit -m "update readme"'
expect allow 'docker compose -f docker-compose.qa.yml up -d'

# --- ask: writes, DDL, migrations, uninspectable input
expect ask 'psql -c "INSERT INTO users(email) VALUES (1)"'
expect ask 'psql -c "update users set name = 1"'
expect ask 'mysql -e "DROP TABLE orders"'
expect ask 'psql -c "create table t(id int)"'
expect ask 'psql -c "TRUNCATE audit_log"'
expect ask 'psql -f migrations/V2__add_index.sql'
expect ask 'mysql app < dump.sql'
expect ask 'docker exec db psql -U app -c "delete from sessions"'
expect ask "mongosh --eval 'db.users.deleteMany({})'"
expect ask "mongosh --eval 'db.users.insertOne({a:1})'"
expect ask 'redis-cli FLUSHALL'
expect ask 'redis-cli set key value'
expect ask './gradlew flywayMigrate'
expect ask 'flyway -url=jdbc:postgresql://localhost/app migrate'
expect ask 'npx prisma migrate deploy'
expect ask 'npx prisma db push'
expect ask 'bin/rails db:migrate'
expect ask 'alembic upgrade head'
expect ask 'python manage.py migrate'
expect ask 'npx knex migrate:latest'
expect ask 'pg_restore -d app backup.dump'
expect ask 'psql <<SQL
insert into t values (1);
SQL'

printf 'db-guard tests: %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
