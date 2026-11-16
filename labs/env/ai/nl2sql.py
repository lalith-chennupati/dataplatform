"""Lab B05: natural-language-to-SQL against the governed lakehouse.

  python nl2sql.py --user ana "revenue by region"
The question is answered with the caller's Trino identity, so B03 row filters and masks still apply.
"""
import argparse, os, re, requests, trino, trino.exceptions

OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("LLM_MODEL", "qwen2.5:1.5b")
TABLES = ["postgresql.crm.customers", "iceberg.curated.orders"]


def schema(cur):
    lines = []
    for t in TABLES:
        cat, sch, tab = t.split(".")
        cur.execute(f"SELECT column_name, data_type FROM {cat}.information_schema.columns "
                    f"WHERE table_schema = '{sch}' AND table_name = '{tab}' ORDER BY ordinal_position")
        lines.append(f"{t}(" + ", ".join(f"{c} {d}" for c, d in cur.fetchall()) + ")")
    return "\n".join(lines)


def to_sql(question, ddl, error=None):
    prompt = (f"You write Trino SQL. Tables:\n{ddl}\n"
              "orders.customer_id joins customers.customer_id.\n"
              "Always use the full three-part table names exactly as listed, for example:\n"
              "SELECT c.segment, count(*) FROM postgresql.crm.customers c GROUP BY c.segment\n"
              "Return only one SQL query, no explanation, no semicolon.\n"
              f"Question: {question}\n")
    if error:
        prompt += f"Your previous query failed with: {error}\nFix it.\n"
    prompt += "SQL:"
    r = requests.post(f"{OLLAMA}/api/generate", json={"model": MODEL, "prompt": prompt, "stream": False,
                                                       "options": {"temperature": 0}}, timeout=300)
    r.raise_for_status()
    text = r.json()["response"]
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip().rstrip(";")


p = argparse.ArgumentParser()
p.add_argument("question")
p.add_argument("--user", default="ana")
a = p.parse_args()
cur = trino.dbapi.connect(host=os.environ.get("TRINO_HOST", "localhost"), port=8080, user=a.user).cursor()
ddl, error = schema(cur), None
for attempt in range(1, 4):                      # self-correct: feed the engine's error back to the model
    sql = to_sql(a.question, ddl, error)
    print(f"-- attempt {attempt}: generated SQL\n{sql}")
    if not re.match(r"(?is)^\s*(select|with)\b", sql):
        raise SystemExit("refusing to run a non-SELECT statement")
    try:
        cur.execute(sql)
        rows = cur.fetchall()
        break
    except trino.exceptions.TrinoUserError as e:
        error = e.message
        print(f"-- error: {error}")
else:
    raise SystemExit("no valid SQL after 3 attempts")
print(f"-- result (as user {a.user})")
for row in rows[:10]:
    print(row)
