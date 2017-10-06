# ETA: Extensible Toolkit for Analytics

An open and extensible video analytics infrastructure.

This project is supported by the [NIST Public Safety Innovation Accelerator
Program](https://www.nist.gov/news-events/news/2017/06/nist-awards-385-million-accelerate-public-safety-communications).

## Installation

Clone the repository

```shell
git clone https://github.com/voxel51/eta
cd eta/
```

If you want to simply install the toolkit and use it, run

```shell
pip install .
```

Now `import eta` will work from anywhere, and you can delete the directory you
just cloned.

If you want to install the project in development mode, run

```shell
pip install -e .
```

Now `import eta` will still work from anywhere, and any changes you make in
your local copy of `eta/` will take effect immediately.

## External dependencies

The ETA package requires
[OpenCV](http://opencv.org),
[ffmpeg](https://www.ffmpeg.org), and
[convert](https://www.imagemagick.org/script/index.php).

Currently ETA supports both `OpenCV 2.4` or later and `OpenCV 3.0` or later.

To install these external dependencies, run the install script

```shell
bash install_externals.bash
```

## Uninstallation

```shell
pip uninstall eta
```