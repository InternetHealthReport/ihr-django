# ihr-django
Internet Health Report API

This is the implementation for the IHR API: https://ihr.iijlab.net/ihr/en-us/api


# 📝 Table of Contents

- [basic installation for all](#install-all)
  - [If you wish to use your machine](#machine)
  - [using docker](#docker)
- [Add test data to the database](#add-test-data)


## basic installation for all <a name = "install-all"></a>

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

Copy IHR's django application :
```zsh
cd internetHealthReport
git clone git@github.com:InternetHealthReport/ihr-django.git ihr

```

Then copy settings.py, urls.py, wsgi.py, Dockerfile,docker compose to the correct place:
```zsh
cp ihr/config/*.py internetHealthReport/
cp ihr/config/Dockerfile .
cp ihr/config/docker-compose.yml .
```
You may have to adjust some variables in settings.py to match your database, smtp account, recapcha credentials.

## If you wish to use your machine <a name = "machine"></a>

install dependencies
```zsh
pip install -r ihr/requirements.txt
```

make sure that the host of database in the settings is localhost
    
```zsh
    cd internetHealthReport
    nano settings.py
```
scroll down to the DATABASES section and make sure that the host is localhost
    

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

## if you want to use docker <a name = "docker"></a>


install docker

```zsh
sudo apt install docker
```


make sure that the host of database in the settings is db
    
```zsh
    cd internetHealthReport
    nano settings.py
```
scroll down to the DATABASES section and make sure that the host is db
    


make sure you are in the internetHealthReport directory



start the docker container

```zsh
docker compose up
```

If this is the first time to run the container, you need to apply the migration files

```zsh
docker ps
```

you will find something like that 
    
```zsh
    CONTAINER ID   IMAGE                                        COMMAND                  CREATED          STATUS          PORTS                    NAMES
    1c1c1c1c1c1c   internethealthreport-django-app         "python manage.py ru…"       20 seconds ago   Up 19 seconds
```

copy the container id and run the following command

```zsh
docker exec -it 1c1c1c1c1c1c /bin/bash
```

you will be inside the container

```zsh
python manage.py migrate
```

congratulations, you have a running django server

Go to http://127.0.0.1:8000/hegemony/ to check if it is working.

## Add test data to the database <a name = "add-test-data"></a>
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

