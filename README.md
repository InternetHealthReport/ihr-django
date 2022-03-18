# django-ihr
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

## TODO Add test data
```zsh
wget 
pg_restore
```

## Running the application
Activate the python environment and lunch django server:
```zsh
cd ihr 
. bin/activate
internetHealthReport/manage.py runserver
```


## Working with a local instance of IHR website
To redirect all API calls to the local django server, add the following line in /etc/hosts:
127.0.0.1 ihr.iijlab.net

