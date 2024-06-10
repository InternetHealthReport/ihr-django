# ihr-django
Internet Health Report API

This is the implementation for the IHR API: https://ihr.iijlab.net/ihr/en-us/api


# 📝 Table of Contents

- [basic installation for all](#install-all)
  - [Setup without docker](#machine)
  - [Setup using docker (recommended)](#docker)
    - [connecting to an existing postgres server](#docker-psql)
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
pip install django==2.2.27
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

Then copy settings.py, urls.py, wsgi.py, Dockerfile, docker compose and environment file to the correct place:
```zsh
cp ihr/config/*.py internetHealthReport/
cp ihr/config/Dockerfile .
cp ihr/config/docker-compose.yml .
cp ihr/config/.env .
```
You may have to adjust some variables in .env (or settings.py if you don't use docker) to match your database, smtp account, recapcha credentials.

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
replace all `os.environ.get` instances (see .env for default values).
    

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

Create tables:
```zsh
./manage.py makemigrations
./manage.py migrate
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
    nano .env
```
update variables to match your database settings
    

## Connecting to an existing postgres server<a name = "docker-psql"></a>

Get your local ip address

```zsh
hostname -I
```
you will get something like that

```zsh
xxx.xxx.x.xx
```
copy the first IP address and paste it in the .env file.
Also you should allow your postgres to accept connections from outside:

```zsh
sudo nano /etc/postgresql/**/main/postgresql.conf
```

change the following line

```zsh
#listen_addresses = 'localhost'
```

to

```zsh
listen_addresses = '*'
```

allow your postgres to accept connections from outside

```zsh
sudo nano /etc/postgresql/**/main/pg_hba.conf
```

add the following line

```zsh
host    all             all            172.xx.0.00/16            md5
```
xx may vary depending on postgres version but in newer versions it is 20 else it could be 17


start the docker container

```zsh
docker compose up
```
And of course you need to have a postgres database running on your machine with the database and user specified in the .env file.

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

