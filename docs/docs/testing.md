# Testing

To test `Jane` you have to create (within PostgreSQL) a test database and a 
test user according to your `local_settings.py` file in `jane/src` (see the 
very end of the template file). Defaults settings are `test_jane` for database 
user, table, and password. This user must have superuser privileges as it has 
to create a new database but also install the postgis extension for that 
database! 


```bash
$ createuser --superuser --encrypted --pwprompt test_jane
```

Finally, running the tests is then a matter of calling:

```bash
$ python manage.py test

Creating test database for alias 'default'...
..............
----------------------------------------------------------------------
Ran 14 tests in 4.142s

OK
Destroying test database for alias 'default'...
```

Optionally, `pytest` can be used after installing `pytest` and `pytest-django`
(which e.g. allows to execute single test cases):

```bash
$ cd /path/to/jane/root
$ cd src
$ pytest
==================== test session starts ==================================
platform linux -- Python 3.4.4, pytest-3.0.5, py-1.4.31, pluggy-0.4.0
Django settings: jane.settings (from ini file)
rootdir: /home/megies/git/jane-master/src, inifile: pytest.ini
plugins: django-3.1.2
collected 53 items

jane/documents/tests/test_documents.py ...
jane/fdsnws/tests/test_dataselect_1.py ................
jane/fdsnws/tests/test_station_1.py ................
jane/jane/tests/test_code_formatting.py .
jane/quakeml/tests/test_quakeml.py ............
jane/stationxml/tests/test_stationxml.py .
jane/waveforms/tests/test_core.py ...
jane/waveforms/tests/test_management_commands.py .

================= 53 passed in 33.48 seconds ==============================

$ pytest -k test_radial_query_quakeml
==================== test session starts ==================================
platform linux -- Python 3.4.4, pytest-3.0.5, py-1.4.31, pluggy-0.4.0
Django settings: jane.settings (from ini file)
rootdir: /home/megies/git/jane-master/src, inifile: pytest.ini
plugins: django-3.1.2
collected 53 items

jane/quakeml/tests/test_quakeml.py .

==================== 52 tests deselected ==================================
============ 1 passed, 52 deselected in 4.92 seconds ======================
```
