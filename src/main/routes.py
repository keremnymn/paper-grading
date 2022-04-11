from flask import render_template, request, Blueprint, jsonify, flash, redirect, url_for, abort, make_response,\
                current_app, session
from src.models import User, Notification, PaperGradingKullanimi, BireyselFatura, Tag, Hangiders
from flask_login import login_user
from src import db
import os, locale
from flask_login import current_user
from sqlalchemy import func, distinct, tuple_, case, desc
from flask_babel import lazy_gettext as _l, get_locale

main = Blueprint('main', __name__)

@main.post('/lang_degis')
def lang_degis():
    id = request.form.get('id')
    session['lang_code'] = id
    if id == 'tr':
        locale.setlocale(locale.LC_TIME, 'tr_TR.UTF-8')
    return session['lang_code'], 200

@main.route('/howto')
@main.route("/nasilyapilir")
def nasilyapilir():
    template = 'kilavuzlar/tr/kilavuz.html' if str(get_locale()) == 'tr' else 'kilavuzlar/en/guide.html'
    return render_template(template, baslik=_l("Nasıl Yapılır?"), isIndex=True)

@main.route('/uyari_tamamdir', methods=['POST'])
def uyari_degistir():
    aydi = request.form.get('aydi')
    path = os.path.join(current_app.config['INFERFILES_PATH'], aydi)
    if not os.path.isfile(os.path.join(path, 'siraya_alindi.txt')):
        abort(404)
    else:
        with open(os.path.join(path, 'siraya_alindi.txt'), 'w') as f:
            f.write('anlaşıldı')
        return '', 200

@main.route('/', methods=['GET', 'POST'])
def pg_landing():
    if not current_user.is_authenticated:
        _user = db.session.query(User).first()
        if _user == None:
            _user = User(username='Test User', email='dummy@dummy.com', isadmin=True, image_file='default.jpg')
            _credit = BireyselFatura(kalan_kredi=9999, user_id=1)
            _tag = Tag(name='High School', lang='en')
            _lesson = Hangiders(name='Science', lang='en')
            db.session.add_all([_user, _credit, _tag, _lesson])
            # db.session.flush()
            db.session.commit()
        login_user(_user)
    
    bitti = False
    if current_user.is_authenticated:
        path = os.path.join(current_app.config['INFERFILES_PATH'], str(current_user.id))
        if os.path.isfile(os.path.join(path, 'siraya_alindi.txt')):
            with open(os.path.join(path, 'siraya_alindi.txt'), 'r') as f:
                f = f.read()
            if str(f) == 'ilk':
                bitti = True
            else:
                bitti = False
    return render_template('paper_grading/pg_landing_page.html', isIndex=True, 
                            baslik='Paper Grading', bitti=bitti)

@main.route('/landing_veriler', methods=['GET'])
def pg_landing_veriler():
    try:
        ogretmenler = db.session.query(func.count(distinct(tuple_(PaperGradingKullanimi.user_id)))).scalar()
        kagitlar = db.session.query(func.sum(PaperGradingKullanimi.kagit_sayisi)).scalar()
        sorular = db.session.query(func.sum(\
                                    PaperGradingKullanimi.coktan_secmeli_sayisi\
                                    + PaperGradingKullanimi.dogru_yanlis_sayisi\
                                    + PaperGradingKullanimi.eslestirme_sayisi\
                                    + PaperGradingKullanimi.bosluk_doldurma_sayisi)).scalar()
        tasarruf = int(round((kagitlar * 3 ) / 60))
        ogretmenler = int(ogretmenler) + 25
        return jsonify([int(ogretmenler), int(kagitlar), int(sorular), int(tasarruf)])
    except:
        return '', 404


@main.route('/notifications')
def notifications():
    notifications = current_user.notifications.order_by(desc(Notification.yeni_mi), Notification.timestamp.desc()).limit(5)
    not_list = [{'name': n.name,'data': n.get_data(),'timestamp': n.timestamp,'id': n.id,'yeni_mi': n.yeni_mi} for n in notifications]
    return jsonify(not_list)

@main.route('/yeni_nots')
def yeni_nots():
    notifications = db.session.query(func.count(case([(Notification.yeni_mi, 1)]))).filter(Notification.user_id==current_user.id).scalar()
    return str(notifications)

@main.route('/read_notifications', methods=['POST'])
def read_notifications():
    bildirim = request.form.getlist('idler[]')
    for x in bildirim:
        x = int(x.replace('yenibild_', ''))
        _not = Notification.query.filter_by(id=x).first_or_404()
        _not.yeni_mi = False
    try:
        db.session.commit()
    except:
        db.session.rollback()
    return '', 200

@main.route('/bildirimler', methods=['GET','POST'])
def bildirimler():
    notifications = current_user.notifications.order_by(Notification.timestamp.asc()).all()
    return render_template('main/bildirimler.html',
                            notifications=notifications,
                            baslik='Bildirimler')