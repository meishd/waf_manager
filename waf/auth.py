from flask import Blueprint,render_template,request,redirect,url_for,flash,g,current_app
from flask_login import login_user,logout_user,current_user
from urllib import parse
from wtforms import Form,StringField,validators,IntegerField,TextAreaField,RadioField,ValidationError,PasswordField,HiddenField,BooleanField
from werkzeug.security import generate_password_hash,check_password_hash
from .models import User,Userpriv
from .DBUtil import DBUtil
from . import login_manager

bp = Blueprint('auth',__name__,url_prefix='/auth')

class LoginForm(Form):
    user_name = StringField("用户名",[validators.data_required(message="请输入用户名")])
    password = PasswordField("密码",[validators.data_required(message="请输入密码")])
    # remember_me =  StringField("remember me")
    remember_me = BooleanField("remember me")

class ChangepasswordForm(Form):
    user_name = HiddenField("用户名")
    old_password = PasswordField("旧密码",[validators.data_required(message="请输入旧密码")])
    new_password = PasswordField("新密码",[validators.data_required(message="请输入新密码"),validators.length(min=8,max=30,message="密码长度8-30")])
    new_password_again = PasswordField("确认新密码",[validators.data_required(message="请输入确认新密码"),validators.equal_to('new_password',message="新密码两次输入不一致")])

    def validate_new_password(form,field):
        newpassword = field.data
        containupper = 0
        containlower = 0
        containdigit = 0
        for i in newpassword:
            if i.isupper():
                containupper = 1
                break
        for i in newpassword:
            if i.islower():
                containlower = 1
                break
        for i in newpassword:
            if i.isdigit():
                containdigit = 1
                break
        if containupper != 1 or containlower != 1 or containdigit != 1:
            raise ValidationError("密码必须包含大小写字母和数字")



@bp.route('/login',methods=('GET','POST'))
def login():
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        user_name = form.user_name.data
        password = form.password.data
        remember_me = form.remember_me.data
        user = User.query.filter_by(user_name=user_name).first()
        if user is None:
            error = '用户名不存在'
        elif user.active == 1:
            error = '用户已禁用'
        else:
            if user.check_password(password):
                if user.login_cnt == 0:
                    flash("首次登录必须修改密码")
                    return redirect(url_for('auth.change_password',user_name=user_name))
                else:
                    g.user = user
                    login_user(user, remember_me)
                    User.query.filter_by(user_name=user_name).update({'login_cnt':user.login_cnt + 1})
                    current_app.logger.info('action - login - user:%s',user.user_name)
                    return render_template('auth/login_dialog_temp.html',message='登录成功')
            else:
                error = '密码不正确'
        flash(error)
    if form.errors:
        first_key = list(form.errors.keys())[0]
        error = ('%s' % (form.errors[first_key][0]))
        flash(error)
    return render_template('auth/login.html',form=form)

@bp.route('/login_ajax',methods=('POST',))
def login_ajax():
    form = LoginForm(request.form)
    error = None
    login_flag = 1
    if form.validate():
        user_name = form.user_name.data
        password = form.password.data
        remember_me = form.remember_me.data
        user = User.query.filter_by(user_name=user_name).first()
        if user is None:
            error='用户名不存在'
        else:
            if user.check_password(password):
                login_user(user,remember_me)
                login_tag = 0
            else:
                error = '密码不正确'
    if form.errors:
        first_key = list(form.errors.keys())[0]
        error = ('%s' % (form.errors[first_key][0]))
    retjson = '{"login_stats":{"login_flag":' + login_flag + ',"error":' + error + '}}'
    return retjson

@bp.route('/change_password',methods=('GET','POST'))
def change_password():
    form = ChangepasswordForm(request.form)
    form.user_name.data = dict(request.args).get('user_name')
    if request.method == 'POST' and form.validate():
        error = None
        user_name = form.user_name.data
        old_password = form.old_password.data
        new_password = form.new_password.data
        user = User.query.filter_by(user_name=user_name).first()
        if user:
            if not user.check_password(old_password):
                error = '旧密码不正确'
            else:
                User.query.filter_by(user_name=user_name).update({'password':generate_password_hash(new_password),'login_cnt':user.login_cnt + 1})
        if error is None:
            current_app.logger.info('action - changepassword - user:%s', user.user_name)
            return render_template('auth/login_dialog_temp.html',message='密码修改成功, 请重新登录')
        flash(error)
    if form.errors:
        first_key = list(form.errors.keys())[0]
        error = ('%s' % (form.errors[first_key][0]))
        flash(error)
    return render_template('auth/change_password.html',form=form)

@bp.route('logout',methods=('GET',))
def logout():
    logout_user()
    return redirect(url_for('ipblacklist.index'))

@login_manager.user_loader
def load_user(id):
    user = User.query.filter_by(id=id).first()
    return user
