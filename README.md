# ihr-django
Internet Health Report API

This is the implementation for the IHR API: https://ihr.iijlab.net/ihr/en-us/api

## Installation of Django and IHR app

Required packages for Ubuntu:
```zsh
sudo apt install apache2 python3 python3-pip postgresql postgresql-contrib
```

Install virtualenv and django:
```zsh
pip3 install virtualenv
virtualenv ihr
```

Install django:
```zsh
cd ihr
. bin/activate
pip install django
```

Create a new django project:
```zsh
django-admin startproject internetHealthReport
```

Copy IHR's django application and install dependencies:
```zsh
cd internetHealthReport
git clone git@github.com:InternetHealthReport/ihr-django.git ihr
pip install -r ihr/requirements.txt
```

Then copy settings.py, urls.py, wsgi.py to the correct place:
```zsh
cp ihr/config/*.py internetHealthReport/
```
You may have to adjust some variables in settings.py to match your database, smtp account, recapcha credentials.

Create the database and django user (change password as needed):
```zsh
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
postgres=#\q
exit
```

Remove migration files and create tables: (TODO move production migration files to a different repository)
```zsh
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc"  -delete
./manage.py makemigrations
manage.py migrate
```

Start django:
```zsh
./manage.py runserver
```

Go to http://127.0.0.1:8000/hegemony/ to check if it is working.

## Add test data to the database
In the production database some of the ids are changed to BIGINT. We should
locally apply these changes before importing data:
```zsh
psql -U django -d ihr -c "ALTER TABLE ihr_hegemony ALTER COLUMN id SET DATA TYPE bigint"
psql -U django -d ihr -c "ALTER TABLE ihr_hegemony_prefix ALTER COLUMN id SET DATA TYPE bigint"
psql -U django -d ihr -c "ALTER TABLE ihr_hegemony_country ALTER COLUMN id SET DATA TYPE bigint"
psql -U django -d ihr -c "ALTER TABLE ihr_atlas_delay ALTER COLUMN id SET DATA TYPE bigint"
```

Download a database snapshot and load it:
```zsh
wget https://ihr-archive.iijlab.net/ihr-dev/psql-snapshot/2022-03-10/2022-03-10_psql_snapshot.sql.lz4 
lz4 2022-03-10_psql_snapshot.sql.lz4 
psql -U django ihr < 2022-03-10_psql_snapshot.sql
```

## Running the application
Activate the python environment and lunch django server:
```zsh
cd ihr 
. bin/activate
internetHealthReport/manage.py runserver
```
Go to http://127.0.0.1:8000/hegemony/ to check if it is working.

## Working with a local instance of IHR website (https://github.com/InternetHealthReport/ihr-website)
To redirect all API calls to the local django server you should change the API
URL in ihr-website/src/plugins/IhrApi.js:
```js
const IHR_API_BASE = 'http://127.0.0.1:8000/'
```

