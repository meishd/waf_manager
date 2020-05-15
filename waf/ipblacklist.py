from flask import Blueprint,render_template,request,redirect,url_for,flash,jsonify,session,g,current_app
from flask_login import current_user
from sqlalchemy import or_,func
from sqlalchemy.orm import sessionmaker
from wtforms import Form,StringField,validators,IntegerField,TextAreaField,RadioField
from wtforms.validators import ValidationError
import json,datetime,math
from urllib import parse
from . import db,models
from .models import Ipblacklist
from .DBUtil import DBUtil

bp = Blueprint('ipblacklist',__name__, url_prefix='/ipblacklist')

class UpdateForm(Form):
    id = StringField("ID")
    ip_addr = StringField("IP Addr",[validators.IPAddress(ipv4=True,ipv6=False,message="IP格式不正确")])
    status = IntegerField("状态",[validators.number_range(min=0,max=1,message="状态不正确")])
    effective_time = IntegerField("有效期(分钟)",[validators.number_range(min=0,message="有效期不正确")])
    remark = StringField("备注",[validators.length(max=50,message="备注不要超过50个字符,否则列表展示很难看的!:)")])

class CreateForm(Form):
    ip_addr = TextAreaField("IP Addr",[validators.DataRequired()])
    status = IntegerField("状态", [validators.number_range(min=0, max=1, message="状态不正确")])
    effective_time = IntegerField("有效期(分钟)", [validators.DataRequired(),validators.number_range(min=0, message="有效期不正确")])
    remark = StringField("备注", [validators.length(max=50, message="备注不要超过50个字符!")])

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


class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj,datetime.datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        else:
            return json.JSONEncoder.default(self,obj)


def get_ipblacklist(id):
    ipblacklist = Ipblacklist.query.filter_by(id=id).first()
    return ipblacklist

@bp.route('/',methods=('GET','POST'))
def index():
    sourcetype = 'all'
    source = 'all'
    if request.args:
        sourcetype = dict(request.args).get('sourcetype')[0]
        source = dict(request.args).get('source')[0]
    context = {
        'sourcetype': sourcetype,
        'source': source,
        'menu': 'ipblacklist'
    }
    return render_template('ipblacklist/index.html',**context)

@bp.route('/source_type',methods=('GET',))
def source_type():
    dbutil = DBUtil()
    sess = dbutil.get_session()
    result = sess.execute('select distinct source_type from ip_blacklist')
    retlist = []
    for row in result:
        retlist.append(row[0])
    retjson = json.dumps(retlist, ensure_ascii=False)
    mainjson = '{"sourcetype":' + retjson + '}'
    return jsonify(mainjson)

@bp.route('/source/<string:source_type>',methods=('GET',))
def source(source_type):
    dbutil = DBUtil()
    sess = dbutil.get_session()
    result = sess.execute('select distinct source from ip_blacklist where source_type = :source_type order by source',{'source_type':source_type})
    retlist = []
    for row in result:
        retlist.append(row[0])
    retjson = json.dumps(retlist, ensure_ascii=False)
    mainjson = '{"source":' + retjson + '}'
    return jsonify(mainjson)


@bp.route('/index_json',methods=('POST',))
def index_json():
    parjson = parse.unquote(request.get_data(as_text=True)).split("=")[1]
    pardict = json.loads(parjson)
    pageindex = pardict.get('pageindex')
    pagesize = pardict.get('pagesize')
    fullsearchword = pardict.get('fullsearchword')
    sourcetype = pardict.get('sourcetype')
    source = pardict.get('source')
    baseQuery =  Ipblacklist.query
    if sourcetype and sourcetype != 'all':
        baseQuery = baseQuery.filter_by(source_type=sourcetype)
    if source and source != 'all':
        baseQuery = baseQuery.filter_by(source=source)
    if fullsearchword != '':
        baseQuery = baseQuery.filter(or_(Ipblacklist.id.like('%' + fullsearchword + '%'),
                                                 Ipblacklist.ip_addr.like('%' + fullsearchword + '%'),
                                                 func.date_format(Ipblacklist.create_time, "%Y-%m-%d_%H:%i:%s").like('%' + fullsearchword + '%'),
                                                 func.date_format(Ipblacklist.modify_time, "%Y-%m-%d_%H:%i:%s").like('%' + fullsearchword + '%'),
                                                 Ipblacklist.source_type.like('%' + fullsearchword + '%'),
                                                 Ipblacklist.source.like('%' + fullsearchword + '%'),
                                                 Ipblacklist.remark.like('%' + fullsearchword + '%')))
    totalcount = baseQuery.count()
    ipblacklists = baseQuery.order_by(Ipblacklist.id.desc()).limit(pagesize).offset((pageindex - 1) * pagesize)

    pagecount = math.ceil(totalcount / pagesize)
    ipblacklists_list = []
    for ipblacklist in ipblacklists:
        ipblacklists_list.append(ipblacklist.to_dict())
    ipblacklists_list_json = json.dumps(ipblacklists_list, ensure_ascii=False, cls=DateEncoder)
    mainjson = '{"ipblacklist":{"ipblacklistArray":' + ipblacklists_list_json + ',"pagination":{"pagesize":' + str(pagesize) + ',"pagecount":' + str(pagecount) + ',"pageindex":' + str(pageindex) + ',"totalcount":' + str(totalcount) + '}}}'
    return jsonify(mainjson)

@bp.route('/edit/<int:id>',methods=('GET','POST'))
def update(id):
    ipblacklist = get_ipblacklist(id)
    form = UpdateForm(request.form)
    sourcetype = dict(request.args).get('sourcetype')[0]
    source = dict(request.args).get('source')[0]
    if request.method == 'POST' and form.validate():
        error = None
        sourcetype = request.form.to_dict().get('sourcetype')
        source = request.form.to_dict().get('source')
        ip_addr = form.ip_addr.data
        status = form.status.data
        effective_time = form.effective_time.data
        remark = form.remark.data
        if Ipblacklist.query.filter_by(ip_addr=ip_addr).first() is not None and ip_addr != ipblacklist.ip_addr:
            error = 'IP已存在!'
        if error is None:
            Ipblacklist.query.filter_by(id=id).update({'ip_addr':ip_addr,'status':status,'effective_time':effective_time,'remark':remark})
            current_app.logger.info('action - ipblacklist_update - user:%s, ip:%s', current_user.user_name, ip_addr)
            return redirect(url_for('ipblacklist.index',sourcetype=sourcetype,source=source))
        flash(error)
    form.id.data = id
    form.ip_addr.data = ipblacklist.ip_addr
    form.status.data = ipblacklist.status
    form.effective_time.data = ipblacklist.effective_time
    form.remark.data = ipblacklist.remark
    if form.errors:
        first_key = list(form.errors.keys())[0]
        error = ('%s' % (form.errors[first_key][0]))
        flash(error)
    context = {
        'form':form,
        'sourcetype':sourcetype,
        'source':source
    }
    return render_template('ipblacklist/update.html', **context)

@bp.route('/delete/<int:id>',methods=('GET',))
def delete(id):
    sourcetype = dict(request.args).get('sourcetype')[0]
    source = dict(request.args).get('source')[0]
    ipblacklist = Ipblacklist.query.filter_by(id=id).first()
    Ipblacklist.query.filter_by(id=id).delete()
    context = {
        'sourcetype':sourcetype,
        'source':source
    }
    current_app.logger.info('action - ipblacklist_delete - user:%s, ip:%s', current_user.user_name, ipblacklist.ip_addr)
    return redirect(url_for('ipblacklist.index', **context))

@bp.route('/create',methods=('GET','POST'))
def create():
    form = CreateForm(request.form)
    if request.method == 'POST' and form.validate():
        error = None
        ip_addr_list = form.ip_addr.data.split(',')
        status = form.status.data
        effective_time = form.effective_time.data
        remark = form.remark.data
        for ip in ip_addr_list:
            if Ipblacklist.query.filter_by(ip_addr=ip).first() is not None:
                error = "IP " + ip + " 已存在"
            break
        if error is None:
            sess = DBUtil().get_session()
            for ip in ip_addr_list:
                ipblacklist = Ipblacklist(ip_addr=ip,status=status,effective_time=effective_time,remark=remark,source_type="手动",source=current_user.user_name)
                sess.add(ipblacklist)
                sess.commit()
                current_app.logger.info('action - ipblacklist_create - user:%s, ip:%s', current_user.user_name, ip)
            return redirect(url_for('ipblacklist.index'))
        flash(error)
    if form.errors:
        first_key = list(form.errors.keys())[0]
        error = ('%s' % (form.errors[first_key][0]))
        flash(error)
    return render_template('ipblacklist/create.html',form=form, menu='manublock')
