"""Run: python -m unittest -v test_access.py. Uses an isolated database copy."""
import os
import shutil
import tempfile
import unittest
from pathlib import Path

_temp=tempfile.TemporaryDirectory()
os.environ['DATABASE_PATH']=str(Path(_temp.name)/'test.db')
os.environ['SECRET_KEY']='test-only-key'
shutil.copy(Path(__file__).parent/'campus.db',os.environ['DATABASE_PATH'])
import app as core
core.app.config['TESTING']=True

class AccessTests(unittest.TestCase):
    def login(self, user, password):
        c=core.app.test_client();c.get('/login')
        with c.session_transaction() as s: token=s['csrf']
        r=c.post('/login',data={'username':user,'password':password,'csrf_token':token})
        self.assertEqual(r.status_code,302)
        with c.session_transaction() as s: token=s['csrf']
        return c, {'X-CSRF-Token':token}

    def test_anonymous(self):
        c=core.app.test_client()
        self.assertEqual(c.get('/').status_code,302)
        self.assertEqual(c.get('/api/students').status_code,401)
        self.assertEqual(c.get('/api/users').status_code,401)

    def test_admin(self):
        c,h=self.login('admin','Admin@12345')
        self.assertEqual(len(c.get('/api/students').json),300)
        self.assertEqual(c.get('/api/users').status_code,200)
        self.assertEqual(c.post('/api/students',json={'id':'NEW-001','department':'CSE','year':2},headers=h).status_code,201)
        self.assertEqual(c.post('/api/users',json={'username':'newstudent','full_name':'Test','role':'student','student_id':'NEW-001','password':'Test@123456'},headers=h).status_code,201)
        self.assertEqual(c.post('/api/users',json={'username':'badstudent','full_name':'Test','role':'student','student_id':'MISSING','password':'Test@123456'},headers=h).status_code,400)
        self.assertEqual(c.delete('/api/students/NEW-001',headers=h).status_code,200)

    def test_faculty_scope_and_edits(self):
        c,h=self.login('faculty','Faculty@12345')
        rows=c.get('/api/students').json
        self.assertTrue(rows and all(s['dept']=='CSE' for s in rows))
        self.assertEqual(c.get('/api/users').status_code,403)
        self.assertEqual(c.get('/api/audit').status_code,403)
        self.assertEqual(c.post('/api/students',json={},headers=h).status_code,403)
        with core.app.app_context():
            other=core.db().execute("SELECT id FROM students WHERE department!='CSE' LIMIT 1").fetchone()[0]
        self.assertEqual(c.post(f'/api/students/{other}/academic',json={'cgpa':8,'backlogs':0},headers=h).status_code,404)
        self.assertEqual(c.get(f'/api/students/{other}/interventions').status_code,404)
        for table,fields in core.TABLES.items():
            values={name:(low+high)//2 for name,(low,high,kind) in fields.items()}
            self.assertEqual(c.post('/api/students/DEMO-0001/'+table,json=values,headers=h).status_code,200)
        self.assertEqual(c.delete('/api/students/DEMO-0001',headers=h).status_code,403)
        self.assertNotIn(other,c.get('/export.csv').text)
        r=c.post('/api/students/DEMO-0001/interventions',json={'action':'Weekly mentor review'},headers=h)
        self.assertEqual(r.status_code,200)
        action=r.json[0]
        r=c.post('/api/students/DEMO-0001/interventions',json={'id':action['id'],'action':action['action'],'status':'Completed'},headers=h)
        self.assertEqual(r.json[0]['status'],'Completed')

    def test_student_scope(self):
        c,h=self.login('student','Student@12345')
        rows=c.get('/api/students').json
        self.assertEqual([s['id'] for s in rows],['DEMO-0001'])
        self.assertEqual(c.get('/api/users').status_code,403)
        self.assertEqual(c.post('/api/students/DEMO-0001/academic',json={'cgpa':10,'backlogs':0},headers=h).status_code,403)
        self.assertEqual(c.post('/api/students/DEMO-0001/interventions',json={'action':'test'},headers=h).status_code,403)
        self.assertEqual(c.get('/api/students/DEMO-0002/interventions').status_code,404)
        self.assertNotIn('DEMO-0002',c.get('/export.csv').text)
        self.assertNotIn(b'href="#/admin"',c.get('/').data)

    def test_csrf_and_model(self):
        c,h=self.login('admin','Admin@12345')
        self.assertEqual(c.post('/api/students',json={}).status_code,400)
        from ai_engine import predict
        low=predict({k:25 for k in core.WEIGHTS});high=predict({k:90 for k in core.WEIGHTS})
        self.assertGreater(low['academic'],high['academic'])
        self.assertGreater(low['placement'],high['placement'])
        self.assertIsNone(predict({})['academic'])
        self.assertTrue(low['recommendations'])

    def test_password_and_disable(self):
        a,h=self.login('admin','Admin@12345')
        a.post('/api/users',json={'username':'tempfaculty','full_name':'Temporary','role':'faculty','department':'CSE','password':'Temp@123456'},headers=h)
        c,ch=self.login('tempfaculty','Temp@123456')
        uid=next(x['id'] for x in a.get('/api/users').json if x['username']=='tempfaculty')
        self.assertEqual(a.patch('/api/users/'+str(uid),json={'password':'New@1234567'},headers=h).status_code,200)
        self.assertEqual(c.get('/api/students').status_code,401)
        c,ch=self.login('tempfaculty','New@1234567')
        self.assertEqual(c.post('/api/password',json={'current':'New@1234567','password':'Final@123456'},headers=ch).status_code,200)
        self.assertEqual(c.get('/api/students').status_code,200)
        a.patch('/api/users/'+str(uid),json={'active':False},headers=h)
        self.assertEqual(c.get('/api/students').status_code,401)

if __name__=='__main__': unittest.main()
