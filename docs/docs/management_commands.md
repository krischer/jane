# Management Command

`Jane` has a couple of custom management commands. This page documents these. 
All of them have to be execute within the `jane/src` directory or use 
absolute paths.


## Available Management Commands

List of all available management commands.

* `add_mappings`
* `index_waveforms`
* `upload_documents`

## Details

Please also view the `--help` output of each command for the most up-to-date
information.

--- 

`$ python manage.py add_mappings`

Use this command to add a large number of waveform mappings. Smaller amounts
of mappings can also conveniently be added via the admin interface. See the 
[Waveforms page](waveforms.md) for more details about how mappings work.

The command takes a single argument, the path to a file which specifies a 
mapping in each line. Each line has `ID` `NEW_ID`, `STARTTIME`, and 
`ENDTIME`. Example file:

```
ZZ.e6008..E XY.A00..HHE 2008-08-18T14:00:00.000000Z 2008-09-30T12:00:00.000000Z
ZZ.e6008..N XY.A00..HHN 2008-08-18T14:00:00.000000Z 2008-09-30T12:00:00.000000Z
```

--- 

`$ python manage.py index_waveforms`

Used to index waveforms. Fairly powerful and flexible and documented in more
detail on the [Waveforms page](waveforms.md).

--- 

`$ python manage.py upload_documents`

The command line can be used as an alternative to the REST interface to 
upload documents. See the [Document Database page](documents.md) for more 
details.
