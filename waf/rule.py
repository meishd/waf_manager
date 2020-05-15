from flask import Blueprint,render_template,request,redirect,url_for,flash,jsonify,current_app
from wtforms import Form,StringField,validators,IntegerField,TextAreaField,RadioField
from wtforms.validators import ValidationError
from flask_login import current_user
from sqlalchemy import or_,func
from datetime import datetime,timedelta
import re,math,json
from .models import Rule,Matchrecord
from .DBUtil import DBUtil
from urllib import parse
from .ipblacklist import DateEncoder


bp = Blueprint('rule',__name__, url_prefix='/rule')

class RuleForm(Form):
    id = IntegerField("ID")
    domain = StringField("域名",[validators.InputRequired(),validators.Length(min=6,max=30,message="URL长度范围: 6-30")])
    url = StringField("URL",[validators.InputRequired(),validators.Length(min=6, max=50,message="URL长度范围: 6-50")])
    match_type = StringField("匹配类型")
    win_duration = IntegerField("时间范围(秒)",[validators.InputRequired(),validators.number_range(min=5,max=600,message="时间范围: 5-600秒")])
    req_threshold = IntegerField("请求阀值",[validators.InputRequired(),validators.number_range(min=1,message="请求阀值大于等于1")])
    block_duration = IntegerField("封禁时间(分钟)",[validators.InputRequired(),validators.number_range(min=2,message="封禁时间大于等于2分钟")])

    def validate_url(form, field):
        patt = "\/[\.a-z0-9\/]{5,30}"
        res = re.match(patt,field.data,re.I)
        if not res:
            raise ValidationError("URL格式不正确: '/'开头, 只包含(/.字母数字)")

@bp.route('/rule_list',methods=('GET','POST'))
def rule_list():
    rules = Rule.query.filter()
    return render_template('rule/rule_list.html',rules=rules,menu='rulemanager')

@bp.route('/edit/<int:id>',methods=('GET','POST'))
def update(id):
    rule = Rule.query.filter_by(id=id).first()
    form = RuleForm(request.form)
    if request.method == 'POST' and form.validate():
        error = None
        domain = form.domain.data
        url = form.url.data
        match_type = form.match_type.data
        win_duration = form.win_duration.data
        req_threshold = form.req_threshold.data
        block_duration = form.block_duration.data
        if Rule.query.filter_by(domain=domain,url=url).first() is not None and (domain != rule.domain or url != rule.url):
            error = '域名和URL组合已存在!'
        if error is None:
            Rule.query.filter_by(id=id).update({'domain':domain,'url':url,'match_type':match_type,'win_duration':win_duration,'req_threshold':req_threshold,'block_duration':block_duration})
            current_app.logger.info('action - rule_update - user:%s, domain:%s, url:%s', current_user.user_name, domain, url)
            return redirect(url_for('rule.rule_list'))
        flash(error)
    form.id.data = rule.id
    form.domain.data = rule.domain
    form.url.data = rule.url
    form.match_type.data = rule.match_type
    form.win_duration.data = rule.win_duration
    form.req_threshold.data = rule.req_threshold
    form.block_duration.data = rule.block_duration
    if form.errors:
        first_key = list(form.errors.keys())[0]
        error = ('%s' % (form.errors[first_key][0]))
        flash(error)
    context = {
        'form':form
    }
    return render_template('rule/rule_update.html', **context)

@bp.route('/delete/<int:id>',methods=('GET',))
def delete(id):
    rule = Rule.query.filter_by(id=id).first()
    Rule.query.filter_by(id=id).delete()
    current_app.logger.info('action - rule_delete - user:%s, domain:%s, url:%s', current_user.user_name, rule.domain, rule.url)
    return redirect(url_for('rule.rule_list'))

@bp.route('/create',methods=('GET','POST'))
def create():
    form = RuleForm(request.form)
    if request.method == 'POST' and form.validate():
        error = None
        domain = form.domain.data
        url = form.url.data
        match_type = form.match_type.data
        win_duration = form.win_duration.data
        req_threshold = form.req_threshold.data
        block_duration = form.block_duration.data

        if Rule.query.filter_by(domain=domain, url=url).first() is not None:
            error = '域名和URL组合已存在!'
        if error is None:
            sess = DBUtil().get_session()
            slide_duration = math.ceil(win_duration/5)
            active_status = 0
            rule = Rule(domain=domain,url=url,match_type=match_type,win_duration=win_duration,req_threshold=req_threshold,block_duration=block_duration,
                        slide_duration=slide_duration,active_status=active_status,user_name=current_user.user_name)
            sess.add(rule)
            sess.commit()
            current_app.logger.info('action - rule_create - user:%s, domain:%s, url:%s', current_user.user_name, domain, url)
            return redirect(url_for('rule.rule_list'))
        flash(error)
    if form.errors:
        first_key = list(form.errors.keys())[0]
        error = ('%s' % (form.errors[first_key][0]))
        flash(error)
    return render_template('rule/rule_create.html',form=form)

@bp.route('matchrecord_list',methods=('GET',))
def matchrecord_list():
    context = {
        'menu':'matchrecord'
    }
    return render_template('/rule/matchrecord_list.html',**context)

@bp.route('rule_domain',methods=('GET',))
def rule_domain():
    dbutil = DBUtil()
    sess = dbutil.get_session()
    result = sess.execute('select distinct domain from rule')
    retlist = []
    for row in result:
        retlist.append(row[0])
    retjson = json.dumps(retlist, ensure_ascii=False)
    mainjson = '{"rule_domain":' + retjson + '}'
    return jsonify(mainjson)

@bp.route('/rule_url/<string:rule_domain>',methods=('GET',))
def rule_url(rule_domain):
    dbutil = DBUtil()
    sess = dbutil.get_session()
    result = sess.execute('select distinct url from rule where domain = :rule_domain order by url',{'rule_domain':rule_domain})
    retlist = []
    for row in result:
        retlist.append(row[0])
    retjson = json.dumps(retlist, ensure_ascii=False)
    mainjson = '{"rule_url":' + retjson + '}'
    return jsonify(mainjson)

@bp.route('/matchrecord_list_json',methods=('POST',))
def matchrecord_list_json():
    parjson = parse.unquote(request.get_data(as_text=True)).split("=")[1]
    pardict = json.loads(parjson)
    pageindex = pardict.get('pageindex')
    pagesize = pardict.get('pagesize')
    fullsearchword = pardict.get('fullsearchword')
    rule_domain = pardict.get('rule_domain')
    rule_url = pardict.get('rule_url')
    time_range = pardict.get('time_range')
    baseQuery =  Matchrecord.query
    if time_range:
        time_begin = datetime.now() + timedelta(hours=-int(time_range))
        baseQuery = baseQuery.filter(Matchrecord.create_time > time_begin)
    if rule_domain and rule_domain != 'all':
        sess = DBUtil().get_session()
        result = sess.execute('select distinct ID from rule where domain=:rule_domain',{'rule_domain':rule_domain})
        ruleidlist = []
        for row in result:
            ruleidlist.append(row[0])
        baseQuery = baseQuery.filter(Matchrecord.rule_id.in_(ruleidlist))
    if rule_url and rule_url != 'all':
        sess = DBUtil().get_session()
        result = sess.execute('select distinct ID from rule where url=:rule_url',{'rule_url':rule_url})
        ruleidlist = []
        for row in result:
            ruleidlist.append(row[0])
        baseQuery = baseQuery.filter(Matchrecord.rule_id.in_(ruleidlist))
    if fullsearchword != '':
        baseQuery = baseQuery.filter(or_(Matchrecord.id.like('%' + fullsearchword + '%'),
                                         Matchrecord.rule_id.like('%' + fullsearchword + '%'),
                                         Matchrecord.ip_addr.like('%' + fullsearchword + '%'),
                                         func.date_format(Matchrecord.win_begin, "%Y-%m-%d_%H:%i:%s").like('%' + fullsearchword + '%'),
                                         func.date_format(Matchrecord.win_end, "%Y-%m-%d_%H:%i:%s").like('%' + fullsearchword + '%'),
                                         func.date_format(Matchrecord.create_time, "%Y-%m-%d_%H:%i:%s").like('%' + fullsearchword + '%'),
                                         Matchrecord.request_cnt.like('%' + fullsearchword + '%')))
    totalcount = baseQuery.count()
    matchrecords = baseQuery.order_by(Matchrecord.id.desc()).limit(pagesize).offset((pageindex - 1) * pagesize)

    pagecount = math.ceil(totalcount / pagesize)
    matchrecord_list = []
    for matchrecord in matchrecords:
        matchrecord_list.append(matchrecord.to_dict())
    matchrecord_list_json = json.dumps(matchrecord_list, ensure_ascii=False, cls=DateEncoder)
    mainjson = '{"matchrecordlist":{"matchrecordlistArray":' + matchrecord_list_json + ',"pagination":{"pagesize":' + str(pagesize) + ',"pagecount":' + str(pagecount) + ',"pageindex":' + str(pageindex) + ',"totalcount":' + str(totalcount) + '}}}'
    return jsonify(mainjson)