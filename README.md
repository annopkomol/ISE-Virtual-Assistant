# ISE Virtual Assistant
A chatbot that is developed to assist the engineering students at Chulalongkorn university. The chatbot uses Dialogflow api to detect and answer intents accordingly with manually configured response according to the incoming intents, which mainly consists of directing users to the page they needed with links. Intents outside of the scope would be searched and crawled from the faculty website, which also doubles as news update notifications.

## Getting Started

These instructions will get you a copy of the project up and running on local server for development and testing purposes.
Some of the features in this project may require you to connect to other services such as <a href="https://cloud.google.com/">Google Cloud Platform</a>, <a href="https://account.it.chula.ac.th/wiki/doku.php">ChulaSSO</a>, 
<a href="https://cloud.google.com/dialogflow-enterprise/docs/reference/rest/v2-overview">Dialogflow API</a> ,and <a href="https://developers.line.biz/en/services/messaging-api/">LINE Messaging API</a>

### (Optional) Setup Python Development Environment
we recommend you to deploy the project on the virtual environment which allows 
you to avoid installing Python packages globally which could break system tools or other projects.

#### Install virtualenv (on MacOS and Linux)
```
python3 -m pip install virtualenv
```
#### create a virtual environment
```
python3 -m venv env
```
```env``` is the location to create the virtual environment.
In this case, venv will create a virtual Python installation in the ```env``` folder.

#### activate a virtual environment
```
source env/bin/activate
```

### Requirements & Dependencies

* python 3.7.x
* Install all requirements from requirements.txt by using
```
$ pip -install -r requirements.txt
```

### Config Variables


```
$ export CHULA_SSO_APP_ID=YOUR_CHULA_SSO_APP_ID
$ export CHULA_SSO_APP_SECRET=YOUR_CHULA_SSO_APP_SECRET
$ export CHULA_SSO_SERVICE_VALIDATION_URL=YOUR_VALIDATION_URL
$ export CHULA_SSO_URL=YOUR_CHULA_SSO_URL
$ export DATABASE_URL=YOUR_POSTGRESQL_URL
$ export DB_HOST=
$ export DB_NAME=POSTGRESQL_NAME
$ export DB_PASSWORD=POSTGRESQL_PASSWORD
$ export DB_USERNAME=POSTGRESQL_USERNAME
$ export DIALOGFLOW_PROJECT_ID=DIALOGFLOW_PROJECT_ID
$ export GOOGLE_APPLICATION_CREDENTIALS=YOUR_GOOGLE_CREDENTIALS.json
$ export LINE_CHANNEL_SECRET=YOUR_LINE_CHANNEL_SECRET
$ export LINE_CHANNEL_ACCESS_TOKEN=YOUR_LINE_CHANNEL_ACCESS_TOKEN
$ export MONGODB_URI=YOUR_MONGODB_URI
```
For using Dialogflow API, copy your credential (json file) from Google Cloud Platform to your project folder

### Running the Server
To run a web server on your development server, use the following command on your project folder
```
$ python3 bot.py
```
Note: the deployment for this project was done on Heroku, so if you run this project on your local machine or other platforms, you
do not have to include ```procfile``` and ```runtime.txt``` on your project

## Architecture Design
<div align="center"><img src="/Screenshots/ss3.png" width="70%" height="70%"></div>

## User Journey
<div align="center"><img src="/Screenshots/ss2.png" width="70%" height="70%"></div>

## Screenshots
<img src="/Screenshots/ss1.png" width="70%" height="70%"><img src="/Screenshots/ss4.png" width="40%" height="40%"><img src="/Screenshots/ss5.png" width="40%" height="40%">
