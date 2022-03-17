# django-ihr
Internet Health Report API

This is the implementation for the IHR API: https://ihr.iijlab.net/ihr/en-us/api

## Installation for testing environment

Required packages for Ubuntu:
```
sudo apt install apache2 python3 python3-pip postgresql postgresql-contrib
```

Install virtualenv and django:
```
pip3 install virtualenv
virtualenv ihr
```

Install django:
```
cd ihr
. bin/activate
pip install django
```

Create a new django project:
```
django-admin startproject internetHealthReport
```

Copy IHR's django application and install dependencies:
```
cd internetHealthReport
git clone git@github.com:InternetHealthReport/ihr-django.git ihr
pip install -r ihr/requirements.txt
```

Then copy settings.py, urls.py, wsgi.py to the correct place:
```
cp ihr/config/*.py internetHealthReport/
```
You may have to adjust some variables in settings.py to match your database, smtp account, recapcha credentials.

Create the database and django user (change password as needed):
```
sudo su postgres
psql
postgres=# CREATE DATABASE ihr;
CREATE DATABASE
postgres=# CREATE USER django WITH PASSWORD '123password456';
CREATE ROLE
postgres=# ALTER ROLE django SET client_encoding TO 'utf8';
ALTER ROLE
postgres=# ALTER ROLE django SET timezone TO 'UTC';
ALTER ROLE
postgres=# GRANT ALL PRIVILEGES ON DATABASE ihr TO django;
GRANT
postgres=#quit
exit
```

Remove migration files and create tables: (TODO move production migration files to a different repository)
```
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc"  -delete
./manage.py makemigrations
manage.py migrate
```

TODO: Add test data:
```
wget 
pg_restore
```

Start django:
```
./manage.py runserver
```

Go to http://127.0.0.1:8000/hegemony/ to check if it is working.

