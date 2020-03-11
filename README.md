# django-ihr
Internet Health Report Website

This is the implementation for the IHR API: https://ihr.iijlab.net

## Server installation

Required packages for Ubuntu:
```
sudo apt install apache2 python3 python3-pip
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
pip install django django-common arrow pyyaml uritemplate
```

Create/import django project:
```
django-admin startproject internetHealthReport
cd internetHealthReport
```
Then copy settings.py, urls.py, wsgi.py from running instance.
