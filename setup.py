from setuptools import setup, find_packages

setup(
    name="university_kindergarten",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "Flask==2.3.2",
        "Flask-SQLAlchemy==3.0.3",
        "Flask-Login==0.6.2",
        "Flask-Bcrypt==1.0.1",
        "Flask-WTF==1.1.1",
        "Flask-Migrate==4.0.4",
        "WTForms==3.0.1",
        "python-dotenv==1.0.0",
    ],
)