import re

from setuptools import find_packages, setup

with open("akd_customizations/__init__.py", encoding="utf-8") as f:
	version = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', f.read()).group(1)

install_requires = []
try:
	with open("requirements.txt", encoding="utf-8") as f:
		install_requires = [
			line.strip() for line in f if line.strip() and not line.startswith("#")
		]
except FileNotFoundError:
	pass

setup(
	name="akd_customizations",
	version=version,
	description="AKD Customizations",
	author="jyothi",
	author_email="jyothi.p@quarkcs.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires,
	python_requires=">=3.14",
)
