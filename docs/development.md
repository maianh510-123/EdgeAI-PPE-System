# Development
Python 3.10+; runtime has no external dependencies. From project root:

```sh
python main.py --config configs/default.yaml
python -m unittest discover -s tests -v
```

Optional: `python -m pip install -e .` installs the src-layout package and CLI.
The build backend requires setuptools; installation may download it. Running main.py
and tests directly needs no package installation or network access.

Config .yaml files currently use JSON syntax, a valid YAML subset. The loader uses
stdlib json, so general YAML syntax/comments are unsupported. TODO: adopt a full
YAML parser if needed. CLI with no config uses AppConfig defaults. An explicitly
supplied missing/invalid config fails rather than silently using defaults.
Environment overrides file/default IDs. .env is not automatically loaded.

Add a detector implementing detect(frame), normalize and validate its labels, and
inject it into PPEPipeline. Set is_demo=False only for real detections. Add transports
implementing send(event); wrap transport failures as OSError. The shipped CLI rejects
unimplemented adapter names. TODO: add factory/registration when an adapter exists.
Tests should cover model-specific label mapping and actual transport failures.

TODO: agree event schema evolution, person association, privacy/retention, model and
dataset licensing, backend contract, hardware, packaging and CI. The team must choose
a repository license before public distribution; no license choice is imposed here.

Optional communication experiments: see ../communication_testbed/README.md.
HTTP uses stdlib; MQTT and CoAP dependencies are optional and require Python 3.11+.
Run network tests with optional packages installed; MQTT test needs
EDGEAI_MQTT_TEST_PORT pointing to an isolated local test broker.
