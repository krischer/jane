# Jane Settings

This page documents the configuration options specific to Jane. To change 
them, please edit the `local_settings.py` file in the `src/jane` directory.

## Default Settings

Quick overview of all available settings including their default values. 

```python
JANE_INSTANCE_NAME = "Jane"
JANE_ACCENT_COLOR = "#D9230F"
```

## Available Settings

Detailed documentation of all available settings. 

#### JANE_INSTANCE_NAME

Name of the instance used in parts of the web interface. Any reasonably short 
string should work.

* *Default Value:* `"Jane"`


#### JANE_ACCENT_COLOR

Color used in certain parts of the web interface. Useful to distinguish
separate Jane installations at a glance. Please pass a string containing a 
hexadecimal HTML color.

* *Default Value:* `"#D9230F"`
