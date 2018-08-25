from setuptools import setup

# scipy 19 needed as contains csgraph
setup(
	name='auto_montage',
	version='0.1',
	description='Automatic cone montage software',
	author='Benjamin Davidson',
	author_email='benjamin.davidson.16@ucl.ac.ul',
	license='MIT',
	packages=['auto_montage'],
	install_requires=[
		'matplotlib',
		'numpy',
		'scipy',
		'scikit-image',
		'Pillow',
		'argparse',
		'xlrd',
		'opencv-python==3.3.0.10',
                'pyyaml'
		],
	entry_points = {
		'console_scripts': ['auto_montage=auto_montage.__main__:main'],
	},
	keywords='AOSLO montage',
	include_package_data=True,
	zip_safe=False)
