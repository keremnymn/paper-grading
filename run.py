import os
from src import create_app

app = create_app()

if __name__ == "__main__":
    if not os.path.isfile(os.path.join(os.getcwd(), 'src', app.config['SQLALCHEMY_DATABASE_URI'])):
        app.app_context().push()
        from src import db
        db.create_all()
        db.session.commit()
    
    if os.environ['RUNNING_ON'] == 'localhost':
        app.run(debug=True)
    else:
        app.run(debug=False)