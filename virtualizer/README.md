This directory is here just so that we can use setuptools along with the 
previously used method (submodule import).

This enables that you either include virtualizer as a git submodule...

... or do:
```sh
$ sudo python setup.py develop
```

... or even:
```sh
$ sudo python setup.py install
```

... and import syntax will always be the same:
```py
import virtualizer.virtualizer
```

You can always use the Virtualizer class as in:
```py
virtualizer.virtualizer.Virtualizer
```

