from flask import Flask, request, abort, redirect, session
from linebot import (LineBotApi, WebhookHandler)
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, StickerSendMessage,
    TemplateSendMessage, ButtonsTemplate, URIAction, MessageAction, FollowEvent)
from datetime import datetime
import pymongo
import json
import requests
import copy
import dialogflow
import os
import uuid
import io
import postgresdb
import textwrap
from google.protobuf.json_format import MessageToJson, MessageToDict
from bs4 import BeautifulSoup
from time import sleep
from concurrent.futures import ThreadPoolExecutor
from google.cloud import storage
from google.cloud.storage import Blob

executor = ThreadPoolExecutor(2)
app = Flask(__name__)
# set the secret key to some random byte, used for session encryption
app.secret_key = b'\xef\xfa"*d\xd5\x18\x89_&}o\x94`\xd5B'

# Global Variable
project_id = os.environ['DIALOGFLOW_PROJECT_ID']
line_bot_api = LineBotApi(os.environ['LINE_CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['LINE_CHANNEL_SECRET'])
appId = os.environ['CHULA_SSO_APP_ID']
appSecret = os.environ['CHULA_SSO_APP_SECRET']
ssoUrl = os.environ['CHULA_SSO_URL']
serviceValidationUrl = os.environ['CHULA_SSO_SERVICE_VALIDATION_URL']
user_session = {}
ise_link = {"class_schedule": {}, "exam_schedule": {}}
pymongo_connection = pymongo.MongoClient(os.environ['MONGODB_URI'])
mongo_db_name = "mongodb_name"
mongo_collection_name = "contents"
contents_col = pymongo_connection[mongo_db_name][mongo_collection_name]


@app.route("/", methods=['GET'])
def index():
    return "hello world"


@app.route("/notification", methods=['GET'])
def notification():
    key = request.args.get('key')
    if key == "iseadmin":
        executor.submit(notify_service)
        return "service activated"
    else:
        return "wrong key"


def notify_service():
    def is_empty_result(page_url):
        r = requests.get(page_url)
        soup = BeautifulSoup(r.content, "html.parser")
        data = soup.find("ul", {"class": "documents-list"})
        return data is None

    def get_content(content_type, page_url):
        y = 1  
        i = 1
        contents = []
        client = storage.Client()
        bucket = client.get_bucket("ise-project-bucket")
        while not is_empty_result(page_url + str(i)):
            r = requests.get(page_url + str(i))
            soup = BeautifulSoup(r.content, "html.parser")
            data = soup.find("ul", {"class": "documents-list"}).find_all("a")
            for value in data:
                content_url = value["href"]
                query = {"url": content_url}
                if contents_col.find_one(query) is not None:
                    i = 998
                else:
                    # stream an image to storage
                    response = requests.get('http://www.ise.eng.chula.ac.th' + value.img["src"], stream=True)
                    content_image = io.BytesIO(response.content)
                    unique_filename = str(uuid.uuid4()) + ".jpg"
                    blob = Blob("content_image/" + unique_filename, bucket)
                    blob.upload_from_file(content_image, content_type="image/jpeg")
                    ######
                    content_img = "https://storage.googleapis.com/ise-project-bucket/content_image/" + unique_filename
                    content_title = value.span.find("span", {"class": "title trim"}).get_text()
                    content_description = value.span.find("span", {"class": "title2 trim"}).get_text()
                    content_date = ""
                    try:
                        content_date = value.span.find("span", {"class": "date"}).get_text()
                    except:
                        content_date = "null"
                    contents.append({"url": content_url, "type": content_type, "img": content_img,
                                     "title": content_title, "description": content_description, "date": content_date})
                    print("insert " + content_type + str(y))
                    print(value["href"])
                    y += 1  # remove later
            i += 1
        # if contents[0] exist > send notification contents[0]
        if contents:
            contents_col.insert_many(contents)
        else:
            print("empty content")

    while True:
        get_content("new-pr", "http://www.ise.eng.chula.ac.th/news?gid=1-008-002-001&pn=")
        get_content("new-prospective", "http://www.ise.eng.chula.ac.th/news?gid=1-008-002-002&pn=")
        get_content("new-current", "http://www.ise.eng.chula.ac.th/news?gid=1-008-002-006&pn=")
        get_content("event", "http://www.ise.eng.chula.ac.th/events?gid=1-008-008&pn=")
        sleep(3600)


@app.route("/login", methods=['GET'])
def login():
    lineid = request.args.get('id')
    if lineid is None:
        return "no parameter"
    # check if the line id is already in the database
    check = isInDatabase(lineid)
    if check:
        return "your LINE account is already linked with the application"
    session['lineid'] = lineid
    return redirect(ssoUrl, code=302)


@app.route("/register", methods=['GET'])
def register():
    ticket = request.args.get('ticket', default='*', type=str)
    print(ticket)
    headers = {'DeeAppId': appId, 'DeeAppSecret': appSecret, 'DeeTicket': ticket}
    print(headers)
    r = requests.get(serviceValidationUrl, headers=headers)
    print(r.status_code)
    print(r.text)
    # if not error
    if r.status_code == 200:
        # check if session exist
        if 'lineid' not in session:
            return "session expired"
        # check if lineid already exist in the DB
        db = postgresdb.DatabaseCon()
        check = db.queryIfExist("""SELECT * from "Users" WHERE "lineId" = '%s'""" % (session["lineid"],))
        if check:
            return "your LINE account is already linked with the application"
        # insert a new row in the DB
        # extract json content first
        content = r.json()
        db = postgresdb.DatabaseCon()
        db.query("""INSERT INTO "Users" ("lineId", "ouid", "firstName", "lastName", "firstNameTh",
            "lastNameTh", "email") VALUES ('%s','%s','%s','%s','%s','%s','%s')
            """ % (session["lineid"], content["ouid"], content["firstname"], content["lastname"],
                   content["firstnameth"], content["lastnameth"], content["email"],))
        db.close()
        # return succesfull login
        line_bot_api.push_message(session["lineid"], [
            TextSendMessage(text='You are now connected with CHULA SSO as "{}"'.format(content["firstname"])),
            StickerSendMessage(package_id='1', sticker_id='13')])
        return "Login Success!"
        # notify user on Line
    # if error > return 401 error
    else:
        return r.text


@app.route("/webhook", methods=['POST'])
def webhook():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)  # pylint: disable=no-member
    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return ('', 200)


# fulfillment query will go in this end point
@app.route("/webhook_dialogflow", methods=['POST'])
def webhook_dialogflow():
    return (200)

@handler.add(FollowEvent)
def handle_follow(event):
    lineid = event.source.user_id
    link = "http://ise-project.herokuapp.com/login?id={}".format(lineid)
    buttons_template = ButtonsTemplate(
        title='Authentication Required', text='Please click the button below to connect with CHULA SSO',
        actions=[URIAction(label='Login', uri=link)
                 ])
    template_message = TemplateSendMessage(
        alt_text='Please open this message from your mobile device to connect with chula sso'
        , template=buttons_template)
    line_bot_api.reply_message(
        event.reply_token, [TextSendMessage(text="Hi, i'm your ISE Virtual Assistant. (happy) \nI'm here to help you with whatever info you might need. \nYou can type 'help' to see what i'm capable of"), template_message])


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    # check the intent
    query_result = detect_intent_texts(project_id, user_id, event.message.text, 'en')

    class Switcher(object):

        def methodname(self, argument):
            # Get the method from 'self'. Default to a lambda.
            method = getattr(self, argument, lambda: "invalid_name")
            if argument is "":
                line_send_text(query_result["fulfillment_text"])
                return
            # Call the method as we return it
            return method()

        def class_schedule(self):
            if isRegistered(user_id):
                major = ""
                try:
                    major = query_result["parameters"]["Major"][0]
                except IndexError:
                    buttons_template = ButtonsTemplate(
                        title='Class Schedule', text='Which major do you want to select?',
                        actions=[MessageAction(label='ICE', text='ice class schedule'),
                                 MessageAction(label='ADME', text='adme class schedule'),
                                 MessageAction(label='NANO', text='nano class schedule'),
                                 MessageAction(label='AERO', text='aero class schedule')])
                    template_message = TemplateSendMessage(
                        alt_text='Class Schedule'
                        , template=buttons_template)
                    line_bot_api.reply_message(event.reply_token, template_message)
                    return
                p = False
                while (p == False):
                    try:
                        FMT = '%x %X'
                        t1 = ise_link["class_schedule"][major]["time_stamp"]
                        t2 = datetime.now().strftime(FMT)
                        tdelta = datetime.strptime(t2, FMT) - datetime.strptime(t1, FMT)
                        if (tdelta.seconds > (3600 * 3)):
                            # more than 3 hours
                            ise_link["class_schedule"][major]["link"] = crawl_class_schedule(major)
                            ise_link["class_schedule"][major]["time_stamp"] = datetime.now().strftime(FMT)
                        line_send_text(ise_link["class_schedule"][major]["link"])
                        p = True;
                    except KeyError:
                        ise_link["class_schedule"].update(
                            {major: {"link": "www.url.com", "time_stamp": '04/12/19 00:01:00'}})
            else:
                print("not registered")

        def default_fallback_intent(self):
            cursor = contents_col.find({'$text': {'$search': event.message.text}}, {'score': {'$meta': 'textScore'}})
            cursor.sort([('score', {'$meta': 'textScore'})])
            contents = []
            for i, doc in enumerate(cursor):
                if i > 4:
                    break
                if doc["description"] == "":
                    doc["description"] = "."
                content = {
                    "type": "bubble",
                    "direction": "ltr",
                    "hero": {
                        "type": "image",
                        "url": doc["img"],
                        "align": "center",
                        "size": "full",
                        "aspectRatio": "16:9",
                        "aspectMode": "cover",
                        "backgroundColor": "#A55858"
                    },
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "spacing": "none",
                        "contents": [
                            {
                                "type": "text",
                                "text": textwrap.shorten(doc["title"], width=100, placeholder="..."),
                                "margin": "none",
                                "size": "md",
                                "weight": "bold",
                                "color": "#801E2B",
                                "wrap": True
                            },
                            {
                                "type": "text",
                                "text": textwrap.shorten(doc["description"], width=150, placeholder="..."),
                                "margin": "sm",
                                "size": "xs",
                                "weight": "regular",
                                "wrap": True
                            }
                        ]
                    },
                    "footer": {
                        "type": "box",
                        "layout": "vertical",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "button",
                                "action": {
                                    "type": "uri",
                                    "label": "Link",
                                    "uri": "http://www.ise.eng.chula.ac.th" + doc["url"]
                                },
                                "color": "#801E2B",
                                "style": "primary"
                            }
                        ]
                    },
                    "styles": {
                        "hero": {
                            "backgroundColor": "#FBBEBE"
                        }
                    }
                }
                contents.append(content)
            if len(contents):
                flex = {
                    "type": "flex",
                    "altText": "Flex Message",
                    "contents": {
                        "type": "carousel",
                        "contents": contents
                    }
                }
                url = 'https://api.line.me/v2/bot/message/reply'
                body = {
                    "replyToken": event.reply_token,
                    "messages": [flex]
                }
                access_token = 'Bearer ' + os.environ['LINE_CHANNEL_ACCESS_TOKEN']
                headers = {'content-type': 'application/json', 'Authorization': access_token}
                r = requests.post(url, headers=headers, json=body)
                print(r.status_code)
            else:
                line_send_text(query_result["fulfillment_text"])

        def default_welcome_intent(self):
            line_send_text(query_result["fulfillment_text"])

        def invalid_name(self):
            line_send_text("invalid method name")

        def help_intent(self):
            content = {
                "type": "flex",
                "altText": "Flex Message",
                "contents": {
                    "type": "bubble",
                    "direction": "ltr",
                    "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                        "type": "text",
                        "text": "Some things you can ask me:",
                        "margin": "none",
                        "size": "xl",
                        "align": "start",
                        "weight": "bold",
                        "wrap": True
                        }
                    ]
                    },
                    "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {
                                "type": "image",
                                "url": "https://storage.googleapis.com/ise-project-bucket/icon/calendar.png",
                                "margin": "none",
                                "align": "start",
                                "gravity": "center",
                                "size": "xxs",
                                "aspectRatio": "1:1",
                                "aspectMode": "fit"
                                },
                                {
                                "type": "text",
                                "text": "Academic Calendar",
                                "flex": 10,
                                "margin": "sm",
                                "align": "start",
                                "gravity": "top",
                                "weight": "bold"
                                }
                            ]
                            },
                            {
                            "type": "text",
                            "text": '"When does semester end"'
                            }
                        ]
                        },
                        {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "xl",
                        "contents": [
                            {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {
                                "type": "image",
                                "url": "https://storage.googleapis.com/ise-project-bucket/icon/calendar.png",
                                "margin": "none",
                                "align": "start",
                                "gravity": "center",
                                "size": "xxs",
                                "aspectRatio": "1:1",
                                "aspectMode": "fit"
                                },
                                {
                                "type": "text",
                                "text": "Class Schedule",
                                "flex": 10,
                                "margin": "sm",
                                "align": "start",
                                "gravity": "top",
                                "weight": "bold"
                                }
                            ]
                            },
                            {
                            "type": "text",
                            "text": '"I want to see ICE class schedule"',
                            "wrap": True
                            }
                        ]
                        },
                        {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "xl",
                        "contents": [
                            {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {
                                "type": "image",
                                "url": "https://storage.googleapis.com/ise-project-bucket/icon/calendar.png",
                                "margin": "none",
                                "align": "start",
                                "gravity": "center",
                                "size": "xxs",
                                "aspectRatio": "1:1",
                                "aspectMode": "fit"
                                },
                                {
                                "type": "text",
                                "text": "Exam Schedule",
                                "flex": 10,
                                "margin": "sm",
                                "align": "start",
                                "gravity": "top",
                                "weight": "bold"
                                }
                            ]
                            },
                            {
                            "type": "text",
                            "text": '"When is the examination date"',
                            "wrap": True
                            }
                        ]
                        },
                        {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "xl",
                        "contents": [
                            {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {
                                "type": "image",
                                "url": "https://storage.googleapis.com/ise-project-bucket/icon/graduation.png",
                                "margin": "none",
                                "align": "start",
                                "gravity": "center",
                                "size": "xxs",
                                "aspectRatio": "1:1",
                                "aspectMode": "fit"
                                },
                                {
                                "type": "text",
                                "text": "Graduation",
                                "flex": 10,
                                "margin": "sm",
                                "align": "start",
                                "gravity": "top",
                                "weight": "bold"
                                }
                            ]
                            },
                            {
                            "type": "text",
                            "text": '"Where can I get my graduation documents"',
                            "wrap": True
                            }
                        ]
                        },
                        {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "xl",
                        "contents": [
                            {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {
                                "type": "image",
                                "url": "https://storage.googleapis.com/ise-project-bucket/icon/project.png",
                                "margin": "none",
                                "align": "start",
                                "gravity": "center",
                                "size": "xxs",
                                "aspectRatio": "1:1",
                                "aspectMode": "fit"
                                },
                                {
                                "type": "text",
                                "text": "Senior Project",
                                "flex": 10,
                                "margin": "sm",
                                "align": "start",
                                "gravity": "top",
                                "weight": "bold"
                                }
                            ]
                            },
                            {
                            "type": "text",
                            "text": '"How to write a senior project proposal?"',
                            "wrap": True
                            }
                        ]
                        },
                        {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "xl",
                        "contents": [
                            {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {
                                "type": "image",
                                "url": "https://storage.googleapis.com/ise-project-bucket/icon/internship.png",
                                "margin": "none",
                                "align": "start",
                                "gravity": "center",
                                "size": "xxs",
                                "aspectRatio": "1:1",
                                "aspectMode": "fit"
                                },
                                {
                                "type": "text",
                                "text": "Internship",
                                "flex": 10,
                                "margin": "sm",
                                "align": "start",
                                "gravity": "top",
                                "weight": "bold"
                                }
                            ]
                            },
                            {
                            "type": "text",
                            "text": '"Where to submit internship report"',
                            "wrap": True
                            }
                        ]
                        },
                        {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "xl",
                        "contents": [
                            {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {
                                "type": "image",
                                "url": "https://storage.googleapis.com/ise-project-bucket/icon/form.png",
                                "margin": "none",
                                "align": "start",
                                "gravity": "center",
                                "size": "xxs",
                                "aspectRatio": "1:1",
                                "aspectMode": "fit"
                                },
                                {
                                "type": "text",
                                "text": "Request Form",
                                "flex": 10,
                                "margin": "sm",
                                "align": "start",
                                "gravity": "top",
                                "weight": "bold"
                                }
                            ]
                            },
                            {
                            "type": "text",
                            "text": '"Where can i get late withdrawal form"',
                            "wrap": True
                            }
                        ]
                        },
                        {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "xl",
                        "contents": [
                            {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {
                                "type": "image",
                                "url": "https://storage.googleapis.com/ise-project-bucket/icon/contact.png",
                                "margin": "none",
                                "align": "start",
                                "gravity": "center",
                                "size": "xxs",
                                "aspectRatio": "1:1",
                                "aspectMode": "fit"
                                },
                                {
                                "type": "text",
                                "text": "Contact",
                                "flex": 10,
                                "margin": "sm",
                                "align": "start",
                                "gravity": "top",
                                "weight": "bold"
                                }
                            ]
                            },
                            {
                            "type": "text",
                            "text": '"Where is ISE office"',
                            "wrap": True
                            }
                        ]
                        }
                    ]
                    }
                }
            }
            url = 'https://api.line.me/v2/bot/message/reply'
            body = {
                "replyToken": event.reply_token,
                "messages": [content]
            }
            access_token = 'Bearer ' + os.environ['LINE_CHANNEL_ACCESS_TOKEN']
            headers = {'content-type': 'application/json', 'Authorization': access_token}
            r = requests.post(url, headers=headers, json=body)
            print(r.status_code)

        def exam_schedule(self):
            line_send_text(query_result["fulfillment_text"])

        def ise_contact(self):
            line_send_text(query_result["fulfillment_text"])

        def academic_calendar(self):
            line_send_text(query_result["fulfillment_text"])

        def graduation(self):
            line_send_text(query_result["fulfillment_text"])

        def internship(self):
            line_send_text(query_result["fulfillment_text"])

        def request_form(self):
            line_send_text(query_result["fulfillment_text"])

        def senior_project(self):
            line_send_text(query_result["fulfillment_text"])

    def line_send_text(input_text):
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=input_text))

    # search and execute from the intent
    switch = Switcher()
    switch.methodname(query_result["intent"])


def isRegistered(lineid):
    FMT = '%x %X'
    if (lineid in user_session) | isInDatabase(lineid):
        user_session[lineid] = datetime.now().strftime(FMT)
        return True
    link = "http://ise-project.herokuapp.com/login?id={}".format(lineid)
    buttons_template = ButtonsTemplate(
        title='Authentication Required', text='Please click the button below to connect with CHULA SSO',
        actions=[URIAction(label='Login', uri=link)
                 ])
    template_message = TemplateSendMessage(
        alt_text='Please open this message from your mobile device to connect with chula sso'
        , template=buttons_template)
    line_bot_api.push_message(lineid, template_message)
    return False


# methods
def detect_intent_texts(project_id, session_id, text, language_code):
    import dialogflow_v2 as dialogflow
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, session_id)

    if text:
        # getting a response from dialogflow
        text_input = dialogflow.types.TextInput(  # pylint: disable=no-member
            text=text, language_code=language_code)
        query_input = dialogflow.types.QueryInput(text=text_input)  # pylint: disable=no-member
        response = session_client.detect_intent(
            session=session, query_input=query_input)
        # keeping everything to python dict for easily accessible
        query_result_dict = {}
        query_result_dict["query_text"] = response.query_result.query_text
        query_result_dict["intent"] = response.query_result.intent.display_name
        query_result_dict["confidence"] = response.query_result.intent_detection_confidence
        query_result_dict["language_code"] = response.query_result.language_code
        query_result_dict["all_required_param"] = response.query_result.all_required_params_present
        query_result_dict["parameters"] = MessageToDict(response.query_result.parameters)
        query_result_dict["payload"] = [MessageToDict(x) for x in response.query_result.fulfillment_messages]
        query_result_dict["fulfillment_text"] = response.query_result.fulfillment_text
        print(query_result_dict["intent"])
        return query_result_dict
    return "text not exist"


def isInDatabase(lineid):
    db = postgresdb.DatabaseCon()
    check = db.queryIfExist("""SELECT * from "Users" WHERE "lineId" = '%s'""" % (lineid,))
    db.close()
    return check


def crawl_class_schedule(major):
    major = major.lower()
    r = requests.get("http://www.ise.eng.chula.ac.th/current-students/schedule/class/")
    soup = BeautifulSoup(r.content, "html.parser")
    data = soup.find("div", {"rel": major}).find("span", {"class": "downloadlinks"})
    return "http://www.ise.eng.chula.ac.th" + data.a['href']


if __name__ == "__main__":
    app.run()
