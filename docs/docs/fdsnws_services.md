# FDSN Web Services


`Jane` implements version 1.1 of all `fdsnws` web services. 

### *dataselect* Service

This draws its data from `jane.waveforms`. It supports arbitrary length 
downloads and also honors the restriced/protected stations defined in the 
admin interface. See the [waveforms documentation](waveforms.md) for more 
information. Use the `/queryauth` route to access protected data.

### *station* Service

This draws its data from the default StationXML plugin from`jane.documents`.
All restrictions and permissions that apply to the documents also apply to 
the *station* service. This, by default, includes the restricted/protected 
stations defined in `jane.waveforms`. Use the `/queryauth` route to access 
protected data.

### *event* Service

This draws its data from the default QuakeML plugin from`jane.documents`.
All restrictions and permissions that apply to the documents also apply to 
the *event* service. This, by default, means that only users who have 
permissions to see private events can see them. Use the `/queryauth` route 
to access protected data.
