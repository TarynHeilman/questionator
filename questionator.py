#############################################################################
# Original creator: Steve Iannaccone
# Contributors: Frank Burkholder (FB)
#
# revisions:
# 07 Nov 2017 - Updated to Python 3                                 (FB)
#             - Slack messaging ability removed                     (FB)
#             - Dependence on PyFiglet removed                      (FB)
# 12 Nov 2017 - Add function to pre-screen student list             (FB)
#
# Flask app for randomly selecting a student to ask a question
#   This requires that Slacker installed (https://github.com/os/slacker),
#   and that you have Slack API token saved to your bash profile as
#   'SLACK_TOKEN' (https://api.slack.com/tokens),
#
# Run this script from the terminal, passing the gstudents Slack channel
# containing the students you'd like to question.
# e.g.:
#   $ python questionator.py --chan='g39ds_platte'
# This will use #g39ds_platte members as the class roster.
#
# This should take about 20sec to start up.
#############################################################################

import os
import sys
import argparse
from slacker import Slacker
import pandas as pd
from flask import Flask, request, url_for, render_template, request
import pickle as pickle
import numpy as np
import pandas as pd
from random import randrange, sample, choice

def adjust_student_list(slack, students):
    print("Getting preliminary list of members...")
    names = []
    for mem_id in students:
        names.append(slack.users.profile.get(mem_id).body['profile']['real_name'])
    entry = 'y'
    while entry in ['y', 'Y']:
        print("\nHere are the students for Questionating:")
        for i, name in enumerate(names, 1):
            print("{0:2d} {1}".format(i, name))
        entry = input("\nWould you like to remove a student? (y/n) ")
        if entry in ['y', 'Y']:
            ind_del = int(input("The number of the student to remove: "))
            del students[ind_del - 1]
            del names[ind_del - 1]

def init_slack_channel(api_token, channel_name):
    slack = Slacker(api_token)
    print("Collecting available Slack channels...")
    chnls = slack.channels.list().body['channels']
    chnl_names = []
    for x in range(len(chnls)):
        chnl_names.append(chnls[x]['name'])

    #find where our channel is in the list:
    chan_idx = chnl_names.index(channel_name)

    #Collect all channel's member IDs:
    print("Collecting members from channel #{}...".format(channel_name))
    all_members = chnls[chan_idx]['members']
    #Filter out any member with an @galvanize email address:
    print("Filter out any member with an @galvanize email address...")
    students = []
    for idx, member in enumerate(all_members):
        email = slack.users.profile.get(member).body['profile']['email']
        if '@galvanize.com' not in email and member not in students:
            students.append(member)
    adjust_student_list(slack, students)
    return slack, students

def get_member_info(slack, member_id):
    """
    INPUT: slacker slack API object, str of Slack member ID
    OUTPUT: User name, and URL to User avatar
    """
    name = slack.users.profile.get(member_id).body['profile']['real_name']
    avatar = slack.users.profile.get(member_id).body['profile']['image_192']
    return name, avatar

def id_to_username(slack_member_list, member_id):
    """
    INPUT: list of members in Slack channel, String of member ID to convert
        to username
    OUTPUT: String of member's Username
    """
    name = slack.users.profile.get(member_id).body['profile']['real_name']
    for member in slack_member_list:
        if member['profile']['real_name'] == name:
            return member['name']

def getUserMap(slack_member_list):
  #get all users in the slack organization
  """
  I modified this from the `slack_history.py` script from Chandler Abraham
  """
  userIdNameMap = {}
  for user in slack_member_list:
    userIdNameMap[user['id']] = user['name']
  return userIdNameMap

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html', class_name=channel_name)


@app.route('/question', methods=['POST'])
def qbot():
    #Find students who have answered the fewest questions:
    df_min = df[df.num_quest == min(df.num_quest)]
    stud_min = df_min.index.values.tolist()
    #Pick a student with minimal questions asked at random:
    random_index = choice(stud_min)

    #Collect Student's Slack user ID and avatar pic link:
    member_name, avatar_link = get_member_info(slack, df.roster[random_index])
    #+1 on the number of questions answered:
    df.num_quest[random_index] += 1
    #slack.users.list().body['members'][1]['name']
    username = df.username[random_index]
    user_id = df.roster[random_index]
    return render_template('question.html',
                            avatar=avatar_link,
                            name=member_name,
                            quest=df.num_quest[random_index],
                            class_name=channel_name)



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=\
        'The Questionator, a lazy way to ask the class a question.')

    parser.add_argument(
      '--chan',
      help="Pick the gStudents slack channel name from which you want to collect user profiles.")

    args = parser.parse_known_args()
    channel_name = args[0].chan
    api_token = os.environ['SLACK_TOKEN']
    print("*"*50)
    print("Initializing Slack API")
    print("*"*50)
    slack, students = init_slack_channel(api_token, channel_name)

    print("*"*50)
    print("Getting usernames and avatars")
    slack_member_list = slack.users.list().body['members']
    usernames = [id_to_username(slack_member_list, x) for x in students]

    user_map = getUserMap(slack_member_list)

    df = pd.DataFrame()
    df['roster'] = students
    # df['id'] = slack_member_list
    df['username'] = usernames
    df['num_quest'] = [0]*len(students)

    print("*"*50)
    print("Starting up Flask app")
    print("*"*50)
    app.run(host='0.0.0.0', port=8080, threaded=True)
