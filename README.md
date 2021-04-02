# Vaccspot bot

## A bot that notifies you when there are open vaccine spots

At this stage it is pretty hacked together.

The goal is to get notifications when covid vaccine appointments become availalbe. Connecticut is hard coded at the moment but if you did a Ctrl-F/Command-F for "CT" and replaced it with another states initials it would probably work just fine.

You need an email address to send the notifications and a recipient email address. You will also need the password for the sender email.

Save the emails in a file called `info.yml` which should look like this:

```
alert:
  sender: <sender email@domain.com>
  target: <recipient email@domain.com>
```

You should also save the password for the sender email as an environment variable called `VACCSPOT_PASS`

## In develpment:

* Get Walgreens data direct from the source rather than though 3rd party API
* Include expired appointments in new alerts
