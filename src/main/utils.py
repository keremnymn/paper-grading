from bs4 import BeautifulSoup
from src import db, celery
from src.models import Notification
import json

def lazy_load_dp(obje):
    soup = BeautifulSoup(obje, "html.parser")
    tags=soup.findAll('img')
    for x in tags:
        x['loading'] = 'lazy'
    return str(soup)

@celery.task(queue='obj')
def bildirim_gonder(notification):
    notification = Notification(
        name=notification['name'], 
        payload_json=json.dumps(notification['data']), 
        user_id=notification['alici']
    )
    db.session.add(notification)
    try:
        db.session.commit()
    except:
        db.session.rollback()