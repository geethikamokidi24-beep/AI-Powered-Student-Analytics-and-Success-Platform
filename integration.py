"""CSV source integration, provenance, data quality and longitudinal snapshots."""
import csv
import io
import json
import re
from datetime import date
from flask import g, request, jsonify


def register(app, core):
    def parse_upload(source, text):
        if source not in ['students', *core.TABLES]:
            raise ValueError('Choose a supported data source.')
        if g.user['role'] == 'student' or (source == 'students' and g.user['role'] != 'admin'):
            raise PermissionError('This role cannot import this data source.')
        if not isinstance(text, str) or not text.strip():
            raise ValueError('Choose a non-empty UTF-8 CSV file.')
        reader = csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
        if not reader.fieldnames:
            raise ValueError('CSV header row is required.')
        aliases = {'id':'student_id', 'roll_no':'student_id', 'roll_number':'student_id', 'dept':'department'}
        fields = [aliases.get(x.strip().lower().replace(' ', '_'), x.strip().lower().replace(' ', '_')) for x in reader.fieldnames]
        if len(set(fields)) != len(fields):
            raise ValueError('Duplicate column headers are not allowed.')
        required = ['student_id','department','year'] if source == 'students' else ['student_id', *core.TABLES[source]]
        absent = set(required)-set(fields)
        if absent:
            raise ValueError('Missing columns: '+', '.join(sorted(absent)))
        reader.fieldnames=fields
        valid, errors, skipped, seen, cleaned = [], [], [], set(), 0
        for n, row in enumerate(reader,2):
            if n>1001: raise ValueError('Limit each file to 1,000 data rows.')
            try:
                if None in row or any(v is None for v in row.values()):
                    raise ValueError('Column count does not match the header.')
                values={k:v.strip() for k,v in row.items()}
                sid=values['student_id']
                if not core.ID_RE.fullmatch(sid):raise ValueError('Invalid student ID.')
                if sid in seen:raise ValueError('Duplicate student ID in this file. First occurrence is retained.')
                seen.add(sid)
                if source=='students':
                    dept=values['department'].upper()
                    year=int(values['year'])
                    if dept not in core.DEPARTMENTS or year not in (1,2,3,4):raise ValueError('Invalid department or year.')
                    vals={'department':dept,'year':year}
                else:
                    if not core._student_row(sid):raise ValueError('Student does not exist or is outside your access scope. Import the roster first.')
                    raw={k:values[k] for k in core.TABLES[source]}
                    if all(v=='' for v in raw.values()):
                        skipped.append({'row':n,'id':sid,'reason':'All module values blank; existing data preserved.'});continue
                    if any(v=='' for v in raw.values()):raise ValueError('Partial record: complete all module fields, or leave all blank to skip.')
                    for k,v in raw.items():
                        if v.endswith('%') and core.TABLES[source][k][:2]==(0,100):raw[k]=v[:-1].strip()
                    vals=core._parse(source,raw)
                normalized=any(row[k]!=values[k] for k in row) or any(str(vals[k])!=values[k] for k in vals)
                if normalized:cleaned+=1
                valid.append({'row':n,'id':sid,'values':vals})
            except (ValueError,TypeError,OverflowError) as exc:
                errors.append({'row':n,'id':str(row.get('student_id',''))[:24],'reason':str(exc)})
        return {'source':source,'accepted':len(valid),'rejected':len(errors),'skipped':len(skipped),
                'normalized':cleaned,'errors':errors,'skipped_rows':skipped,'records':valid,
                'ignored_columns':sorted(set(fields)-set(required))}

    @app.route('/api/import',methods=['POST'])
    @core.need()
    def import_csv():
        d=core.body()
        try: result=parse_upload(d.get('source'),d.get('csv'))
        except PermissionError as exc:return jsonify(error=str(exc)),403
        except (ValueError,csv.Error) as exc:return jsonify(error=str(exc)),400
        if d.get('apply') is True:
            conn=core.db();source=result['source']
            with conn:
                for r in result['records']:
                    cols=list(r['values'])
                    if source=='students':
                        conn.execute('INSERT INTO students(id,department,year) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET department=excluded.department,year=excluded.year',
                                     (r['id'],r['values']['department'],r['values']['year']))
                    else:
                        conn.execute(f"INSERT INTO {source}(student_id,{','.join(cols)}) VALUES(?,{','.join('?' for _ in cols)}) ON CONFLICT(student_id) DO UPDATE SET {','.join(c+'=excluded.'+c for c in cols)},updated_at=CURRENT_TIMESTAMP",
                                     [r['id']]+[r['values'][c] for c in cols])
                conn.execute('INSERT INTO import_runs(source,filename,username,accepted,rejected,skipped) VALUES(?,?,?,?,?,?)',
                             (source,str(d.get('filename','upload.csv'))[:120],g.user['username'],result['accepted'],result['rejected'],result['skipped']))
                conn.execute('INSERT INTO audit_log(username,action,detail) VALUES(?,?,?)',
                             (g.user['username'],'csv_import',f"{source}: {result['accepted']} accepted, {result['rejected']} rejected"))
            result['applied']=True
        else:result['applied']=False
        result['preview']=result.pop('records')[:10]
        return jsonify(result)

    @app.route('/api/quality')
    @core.need()
    def quality():
        rows=[core.compute(r) for r in core.scoped_rows()]
        coverage={k:sum(k in s['idx'] for s in rows) for k in core.WEIGHTS}
        sql='SELECT * FROM import_runs'
        args=[]
        if g.user['role']!='admin':sql+=' WHERE username=?';args=[g.user['username']]
        runs=core.db().execute(sql+' ORDER BY id DESC LIMIT 20',args).fetchall()
        return jsonify(total=len(rows),complete=sum(not s['missing'] for s in rows),coverage=coverage,
                       unrated=sum(s['score'] is None for s in rows),imports=[dict(r) for r in runs])

    def history_rows():
        where,args=core.scope()
        return core.db().execute('SELECT h.* FROM snapshots h JOIN students s ON s.id=h.student_id'+where+' ORDER BY h.period,h.student_id',args).fetchall()

    @app.route('/api/trends',methods=['GET','POST'])
    @core.need()
    def trends():
        if request.method=='POST':
            if g.user['role']=='student':return jsonify(error='Admin or Faculty access required.'),403
            period=str(core.body().get('period',''))
            if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',period) or period>date.today().strftime('%Y-%m') or period<'2000-01':
                return jsonify(error='Use a month from 2000-01 through the current month (YYYY-MM).'),400
            with core.db() as conn:
                for r in core.scoped_rows():
                    s=core.compute(r)
                    conn.execute('INSERT INTO snapshots(student_id,period,payload,source) VALUES(?,?,?,?) ON CONFLICT(student_id,period) DO UPDATE SET payload=excluded.payload,source=excluded.source',
                                 (s['id'],period,json.dumps(s),'Recorded snapshot'))
            core.audit('snapshot',period)
        groups={}
        for r in history_rows():groups.setdefault(r['period'],[]).append((json.loads(r['payload']),r['source']))
        output=[]
        for period,items in sorted(groups.items()):
            rated=[s['score'] for s,_ in items if s['score'] is not None]
            output.append({'period':period,'count':len(items),'rated':len(rated),'score':round(sum(rated)/len(rated),1) if rated else None,
                           'academic':sum(s['acadRisk'] for s,_ in items),'placement':sum(s['plcRisk'] for s,_ in items),
                           'high':sum(s['level']=='High' for s,_ in items),'simulated':any(src=='Simulated demo history' for _,src in items)})
        return jsonify(output)

    @app.route('/api/students/<sid>/history')
    @core.need()
    def student_history(sid):
        if not core._student_row(sid):return jsonify(error='Student not found.'),404
        rows=core.db().execute('SELECT period,payload,source FROM snapshots WHERE student_id=? ORDER BY period',(sid,)).fetchall()
        return jsonify([{'period':r['period'],'score':json.loads(r['payload'])['score'],'source':r['source']} for r in rows])
