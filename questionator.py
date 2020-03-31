#############################################################################
# Original creator: Steve Iannaccone
# Contributors: Frank Burkholder (FB), Taryn Heilman (TH)
#
# revisions:
# 07 Nov 2017 - Updated to Python 3                                 (FB)
#             - Slack messaging ability removed                     (FB)
#             - Dependence on PyFiglet removed                      (FB)
# 12 Nov 2017 - Add function to pre-screen student list             (FB)
# 25 Feb 2018 - Use channels.info to get member list                (FB)
# 31 Mar 2020 - Fix docstrings                                      (TH)
#             - Make filtering galvanize addresses optional         (TH)
#             - Do not hard code port                               (TH)
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
import json


def adjust_student_list(slack, students):
    """Interactive, allows user to remove any students, modifies students list in place

    INPUT:
        slack: Slacker object slack
        students: list of students
    """
    print("Getting preliminary list of members...")
    names = []
    for mem_id in students:
        names.append(slack.users.profile.get(mem_id).body['profile']['real_name'])
    entry = 'y'
    while entry in ['y', 'Y']:
        print("\nHere are the students for Questionating:")
        for i, name in enumerate(names, 1):
            print("{0:2d} {1}".format(i, name))
        print("\nThere are {} students.".format(len(students)))
        entry = input("\nWould you like to remove a student? (y/n) ")
        if entry in ['y', 'Y']:
            ind_del = int(input("The number of the student to remove: "))
            del students[ind_del - 1]
            del names[ind_del - 1]


def remove_galvanize_emails(slack, all_members):
    """Filters out channel members with an @galvanize email address

    INPUT:
        slack: Slacker object slack
        all_members: list of member objects

    OUTPUT:
        list students
    """
    print("Filtering out members with an @galvanize email address...")
    students = []
    for idx, member in enumerate(all_members):
        email = slack.users.profile.get(member).body['profile']['email']
        if '@galvanize.com' not in email and member not in students:
            students.append(member)
    return students


def init_slack_channel(api_token, channel_name, remove_galvanize_employees):
    """initialize slack channel

    INPUT:
        api_token: string, slack api token
        channel_name: string, name of channel to pull members from
        remove_galvanize_employees: bool, whether to filter out the @galvanize email addresses
    OUTPUT:
        Slacker object slack
        list students
    """
    slack = Slacker(api_token)
    print("Collecting available Slack channels...")
    chnls = slack.channels.list().body['channels']
    chnl_names = []
    for x in range(len(chnls)):
        chnl_names.append(chnls[x]['name'])
    chan_idx = chnl_names.index(channel_name)       # channel index
    chan = chnls[chan_idx]                          # channel of interest
    chan_id = chan['id']                            # channel id
    chan_info = slack.channels.info(chan_id)        # channel info (json)
    chan_dict = json.loads(chan_info.raw)           # channel dictionary
    all_members = chan_dict['channel']['members']   # member ids

    # Collect all channel's member IDs:
    print("Collecting members from channel #{}...".format(channel_name))
    if remove_galvanize_employees:
        students = remove_galvanize_emails(slack, all_members)
    else:
        students = all_members

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


def get_user_map(slack_member_list):
    """Get all users in the slack organization

    Steve modified this from the `slack_history.py` script from Chandler Abraham

    INPUT: list slack_member_list, get all users in the slack organization
    OUTPUT: dictionary, with keys user id and the values user name
    """
    user_id_name_map = {}
    for user in slack_member_list:
        user_id_name_map[user['id']] = user['name']
    return user_id_name_map


app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html', class_name=channel_name)


@app.route('/question', methods=['POST'])
def qbot():
    # Find students who have answered the fewest questions:
    df_min = df[df.num_quest == min(df.num_quest)]
    stud_min = df_min.index.values.tolist()
    # Pick a student with minimal questions asked at random:
    random_index = choice(stud_min)

    #Collect Student's Slack user ID and avatar pic link:
    member_name, avatar_link = get_member_info(slack, df.roster[random_index])
    # +1 on the number of questions answered:
    df.num_quest[random_index] += 1

    # slack.users.list().body['members'][1]['name']
    username = df.username[random_index]
    user_id = df.roster[random_index]
    return render_template('question.html',
                            avatar=avatar_link,
                            name=member_name,
                            quest=df.num_quest[random_index],
                            class_name=channel_name)


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='The Questionator, a lazy way to ask the class a question.')

    parser.add_argument('--chan', type=str,
                        help="Pick the gStudents slack channel name from which you want to collect user profiles.")

    parser.add_argument('--remove-galvanize-employees', type=str, default='True', choices=('True', 'False'),
                        help="Whether to remove galvanize.com email addresses")

    parser.add_argument('--port', type=int, default=8080,
                        help='Which port number to run the questionator on')

    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = parse_args()

    channel_name = args.chan
    api_token = os.environ['SLACK_TOKEN']
    print("*"*50)
    print("Initializing Slack API")
    print("*"*50)
    remove_galvanize_employees = args.remove_galvanize_employees == 'True'
    slack, students = init_slack_channel(api_token, channel_name, remove_galvanize_employees)

    print("*"*50)
    print("Getting usernames and avatars")
    slack_member_list = slack.users.list().body['members']
    usernames = [id_to_username(slack_member_list, x) for x in students]

    user_map = get_user_map(slack_member_list)

    df = pd.DataFrame()
    df['roster'] = students
    df['username'] = usernames
    df['num_quest'] = [0]*len(students)

    print("*"*50)
    print("Starting up Flask app")
    print("*"*50)
    app.run(host='0.0.0.0', port=args.port, threaded=True)
