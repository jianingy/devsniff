# intro

`devsniff` is an HTTP Proxy for API development.

![screenshot](https://raw.githubusercontent.com/jianingy/devsniff/master/docs/img/screen1.png)

# features

* hostname remapping
* filter requests by mime-type / hostname
* multiple profiles for different environments
* automatically decode gzip content
* HTTP/1.1 chunking transfer
* HTTPS passthrough (not MITM)


# installation

```
python ./setup.py install
```

If you wanna get invovled with development, please run

```
python ./setup.py develop
```

# getting started

```
devsniff --database=sqlite:///path/to/database.db
```
