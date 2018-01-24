# The Questionator

The Questionator is a Python 3 Flask web application that collects student
names and profile pictures from a student Slack channel and then selects one
to "questionate."

It filters out any member with an `@galvanize.com` email address so you won't
ask any support staff or instructors who are also on the channel questions.

Because this interacts with Slack's API, you will need an API token. You can get
an API key [here](https://api.slack.com/custom-integrations/legacy-tokens). Set this key to a local
environment alias in your `.bash_profile`, `.bashrc`, or `.zshrc` resource
file. Use the alias name `SLACK_TOKEN` so the python script will pull it in
automatically when launched.

For example:
```bash
export SLACK_TOKEN="your token string here..."
```
Don't forget that you have to re-source you bash profile after editing it...

```bash
$ source ~/.bash_profile
```

API calls are made through python using the [Slacker package](https://github.com/os/slacker). You will need to install this before you run the script.

```bash
$ pip install slacker
```

You specify the Slack channel your class is using by passing it as a system
argument when you exectute the script from terminal.

To run the Questionator:
```bash
$ python questionator.py --chan='channel_name' 
```

This would collect student names, Slack usernames, and profile pics for members
in the 'channel_name' channel.

The script takes about 20 seconds to initialize with all the necessary info
from the Slack API. After which, it will launch the Flask App
_(running on port 8080)_.

## What It Does
After collecting all the class members, it initializes the number of questions
asked to zero for everyone. When you press the button `Ask a question` it gets
the list of students who have answered the fewest questions _(initially, this
will be everyone since they have all answered zero questions)_. It then makes a
random selection from this list of whom to ask the question. The username and
profile pic for that student are collected and displayed on screen. That student
then has their "number of questions asked" incremented by one. This helps track
how many questions have been asked, as well as remove the possibility of asking
the same student two or more consecutive questions.
