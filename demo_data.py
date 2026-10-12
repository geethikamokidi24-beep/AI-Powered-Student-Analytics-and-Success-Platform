"""Generate explicitly simulated history and CSV source exports for the demo."""
import csv
import json
import sqlite3
from pathlib import Path

def prepare(core, introduce_missing=False):
    conn=sqlite3.connect(core.DB_PATH);conn.row_factory=sqlite3.Row
    if introduce_missing:
        # Purposeful gaps demonstrate missing-data handling, not zero imputation.
        conn.execute("DELETE FROM lms WHERE student_id IN ('DEMO-0010','DEMO-0020','DEMO-0030','DEMO-0040','DEMO-0050')")
        conn.execute("DELETE FROM placement WHERE student_id IN ('DEMO-0010','DEMO-0020','DEMO-0060')")
        conn.commit()
    rows=conn.execute(core.SELECT_ALL+' ORDER BY s.id').fetchall()
    folder=Path(core.BASE)/'sample_sources';folder.mkdir(exist_ok=True)
    with (folder/'students.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['student_id','department','year']);w.writerows((r['id'],r['department'],r['year']) for r in rows)
    for table,fields in core.TABLES.items():
        with (folder/(table+'.csv')).open('w',newline='') as f:
            w=csv.writer(f);w.writerow(['student_id',*fields]);w.writerows([r['id'],*[r[k] for k in fields]] for r in rows)
    for i,period in enumerate(['2026-07','2026-08','2026-09']):
        for r in rows:
            d=dict(r)
            # Fabricated historic profiles, explicitly marked simulated.
            for field in ['overall_pct','login_score','assignment_pct','aptitude','coding','mock_interview','technical','soft']:
                if d[field] is not None:d[field]=max(0,d[field]-(2-i)*4)
            payload=core.compute(d)
            conn.execute('INSERT OR REPLACE INTO snapshots(student_id,period,payload,source) VALUES(?,?,?,?)',
                         (r['id'],period,json.dumps(payload),'Simulated demo history'))
    conn.commit();conn.close()
    (folder/'attendance_dirty_demo.csv').write_text('student_id,overall_pct\n DEMO-0001 , 78% \nDEMO-0001,80\nDEMO-0002,150\nMISSING-999,70\nDEMO-0003,\n')

if __name__=='__main__':
    import app
    prepare(app,introduce_missing=True)
    print('Source CSVs and simulated monthly snapshots prepared.')
