=====
django-spcc
=====

django-spcc 是一个Django APP，提供了实用的model，view，forms，templates等公共库。


Quick start
-----------
# Only support Django 2.2.x, Python 3.6

1. Add "spcc" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = [
        ...
        'spcc',
    ]

2. Include the spcc URLconf in your project urls.py like this::

    path('spcc/', include('spcc.urls')),

3. Run `python manage.py migrate` to create the spcc models.