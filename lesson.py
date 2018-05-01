'''
HITwh102 Course Selection System
author: lllfq idfqxyfy
update: 2018.4.29
'''

#!/usr/bin/env python3

from flask import Flask, views, request, redirect, url_for, Response, render_template, json, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import backref
from datetime import date, datetime, timedelta
from flask_mail import Mail, Message
from threading import Thread
from functools import wraps
import uwsgi
import os

TEACHER_SIGNUP_KEY = os.environ['TEACHER_SIGNUP_KEY']
NUMBER_OF_STUDENTS_IN_DEPARTMENT = 56
FIRST_DAY_OF_THE_TERM = datetime(2018, 2, 26, 00, 00, 00)

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ['SECRET_KEY']  

DB_USERNAME = 'root'
DB_PASSWORD = os.environ['DB_PASSWORD']
DB_HOST = '127.0.0.1'
DB_PORT = '3306'
DATABASE = 'hitwh102'
DB_URI = 'mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset=utf8' \
    .format(username=DB_USERNAME, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT, database=DATABASE)
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SQLALCHEMY_COMMIT_TEARDOWN'] = True

MAIL_SUBJECT_PREFIX = '[HITwh102 css]'
MAIL_SENDER = os.environ['MAIL_USERNAME']
app.config['MAIL_USERNAME'] = os.environ['MAIL_USERNAME']
app.config['MAIL_PASSWORD'] = os.environ['MAIL_PASSWORD']
app.config['MAIL_SERVER'] = 'smtp.qq.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True

db = SQLAlchemy(app)
mail = Mail(app)

def show_cron(n):
    now = datetime.now()
    print(now,'cron_job is running')

def selecting_end_email(n):
    ctx = app.app_context()
    ctx.push()
    les = db.session.query(Lesson).all()
    for lesson in les:
        if lesson.start_time.date() == date.today():
            tea = lesson.teacher
            stu = lesson.students
            selected = []
            for student in stu:
                selected.append({'no': student.no, 'name': student.name})
            send_email('%s的实验%s选课已截止' % (to_str_time(lesson.start_time), lesson.classname), tea.email.split(), 'email/selecting_end',
                       user_name=tea.name, lesson_name=lesson.classname, lesson_room=lesson.classroom,
                       lesson_time=lesson.start_time, stu_num=lesson.stu_num,stu_e=len(lesson.students),selected=selected)
            now = datetime.now()
            print('%s --> 发送%s的实验%s截止邮件给%s成功' % (now,lesson.start_time,lesson.classname,tea.name))

jobs = [ { "name" : selecting_end_email,
           "time": [00, 7, -1, -1, -1], #minute, hour, day, month, weekday, "-1" means "all"
          },
         { "name" : show_cron,
           "time": [9],               
         },
         ]

for job_id, job in enumerate(jobs):
    uwsgi.register_signal(job_id, "", job['name'])
    if len(job['time']) == 1:
        uwsgi.add_timer(job_id, job['time'][0])
    else:
        uwsgi.add_cron(job_id, job['time'][0], job['time'][1], job['time'][2], job['time'][3], job['time'][4])

def to_datetime(time):
    week = int(time.split('，')[0][0:-1][1:])  # 均为中文逗号
    weekday = time.split('，')[1][-1]
    hours = int(time.split('，')[2].split(':')[0])
    minutes = int(time.split('，')[2].split(':')[1])
    if weekday == '一':
        weekday = 1
    elif weekday == '二':
        weekday = 2
    elif weekday == '三':
        weekday = 3
    elif weekday == '四':
        weekday = 4
    elif weekday == '五':
        weekday = 5
    elif weekday == '六':
        weekday = 6
    elif weekday == '日':
        weekday = 7
    days = (week - 1) * 7 + weekday - 1
    time = FIRST_DAY_OF_THE_TERM + timedelta(days=days, hours=hours, minutes=minutes)
    return time


def to_str_time(time):
    days = (time - FIRST_DAY_OF_THE_TERM).days
    seconds = (time - FIRST_DAY_OF_THE_TERM).seconds
    week = days // 7 + 1
    weekday = days % 7 + 1
    hours = str(seconds // 3600).zfill(2)
    minutes = str((seconds % 3600) // 60).zfill(2)
    if weekday == 1:
        weekday = '一'
    elif weekday == 2:
        weekday = '二'
    elif weekday == 3:
        weekday = '三'
    elif weekday == 4:
        weekday = '四'
    elif weekday == 5:
        weekday = '五'
    elif weekday == 6:
        weekday = '六'
    elif weekday == 7:
        weekday = '日'
    time = '第%s周，星期%s，%s:%s' % (week, weekday, hours, minutes)  # 中文逗号（非必需）
    return time


def send_email(subject, recipients, template, **kwargs):
    msg = Message(MAIL_SUBJECT_PREFIX + subject, sender=MAIL_SENDER, recipients=recipients)
    msg.html = render_template(template + '.html', **kwargs)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


def objs_dict(objs):
    ''' 包含实例对象的列表 --> 包含实例对象信息的字典的字典
        包含信息：不完全是严格的属性名-属性值形式，做了部分类型转换'''
    dic = {}
    if objs:
        for i in range(len(objs)):
            dic[i + 1] = objs[i].obj_dict()
    return dic


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        user_no = request.cookies.get('username')
        psw_hash = request.cookies.get('psw_hash')
        result = user_login(no=user_no, psw_hash=psw_hash)
        if result['result'] == 'success':
            return func(*args, **kwargs)
        else:
            return redirect(url_for('login'))

    return wrapper


def user_login(no, password=None, psw_hash=None):
    data = {'result': 'error', 'identify': '', 'user_id': '', 'psw_hash': ''}
    psw = password or psw_hash
    if no and psw:
        user = None
        if len(str(no)) == 2:
            data.update({'identify': 'teacher'})
            user = db.session.query(Teacher).filter_by(no=no).first()
        elif len(str(no)) == 9:
            data.update({'identify': 'student'})
            user = db.session.query(Student).filter_by(no=no).first()
        if not user:                                       # 检查用户是否存在 若否，返回用户不存在
            data.update({'result': 'unexist'})
        if user:
            psw_check = psw_hash == user.psw_hash or user.check_password(password)
            if not psw_check:                              # 检查密码是否匹配 若否，返回密码错误
                data.update({'result': 'wrong'})
            elif not user.confirmed:                       # 检查用户是否已激活 若否，返回待激活
                data.update({'result': 'wait'})
            else:                                          # 通过上述检查，返回登录成功
                data.update({'result': 'success', 'user_id': user.id, 'psw_hash': user.psw_hash})
    return data




@app.route('/error/<e>')
def error(e):
    if e == '404':
        error_message = '页面不存在'
    elif e == 'no_authority':
        error_message = '无访问权限'
    elif e == 'invalid_token':
        error_message = '无效的验证链接或链接已过期。请尝试重新注册，并在收到邮件后30分钟内访问新链接'
    elif e == 'already_confirmed':
        error_message = '账号注册与验证已完成，无需重复验证'
    else:
        error_message = '没有错误。如果你坚持要的话 ：%s' % e
    return render_template('error.html', error_message=error_message)


@app.route('/confirm/<token>')
def confirm(token):
    s = Serializer(app.config['SECRET_KEY'])
    try:
        data = s.loads(token)
    except:
        return redirect(url_for('error', e='invalid_token'))
    user_no = data.get('confirm_no')
    email = data.get('confirm_email')
    tea = db.session.query(Teacher).filter_by(no=user_no, email=email).first()
    stu = db.session.query(Student).filter_by(no=user_no, email=email).first()
    if len(str(user_no)) == 2 and tea:
        if not tea.confirmed:
            tea.confirmed = True

        else:
            return redirect(url_for('error', e='already_confirmed'))
    elif len(str(user_no)) == 9 and stu:
        if not stu.confirmed:
            stu.confirmed = True
        else:
            return redirect(url_for('error', e='already_confirmed'))
    else:
        return redirect(url_for('error', e='invalid_token'))
    db.session.commit()
    return redirect(url_for('login'))


@app.route('/logout/')
@login_required
def logout():
    '''注销,清除所有cookies'''
    resp = Response("注销成功")
    resp.set_cookie('user_id', '', max_age=0)
    resp.set_cookie('username', '', max_age=0)
    resp.set_cookie('identify', '', max_age=0)
    resp.set_cookie("psw_hash", '', max_age=0)
    return resp


'''学生-课程 多对多关系的中间表'''
student_lesson = db.Table(
    'student_lesson',
    db.Model.metadata,
    db.Column('student_id', db.Integer, db.ForeignKey('student.id'), primary_key=True),
    db.Column('lesson_id', db.Integer, db.ForeignKey('lesson.id'), primary_key=True)
)


class Student(db.Model):
    __tablename__ = 'student'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    no = db.Column(db.Integer, unique=True, nullable=False)
    name = db.Column(db.String(10), nullable=False)
    email = db.Column(db.String(30), nullable=False)
    psw_hash = db.Column(db.String(256), nullable=False)
    confirmed = db.Column(db.Boolean, default=False)

    def generate_confirmation_token(self, expiration=1800):
        s = Serializer(app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm_no': self.no,
                        'confirm_email': self.email})

    def set_password(self, password):
        self.psw_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.psw_hash, password)

    def obj_dict(self):
        ''' 学生对象 --> 包含该学生对象属性键值对的字典, 且将课程一项的值：包含课程对象的列表 --> 包含课程信息的字典的列表 '''
        tem = []
        dic = dict(self.__dict__)
        del dic['_sa_instance_state']
        for lesson in self.lessons:
            tem.append({'id': lesson.id, 'classname': lesson.classname, 'classroom': lesson.classroom,
                        'start_time': to_str_time(lesson.start_time), 'stu_num': lesson.stu_num})
        dic['lessons'] = tem
        return dic

    def __repr__(self):
        return '<student(id:%s,no:%s,name:%s)>' % (self.id, self.no, self.name)


class Teacher(db.Model):
    __tablename__ = 'teacher'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    no = db.Column(db.Integer, unique=True, nullable=False)
    name = db.Column(db.String(10), nullable=False)
    email = db.Column(db.String(30), nullable=False)
    psw_hash = db.Column(db.String(256), nullable=False)
    confirmed = db.Column(db.Boolean, default=False)
    noticed = db.Column(db.String(100), nullable=True)

    def generate_confirmation_token(self, expiration=1800):
        s = Serializer(app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm_no': self.no,
                        'confirm_email': self.email})

    def set_password(self, password):
        self.psw_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.psw_hash, password)

    def obj_dict(self):
        ''' 教师对象 --> 包含该教师对象属性键值对的字典, 且将课程一项的值：包含课程对象的列表 --> 包含课程信息的字典的列表 '''
        tem = []
        dic = dict(self.__dict__)
        del dic['_sa_instance_state']
        for lesson in self.lessons:
            tem.append({'id': lesson.id, 'classname': lesson.classname, 'classroom': lesson.classroom,
                        'start_time': to_str_time(lesson.start_time), 'stu_num': lesson.stu_num})
        dic['lessons'] = tem
        return dic

    def __repr__(self):
        return '<teacher(id:%s,no:%s,name:%s)>' % (self.id, self.no, self.name)


class Lesson(db.Model):
    __tablename__ = 'lesson'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    classname = db.Column(db.String(30), nullable=False)
    classroom = db.Column(db.String(10), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    stu_num = db.Column(db.Integer, nullable=False, default=8)
    tel = db.Column(db.String(11), nullable=False)

    students = db.relationship('Student', secondary=student_lesson,
                               backref=backref('lessons', order_by=start_time.desc()), cascade='save-update')
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'))
    teacher = db.relationship('Teacher',
                              backref=backref('lessons', order_by=start_time.desc(), cascade='save-update,delete'))
    def check_available(self):
        if len(self.students) < self.stu_num and date.today() < self.start_time.date():
            return True
        else:
            return False

    def obj_dict(self):
        ''' 课程对象 --> 包含该课程对象属性键值对的字典, 且将教师一项的值：教师对象 --> 包含教师信息的字典，
                        将学生一项的值：包含学生对象的列表 --> 包含学生信息的字典的列表 '''
        tem = []
        dic = dict(self.__dict__)
        dic['start_time'] = to_str_time(self.start_time)
        dic['available'] = self.check_available()
        dic['teacher'] = {'id': self.teacher.id, 'no': self.teacher.no, 'name': self.teacher.name}
        del dic['_sa_instance_state']
        for student in self.students:
            tem.append({'id': student.id, 'no': student.no, 'name': student.name})
        dic['students'] = tem
        return dic

    def __repr__(self):
        return '<lesson(id:%s,classname:%s,classroom:%s,start_time:%s)>' % (
        self.id, self.classname, self.classroom, self.start_time)


class LoginView(views.MethodView):
    '''登录视图,也作为主页'''

    def get(self):
        return render_template('login.html')

    def post(self):
        no = request.form.get('username')
        password = request.form.get('password')
        result = user_login(no=no, password=password)
        tem = result.copy()
        result = json.dumps(result)
        resp = Response(result)
        resp.set_cookie('user_id', str(tem['user_id']))
        resp.set_cookie("username", str(no))
        resp.set_cookie('identify', str(tem['identify']))
        resp.set_cookie("psw_hash", str(tem['psw_hash']))
        return resp


app.add_url_rule('/', view_func=LoginView.as_view('login'))


class SignupView(views.MethodView):
    '''注册视图，路径是/signup/'''

    def get(self):
        return render_template('signup.html')

    def post(self):
        no = request.form.get('username')
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        no1 = str(no)[0:7]
        if no1 == TEACHER_SIGNUP_KEY:    # 检查学号栏前7位是否为教师注册密钥 若是，注册目标为教师
            no2 = int(str(no)[7:9])
            tea = db.session.query(Teacher).filter_by(no=no2).first()
            if not tea:                  # 检查是否存在该学号的教师 若否，注册教师，返回待激活
                teacher = Teacher(no=no2, name=name, email=email)
                teacher.set_password(password=password)
                db.session.add(teacher)
                db.session.commit()
                token = teacher.generate_confirmation_token().decode('utf-8')
                send_email('确认注册', email.split(), 'email/confirm', user_name=name, email=email, token=token)
                return jsonify(result='wait')
            elif not tea.confirmed:      # 检查已存在的教师是否已激活 若否，覆盖注册信息，返回已覆盖
                tea.name = name
                tea.email = email
                tea.set_password(password=password)
                db.session.commit()
                token = tea.generate_confirmation_token().decode('utf-8')
                send_email('确认注册', email.split(), 'email/confirm', user_name=name, email=email, token=token)
                return jsonify(result='cover')
            else:                        # 存在已激活的该学号教师 返回已存在
                return jsonify(result='exist')
        else:                            # 学号栏前7位不是教师注册密钥，注册目标为学生
            stu = db.session.query(Student).filter_by(no=no).first()
            if not stu:                  # 检查是否存在该学号的学生 若否，注册学生，返回待激活
                student = Student(no=no, name=name, email=email)
                student.set_password(password=password)
                db.session.add(student)
                db.session.commit()
                token = student.generate_confirmation_token().decode('utf-8')
                send_email('确认注册', email.split(), 'email/confirm', user_name=name, email=email, token=token)
                return jsonify(result='wait')
            elif not stu.confirmed:      # 检查已存在的学生是否已激活 若否，覆盖注册信息，返回已覆盖
                stu.name = name
                stu.email = email
                stu.set_password(password=password)
                db.session.commit()
                token = stu.generate_confirmation_token().decode('utf-8')
                send_email('确认注册', email.split(), 'email/confirm', user_name=name, email=email, token=token)
                return jsonify(result='cover')
            else:                        # 存在已激活的该学号学生 返回已存在
                return jsonify(result='exist')


app.add_url_rule('/signup/', view_func=SignupView.as_view('signup'))


class StudentView(views.MethodView):
    '''学生操作视图,路径/student/'''
    decorators = [login_required]

    def __show_lessons(self):
        '''根据cookie查询学生，返回已选课程与所有课程'''
        user_id = request.cookies.get('user_id')
        stu = db.session.query(Student).filter_by(id=user_id).first()
        my_lessons = stu.lessons
        all_lessons = db.session.query(Lesson).all()
        data = {'name': stu.name,
                'my_lessons': objs_dict(my_lessons),
                'all_lessons': objs_dict(all_lessons)
                }
        return jsonify(data)

    def get(self):                       # 渲染模板
        identify = request.cookies.get('identify')
        if identify == 'student':
            return render_template('student.html')
        else:
            return redirect(url_for('error', e='no_authority'))

    def post(self):
        type = request.form.get('type')  # 判断功能
        if type == 'get':                # 显示课程
            return self.__show_lessons()

        elif type == 'select':           # 选课
            student_id = request.cookies.get('user_id')
            lesson_id = request.form.get('lesson_id')

            stu = db.session.query(Student).filter_by(id=student_id).first()
            les = db.session.query(Lesson).filter_by(id=lesson_id).first()
            tea = les.teacher
            if len(les.students) < les.stu_num and date.today() < les.start_time.date():  # 选课条件：人数未满且日期为至少前一天
                stu.lessons.append(les)
                db.session.commit()
            # stu_num_selected = 0
            # namesake_lessons = db.session.query(Lesson).filter_by(classname=les.classname).all()
            # for lesson in namesake_lessons:
            #     stu_num_selected += len(lesson.students)
            # if stu_num_selected == NUMBER_OF_STUDENTS_IN_DEPARTMENT:
            #     if les.classname not in tea.noticed:
            #         send_email('您的%s实验已基本完成选课' % les.classname, tea.email.split(), 'selecting_complete',
            #                    user_name=tea.name, lssson_name=les.classname, lesson_room=les.classroom)
            #         tea.noticed.append(les.classname)
            #         db.session.commit()
            return self.__show_lessons()

        elif type == 'unselect':        # 取消选课
            student_id = request.cookies.get('user_id')
            lesson_id = request.form.get('lesson_id')

            stu = db.session.query(Student).filter_by(id=student_id).first()
            les = db.session.query(Lesson).filter_by(id=lesson_id).first()
            if date.today() < les.start_time.date():            # 取消选课条件：日期为至少前一天
                stu.lessons.remove(les)
            db.session.commit()
            return self.__show_lessons()


app.add_url_rule('/student/', view_func=StudentView.as_view('student'))


class TeacherView(views.MethodView):
    decorators = [login_required]
    '''教师操作视图，路径/teacher/'''

    def __show_lessons(self):
        '''根据cookie查询教师，返回已开课程与所有课程'''
        user_id = request.cookies.get('user_id')
        tea = db.session.query(Teacher).filter_by(id=user_id).first()
        my_lessons = tea.lessons
        all_lessons = db.session.query(Lesson).all()
        data = {'name': tea.name,
                'my_lessons': objs_dict(my_lessons),
                'all_lessons': objs_dict(all_lessons)
                }
        return jsonify(data)

    def get(self):                      # 渲染模板
        identify = request.cookies.get('identify')
        if identify == 'teacher':
            return render_template('teacher.html')
        else:
            return redirect(url_for('error', e='no_authority'))

    def post(self):
        type = request.form.get('type') # 判断功能
        if type == 'get':               # 显示课程列表
            return self.__show_lessons()

        elif type == 'add':             # 创建课程系
            teacher_id = request.cookies.get('user_id')
            classname = request.form.get('classname')
            classroom = request.form.get('classroom')
            time = request.form.get('time')
            stu_num = request.form.get('number')
            tel = request.form.get('tel')

            tea = db.session.query(Teacher).filter_by(id=teacher_id).first()
            stu = db.session.query(Student).all()
            str_times = time.split('/')
            str_times.pop()
            for str_time in str_times:
                start_time = to_datetime(str_time)
                lesson = Lesson(teacher=tea, classname=classname, classroom=classroom, start_time=start_time,
                                stu_num=stu_num, tel=tel, teacher_id=tea.id)
                db.session.add(lesson)
            db.session.commit()
            no1_les = db.session.query(Lesson).filter_by(teacher_id=tea.id, classname=classname).order_by(
                Lesson.start_time).first()
            for student in stu:
                send_email('新实验%s可选' % no1_les.classname, student.email.split(), 'email/lesson_added',
                           user_name=student.name, lesson_name=classname, lesson_room=classroom,
                           lesson_time=no1_les.start_time, stu_num=stu_num, operator=tea.name)
            return self.__show_lessons()

        elif type == 'delete':          # 删除课程
            teacher_id = request.cookies.get('user_id')
            lesson_id = request.form.get('lesson_id')

            tea = db.session.query(Teacher).filter_by(id=teacher_id).first()
            les = db.session.query(Lesson).filter_by(teacher=tea, id=lesson_id).first()
            for student in les.students:
                send_email('您的%s实验已删除' % les.classname, student.email.split(), 'email/lesson_deleted',
                           user_name=student.name, lesson_name=les.classname, lesson_room=les.classroom,
                           lesson_time=les.start_time, operator=tea.name)
            db.session.delete(les)
            db.session.commit()
            return self.__show_lessons()

        elif type == 'change':          # 修改课程时间
            teacher_id = request.cookies.get('user_id')
            lesson_id = request.form.get('lesson_id')
            new_time = to_datetime(request.form.get('new_time'))

            tea = db.session.query(Teacher).filter_by(id=teacher_id).first()
            les = db.session.query(Lesson).filter_by(teacher=tea, id=lesson_id).first()
            for student in les.students:
                send_email('您的%s实验已改期' % les.classname, student.email.split(), 'email/lesson_time_changed',
                           user_name=student.name, lesson_name=les.classname, lesson_room=les.classroom,
                           lesson_time=les.start_time, new_time=new_time, operator=tea.name)
            les.start_time = new_time
            db.session.commit()
            return self.__show_lessons()


app.add_url_rule('/teacher/', view_func=TeacherView.as_view('teacher'))

# db.drop_all()
# db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)


