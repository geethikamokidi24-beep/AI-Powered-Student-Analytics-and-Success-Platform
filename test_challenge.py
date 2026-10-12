"""Integration and trend checks against a temporary copy of the supplied demo DB."""
import unittest
import json
from datetime import date
import test_access
core = test_access.core

class ChallengeTests(unittest.TestCase):
    login=test_access.AccessTests.login

    def test_preview_and_cleaning(self):
        c,h=self.login('admin','Admin@12345')
        csv='student_id,overall_pct\n DEMO-0001 , 78% \nDEMO-0001,80\nDEMO-0002,150\nMISSING-999,70\nDEMO-0003,\n'
        before=c.get('/api/students').json
        r=c.post('/api/import',json={'source':'attendance','csv':csv},headers=h)
        self.assertEqual(r.status_code,200)
        self.assertEqual((r.json['accepted'],r.json['rejected'],r.json['skipped']),(1,3,1))
        self.assertEqual(r.json['preview'][0]['values']['overall_pct'],78)
        self.assertEqual(before,c.get('/api/students').json)
        r=c.post('/api/import',json={'source':'attendance','csv':csv,'apply':True},headers=h)
        self.assertTrue(r.json['applied'])
        self.assertEqual(c.get('/api/students').json[0]['raw']['overall_pct'],78)
        self.assertEqual(c.get('/api/quality').json['imports'][0]['accepted'],1)

    def test_all_sources(self):
        c,h=self.login('admin','Admin@12345')
        for source,fields in core.TABLES.items():
            csv='student_id,'+','.join(fields)+'\nDEMO-0001,'+','.join(str((lo+hi)//2) for lo,hi,kind in fields.values())+'\n'
            r=c.post('/api/import',json={'source':source,'csv':csv,'apply':True},headers=h)
            self.assertEqual(r.status_code,200)
            self.assertEqual(r.json['accepted'],1)
        self.assertIsNotNone(c.get('/api/students').json[0]['ai']['academic'])

    def test_authorization(self):
        c,h=self.login('student','Student@12345')
        r=c.post('/api/import',json={'source':'attendance','csv':'student_id,overall_pct\nDEMO-0001,90'},headers=h)
        self.assertEqual(r.status_code,403)
        self.assertEqual(c.post('/api/trends',json={'period':'2026-09'},headers=h).status_code,403)
        self.assertTrue(all(r['count']==1 for r in c.get('/api/trends').json))
        self.assertEqual(c.get('/api/students/DEMO-0002/history').status_code,404)
        c,h=self.login('faculty','Faculty@12345')
        with core.app.app_context():other=core.db().execute("SELECT id FROM students WHERE department!='CSE' LIMIT 1").fetchone()[0]
        r=c.post('/api/import',json={'source':'academic','csv':f'student_id,cgpa,backlogs\n{other},8,0','apply':True},headers=h)
        self.assertEqual(r.json['accepted'],0)
        self.assertEqual(r.json['rejected'],1)
        r=c.post('/api/import',json={'source':'students','csv':'student_id,department,year\nNEW-001,CSE,1'},headers=h)
        self.assertEqual(r.status_code,403)

    def test_bad_headers_partial_nonfinite(self):
        c,h=self.login('admin','Admin@12345')
        for csv in ['student_id,cgpa\nDEMO-0001,7','id,student_id,cgpa,backlogs\nA,A,7,0']:
            self.assertEqual(c.post('/api/import',json={'source':'academic','csv':csv},headers=h).status_code,400)
        for values in ['7,','NaN,0','Infinity,0','7,1.5']:
            r=c.post('/api/import',json={'source':'academic','csv':'student_id,cgpa,backlogs\nDEMO-0001,'+values},headers=h)
            self.assertEqual(r.json['rejected'],1)
            self.assertEqual(r.json['accepted'],0)

    def test_snapshot_and_quality(self):
        c,h=self.login('admin','Admin@12345')
        month=date.today().strftime('%Y-%m')
        r=c.post('/api/trends',json={'period':month},headers=h)
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json[-1]['count'],300)
        self.assertFalse(r.json[-1]['simulated'])
        r2=c.post('/api/trends',json={'period':month},headers=h)
        self.assertEqual(len(r.json),len(r2.json))
        self.assertEqual(c.post('/api/trends',json={'period':'2099-99'},headers=h).status_code,400)
        q=c.get('/api/quality').json
        self.assertEqual(q['total'],300)
        self.assertEqual(len(q['coverage']),7)
        self.assertLess(q['complete'],300)
        with core.app.app_context():
            self.assertEqual(core.db().execute('PRAGMA foreign_key_check').fetchall(),[])

if __name__=='__main__':unittest.main()
