from flask import Blueprint,render_template,request,redirect,url_for,flash,jsonify,current_app
from flask_login import current_user
from wtforms import Form,StringField,validators,IntegerField,TextAreaField,RadioField
from wtforms.validators import ValidationError
from .models import Ipwhite
from .DBUtil import DBUtil

bp = Blueprint('ipwhite',__name__, url_prefix='/ipwhite')

class CreateForm(Form):
    ip_addr = TextAreaField("IP Addr",[validators.DataRequired()])
    remark = StringField("备注",[validators.length(max=60,message="不要超过60个字符")])

    def validate_ip_addr(form,field):
        ip_addr_list = field.data.split(",")
        if (len(ip_addr_list) > 10):
            raise ValidationError("一次最多只能提交10个IP")
        ip_addr_list_uniq = list(set(ip_addr_list))
        if len(ip_addr_list_uniq) != len(ip_addr_list):
            raise ValidationError("IP存在重复数据")
        for ip in ip_addr_list:
            myvalidator = validators.ip_address(ipv4=True,ipv6=False,message="IP格式不正确")
            ret = myvalidator.check_ipv4(ip)
            if not ret:
                raise ValidationError("IP格式不正确: " + ip)

class UpdateForm(Form):
    ip_addr = StringField("IP Addr",[validators.DataRequired(),validators.IPAddress(message="IP格式不正确")])
    remark = StringField("备注", [validators.length(max=60, message="不要超过60个字符")])

@bp.route('/index',methods=('GET','POST'))
def index():
    ipwhites = Ipwhite.query.filter()
    context = {
        'ipwhites': ipwhites,
        'menu': 'ipwhite'
    }
    return render_template('ipwhite/index.html',**context)

@bp.route('/create',methods=('GET','POST'))
def create():
    form = CreateForm(request.form)
    if request.method == 'POST' and form.validate():
        error = None
        ip_addr_list = form.ip_addr.data.split(',')
        remark = form.remark.data
        user_name = current_user.user_name
        for ip_addr in ip_addr_list:
            if Ipwhite.query.filter_by(ip_addr=ip_addr).first() is not None:
                error="IP:" + ip_addr + "已存在"
            break
        if error is None:
            sess = DBUtil().get_session()
            for ip_addr in ip_addr_list:
                ipwhite = Ipwhite(ip_addr=ip_addr,remark=remark,user_name=user_name)
                sess.add(ipwhite)
                sess.commit()
                current_app.logger.info('action - ipwhite_create - user:%s, ip:%s', current_user.user_name, ip_addr)
            return redirect(url_for('ipwhite.index'))
        flash(error)
    if form.errors:
        first_key = list(form.errors.keys())[0]
        error = ('%s' % (form.errors[first_key][0]))
        flash(error)
    context = {
        'form': form,
        'menu': 'ipwhite'
    }
    return render_template('/ipwhite/create.html',**context)

@bp.route('/edit/<int:id>',methods=('GET','POST'))
def update(id):
    ipwhite = Ipwhite.query.filter_by(id=id).first()
    form = UpdateForm(request.form)
    if request.method == 'POST' and form.validate():
        error = None
        ip_addr = form.ip_addr.data
        remark = form.remark.data
        if ip_addr != ipwhite.ip_addr and Ipwhite.query.filter_by(ip_addr=ip_addr).first() is not None:
            error = "IP:" + ip_addr + " 已存在"
        if error is None:
            Ipwhite.query.filter_by(ip_addr=ip_addr).update({'ip_addr':ip_addr,'remark':remark})
            current_app.logger.info('action - ipwhite_update - user:%s, ip:%s', current_user.user_name, ip_addr)
            return redirect(url_for('ipwhite.index'))
        flash(error)
    form.ip_addr.data = ipwhite.ip_addr
    form.remark.data = ipwhite.remark
    if form.errors:
        first_key = list(form.errors.keys())[0]
        error = ('%s' % (form.errors[first_key][0]))
        flash(error)
    context = {
        'form': form,
        'menu': 'ipwhite'
    }
    return render_template('/ipwhite/update.html',**context)

@bp.route('/delete/<int:id>',methods=('GET',))
def delete(id):
    ipwhite = Ipwhite.query.filter_by(id=id).first()
    Ipwhite.query.filter_by(id=id).delete()
    current_app.logger.info('action - ipwhite_delete - user:%s, ip:%s', current_user.user_name, ipwhite.ip_addr)
    return redirect(url_for('ipwhite.index'))