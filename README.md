# About

This project is a hard fork of [HTML Muncher](https://github.com/ccampbell/html-obsfucate-css-selectorser.git) which appears to have been abandoned in 2011. `obsfucate-css-selectors` is a Python utility that rewrites CSS, HTML, and JavaScript files in order to save precious bytes and obfuscate your code

if your stylesheet starts out looking like this:

.file2 #special {
    font-size: 1.5em;
    color: #F737FF;
}

.file2 #special2 {
    letter-spacing: 0;
}

.box {
    border: 2px solid #aaa;
    -webkit-border-radius: 5px;
    background: #eee;
    padding: 5px;
}

it will be rewritten as

.d #d {
    font-size: 1.5em;
    color: #F737FF;
}

.d #i {
    letter-spacing: 0;
}

.i {
    border: 2px solid #aaa;
    -webkit-border-radius: 5px;
    background: #eee;
    padding: 5px;
}


# Installation

download the source and install locally

```
git clone http://github.com/ThinkAlexandria/obsfucate-css-selectors
cd obsfucate-css-selectors
python setup.py install
```

# Usage

```bash
obsfuate-css-selectors --help
```

# Examples

to update a bunch of stylesheets and views:
```
obsfucate-css-selectors --css demo/css --html demo/views
```

to update a single file with inline styles/javascript:
```
obsfucate-css-selectors --html demo/single-file/view-with-inline-styles.html
```

you can also select specific files:
```
obsfucate-css-selectors --css file1.css,file2.css --html view1.html,view2.html
```

or you can mix and match files and directories
```
obsfucate-css-selectors --css /my/css/directory,global.css --html /view/directory1,/view/directory2,/view/directory3,template.html
```
