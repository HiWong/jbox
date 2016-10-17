import os
import requests
import uuid
from flask import abort, Flask, json, jsonify, render_template, redirect, request, url_for, flash, session
from flask_httpauth import HTTPAuth
from flask_oauthlib.client import OAuth
from . import auth
from config import basedir
from ..models import db, Channel, Developer, Integration, generate_integration_id
from ..main.views import update_qq_api_request_data, qq, json_to_dict

app = Flask(__name__)
app.debug = True
app.secret_key = 'development'
oauth = OAuth(app)

UPLOAD_FOLDER = basedir + '/jbox/static/images/'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
GITHUB_CLIENT_ID = "c293cc8df7ff97e14237"
GITHUB_CLIENT_SECRET = "b9eb46397fa59c4415a7a741d6f5490896ab710f"

github = oauth.remote_app(
    'github',
    consumer_key=GITHUB_CLIENT_ID,
    consumer_secret=GITHUB_CLIENT_SECRET,
    base_url='https://api.github.com/',
    request_token_url=None,
    access_token_url='https://github.com/login/oauth/access_token',
    request_token_params={'scope': 'admin:repo_hook'},
    authorize_url='https://github.com/login/oauth/authorize'
)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@auth.route('/manage', methods=['GET', 'POST'])
def manage():
    developer = get_developer()
    print(developer)
    integrations = developer.integrations
    return render_template('auth/manage.html', **locals())
    # return render_template('index.html')


@auth.route('/add_third_party', methods=['GET'])
def add_third_party():
    return render_template('auth/third_party_integration.html')


@auth.route('/github_integration', methods=['GET'])
def github_integration():
    developer = get_developer()
    integrations = developer.integrations
    github_integrations = []
    if integrations:
        for integration in integrations:
            if integration.type == 'github':
                github_integrations.append(integration)
    tp_length = len(github_integrations)
    return render_template('auth/github_integration.html', **locals())


@auth.route('/manage/create_integration/<string:integration_id>/<string:token>/<string:channel>',
            methods=['GET', 'POST'])
def create_integration(integration_id, token, channel):
    integration = Integration.query.filter_by(integration_id=integration_id).first()
    channels = get_channel_list()
    developer = get_developer()
    dev_key = developer.dev_key
    return render_template('auth/create.html', **locals())


@auth.route('/manage/edit_integration/<string:integration_id>', methods=['GET', 'POST'])
def edit_integration(integration_id):
    developer = get_developer()
    integration = Integration.query.filter_by(integration_id=integration_id).first()
    channel = integration.channel.channel
    channels = get_channel_list()
    dev_key = developer.dev_key
    return render_template('auth/create.html', **locals())


@auth.route('/manage/edit_github_integration/<string:integration_id>', methods=['GET', 'POST'])
def edit_github_integration(integration_id):
    developer = get_developer()
    integration = Integration.query.filter_by(integration_id=integration_id).first()
    repositories = integration.repositories
    store_repos = []
    if repositories:
        for repository in repositories:
            store_repos.append(repository.repository)
    channel = integration.channel.channel
    channels = get_channel_list()
    dev_key = developer.dev_key
    try:
        response = github.get('https://api.github.com/user/repos', {'access_token': integration.token})
        me = github.get('user')
        user = me.data['login']
        print(user)
        list = response.data
        repos = []
        if len(list) > 1:
            for i in range(len(list)):
                repos.append(list[i]['name'])
            print(repos)
        return render_template('auth/create.html', **locals())
    except Exception:
        return github.authorize(callback=url_for('auth.github_authorize', integration_id=integration_id, _external=True))


@auth.route('/github/authorize/<string:integration_id>', methods=['GET'])
def github_authorize(integration_id):
    resp = github.authorized_response()
    if resp is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )
    session['github_token'] = (resp['access_token'], '')
    response = github.get('https://api.github.com/user/repos', {'access_token': session['github_token'][0]})
    integration = Integration.query.filter_by(integration_id=integration_id).first()
    repositories = integration.repositories
    store_repos = []
    if repositories:
        for repository in repositories:
            store_repos.append(repository.repository)
    channel = integration.channel.channel
    channels = get_channel_list()
    developer = get_developer()
    dev_key = developer.dev_key
    me = github.get('user')
    user = me.data['login']
    print(user)
    list = response.data
    repos = []
    if len(list) > 1:
        for i in range(len(list)):
            repos.append(list[i]['name'])
        print(repos)
    return render_template('auth/create.html', **locals())


@auth.route('/new/post_to_channel', methods=['GET'])
def post_to_channel():
    developer = get_developer()
    dev_key = developer.dev_key
    channels = get_channel_list()
    return render_template('auth/new/post2channel.html', **locals())


@auth.route('/new/github/post_to_channel', methods=['GET'])
def post_to_channel_github():
    developer = get_developer()
    dev_key = developer.dev_key
    channels = get_channel_list()
    github = True
    return render_template('auth/new/post2channel.html', **locals())


@auth.route('/new/channel', methods=['GET'])
def new_channel():
    developer = get_developer()
    dev_key = developer.dev_key
    return render_template('auth/new/channel.html', **locals())


@auth.route('/qrcode', methods=['GET'])
def qrcode():
    developer = get_developer()
    return render_template('auth/qrcode.html', dev_key=developer.dev_key)


@auth.route('/upload/avatar/<dev_key>', methods=['POST'])
def upload_avatar(dev_key):
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            developer = Developer.query.filter_by(dev_key=dev_key).first()
            if developer is not None and developer.avatar is not None:
                path = os.path.join(UPLOAD_FOLDER, developer.avatar)
                if os.path.exists(path) and os.path.isfile(path):
                    os.remove(path)
                file_type = file.filename.rsplit('.', 1)[1]
                filename = generate_file_name(developer.dev_key, file_type)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                return jsonify(name=filename)


@auth.route('/upload/<integration_id>', methods=['POST'])
def upload_icon(integration_id):
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            integration = Integration.query.filter_by(integration_id=integration_id).first()
            if integration is not None and integration.icon is not None:
                path = os.path.join(UPLOAD_FOLDER, integration.icon)
                if os.path.exists(path) and os.path.isfile(path):
                    os.remove(path)
                file_type = file.filename.rsplit('.', 1)[1]
                filename = generate_file_name(integration.integration_id, file_type)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                return jsonify(name=filename)


def get_channel_list():
    channel_list = []
    developer = get_developer()
    if developer is not None:
        channels = developer.channels
        for channel in channels:
            channel_list.append(channel.channel)
        return channel_list


def get_developer():
    if 'qq_token' in session:
        respMe = qq.get('/oauth2.0/me', {'access_token': session['qq_token'][0]})
        openid = json_to_dict(respMe.data)['openid']
        developer = Developer.query.filter_by(platform_id=openid).first()
        return developer
    return None


@auth.route('/profile', methods=['GET'])
def profile():
    developer = get_developer()
    return render_template('auth/profile.html', developer=developer)


@auth.route('/setting', methods=['GET', 'POST'])
def setting():
    developer = get_developer()
    return render_template('auth/setting.html', developer=developer)


def generate_file_name(id, file_type):
    return uuid.uuid3(uuid.NAMESPACE_DNS, id).__str__() + '.' + file_type


@auth.route('/github/authorize/<string:channel>', methods=['GET'])
def authorize_github(channel):
    return github.authorize(callback=url_for('auth.new_github_integration', channel=channel, _external=True))


@auth.route('/github/integrations/<string:channel>', methods=['GET', 'POST'])
def new_github_integration(channel):
    resp = github.authorized_response()
    if resp is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )
    session['github_token'] = (resp['access_token'], '')
    token = session['github_token'][0]
    new_integration_id = generate_integration_id()
    developer = get_developer()
    github_channel = Channel.query.filter_by(developer=developer, channel=channel).first()
    if github_channel is None:
        github_channel = Channel(developer=developer, channel=channel)
        db.session.add(github_channel)
        db.session.commit()
    integration = Integration(developer=developer,
                              integration_id=new_integration_id,
                              channel=github_channel,
                              description='',
                              icon='',
                              token=token,
                              type='github')
    db.session.add(integration)
    db.session.commit()
    return redirect(url_for('auth.edit_github_integration', integration_id=new_integration_id))


@github.tokengetter
def get_github_oauth_token():
    return session.get('github_token')
