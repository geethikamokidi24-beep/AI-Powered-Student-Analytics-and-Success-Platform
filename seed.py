"""Initialize demo accounts and 300 synthetic student records.
The supplied campus.db is already initialized. Do not run again unless resetting.
python seed.py --reset deletes the existing database and recreates demo data.
python seed.py --reset --no-demo creates only Admin and Faculty accounts.
"""
import os
import random
import sys

from werkzeug.security import generate_password_hash

import app as core


def clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))


def main():
    if "--reset" in sys.argv and os.path.exists(core.DB_PATH):
        os.remove(core.DB_PATH)
    core.init_db()
    conn = core.sqlite3.connect(core.DB_PATH)
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
        sys.exit("Database already has users. Run with --reset to start over.")
    accounts = [("admin", "Administrator", "admin", "Admin@12345", None, None),
                ("faculty", "CSE Faculty", "faculty", "Faculty@12345", "CSE", None)]
    for user, name, role, password, dept, sid in accounts:
        conn.execute("INSERT INTO users(username,password_hash,full_name,role,department,student_id) VALUES(?,?,?,?,?,?)",
                     (user, generate_password_hash(password), name, role, dept, sid))
    if "--no-demo" not in sys.argv:
        rnd = random.Random(2026)
        normal = lambda: sum(rnd.random() for _ in range(6)) - 3  # roughly sd 0.7
        n = lambda: normal() / 0.7071
        for i in range(1, 301):
            sid, a = f"DEMO-{i:04d}", n()
            conn.execute("INSERT INTO students(id, department, year) VALUES (?,?,?)",
                         (sid, rnd.choice(core.DEPARTMENTS), rnd.randint(1, 4)))
            cgpa = round(clamp(6.9 + a * 1.1 + n() * .4, 4, 9.9), 1)
            back = rnd.randint(0, 4) if cgpa < 6 else (1 if rnd.random() < .08 else 0)
            plc = [clamp(64 + a * 9 + n() * 13), clamp(56 + a * 7 + n() * 17), clamp(58 + a * 6 + n() * 15)]
            if a > 0 and rnd.random() < .18:
                plc = [clamp(x - 24) for x in plc]
            rows = {
                "academic": (cgpa, back),
                "attendance": (round(clamp(82 + a * 7 + n() * 7, 40, 100), 1),),
                "lms": (round(clamp(52 + a * 10 + n() * 16), 1), round(clamp(70 + a * 10 + n() * 14), 1)),
                "engagement": (max(0, round(2 + a + n())), max(0, round(1 + n() * .6)),
                               max(0, round(.5 + a * .4 + n() * .5)), max(0, round(1.5 + a * .6 + n()))),
                "placement": tuple(round(x, 1) for x in plc),
                "skills": (round(clamp(58 + a * 6 + n() * 14), 1), round(clamp(58 + a * 5 + n() * 14), 1)),
                "feedback": (round(clamp(3.4 + n() * .6, 1, 5), 1), round(clamp(3.5 + n() * .6, 1, 5), 1)),
            }
            for table, vals in rows.items():
                cols = list(core.TABLES[table])
                conn.execute(f"INSERT INTO {table}(student_id,{','.join(cols)}) VALUES (?,{','.join('?' * len(cols))})",
                             (sid, *vals))
    if "--no-demo" not in sys.argv:
        conn.execute("UPDATE students SET department='CSE' WHERE id='DEMO-0001'")
        conn.execute("INSERT INTO users(username,password_hash,full_name,role,student_id) VALUES(?,?,?,?,?)",
                     ("student",generate_password_hash("Student@12345"),"Demo Student","student","DEMO-0001"))
    conn.commit()
    conn.close()
    if "--no-demo" not in sys.argv:
        from demo_data import prepare
        prepare(core, introduce_missing=True)
    print("Database ready:", core.DB_PATH)
    print("Demo accounts: admin / Admin@12345; faculty / Faculty@12345")
    print("Student account (with demo data): student / Student@12345")
    print("Change demo passwords from My account before using real data.")
    if "--no-demo" not in sys.argv:
        print("300 synthetic students loaded (IDs start with DEMO-). They are not real people.")


if __name__ == "__main__":
    main()
