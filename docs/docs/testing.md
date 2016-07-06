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
